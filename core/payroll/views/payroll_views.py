# core/payroll/views/payroll_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from ..models import Payroll, PayrollPeriod, PayrollRubro, AdelantoQuincena, Rubro, TipoRubro
from decimal import Decimal
from django.core.exceptions import ValidationError
from ..forms.payroll_forms import PayrollForm, PayrollRubroForm
from core.employees.models import Employee
from core.employees.utils import send_payroll_notification_email
import json
import logging

logger = logging.getLogger(__name__)


@login_required
def payroll_list(request):
    payrolls = Payroll.objects.select_related(
        'employee__user',
        'period'
    ).all()
    
    period_id = request.GET.get('period')
    employee_id = request.GET.get('employee')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if search in ['None', 'none', '', None]:
        search = None
    elif search:
        search = search.strip()
        if not search:
            search = None
    
    if period_id in ['', 'None', None]:
        period_id = None
    
    if employee_id in ['', 'None', None]:
        employee_id = None
        
    if status in ['', 'None', None]:
        status = None
    
    if period_id:
        payrolls = payrolls.filter(period_id=period_id)
    
    if employee_id:
        payrolls = payrolls.filter(employee_id=employee_id)
    
    if status == 'paid':
        payrolls = payrolls.filter(is_paid=True)
    elif status == 'unpaid':
        payrolls = payrolls.filter(is_paid=False)
    
    if search:
        payrolls = payrolls.filter(
            Q(employee__user__first_name__icontains=search) |
            Q(employee__user__last_name__icontains=search) |
            Q(employee__employee_number__icontains=search) |
            Q(employee__user__email__icontains=search)
        )
    
    payrolls = payrolls.order_by('-created_at')
    
    paginator = Paginator(payrolls, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'periods': PayrollPeriod.objects.filter(is_closed=False).order_by('-start_date'),
        'employees': Employee.objects.filter(status='active').select_related('user').order_by('user__first_name'),
        'current_filters': {
            'period': period_id or '',
            'employee': employee_id or '',
            'status': status or '',
            'search': search or '',
        }
    }
    
    return render(request, 'pages/admin/payroll/list.html', context)


@login_required
def payroll_form(request, pk=None):
    """Crear o editar nómina"""
    payroll = get_object_or_404(Payroll, pk=pk) if pk else None
    
    if request.method == 'POST':
        form = PayrollForm(request.POST, instance=payroll)
        if form.is_valid():
            payroll = form.save()
            
            # Aplicar rubros automáticos si es nueva nómina
            if not pk:
                payroll.aplicar_rubros_automaticos()
            
            messages.success(request, 'Nómina guardada correctamente.')
            return redirect('payroll:payroll_detail', pk=payroll.pk)
        else:
            messages.error(request, 'Error al guardar la nómina.')
    else:
        form = PayrollForm(instance=payroll)
    
    context = {
        'form': form,
        'payroll': payroll,
        'is_edit': pk is not None,
    }
    
    return render(request, 'pages/admin/payroll/form.html', context)


@login_required
def payroll_detail(request, pk):
    """Detalle de nómina con rubros aplicados"""
    payroll = get_object_or_404(Payroll, pk=pk)
    rubros_aplicados = payroll.rubros_aplicados.select_related('rubro', 'rubro__tipo_rubro').all()
    adelantos_pendientes = payroll.get_adelantos_pendientes()
    
    context = {
        'payroll': payroll,
        'rubros_aplicados': rubros_aplicados,
        'adelantos_pendientes': adelantos_pendientes,
        'ingresos': rubros_aplicados.filter(rubro__tipo_rubro__tipo='ingreso'),
        'egresos': rubros_aplicados.filter(rubro__tipo_rubro__tipo='egreso'),
    }
    
    return render(request, 'pages/admin/payroll/detail.html', context)


@login_required
def payroll_select_rubro(request, payroll_pk):
    """Seleccionar y aplicar rubro existente a nómina"""
    payroll = get_object_or_404(Payroll, pk=payroll_pk)
    
    # Obtener rubros ya aplicados para evitar duplicados
    rubros_aplicados_ids = payroll.rubros_aplicados.values_list('rubro_id', flat=True)
    
    if request.method == 'POST':
        rubro_id = request.POST.get('rubro_id')
        monto_manual = request.POST.get('monto_manual')
        observaciones = request.POST.get('observaciones', '')
        
        if not rubro_id:
            messages.error(request, 'Debe seleccionar un rubro.')
            return redirect('payroll:payroll_select_rubro', payroll_pk=payroll.pk)
        
        try:
            rubro = Rubro.objects.get(id=rubro_id, is_active=True)
            
            # Verificar que no esté ya aplicado
            if rubro.id in rubros_aplicados_ids:
                messages.error(request, f'El rubro "{rubro.nombre}" ya está aplicado a esta nómina.')
                return redirect('payroll:payroll_select_rubro', payroll_pk=payroll.pk)
            
            # Calcular monto según el tipo de cálculo del rubro
            monto_calculado = 0
            porcentaje_aplicado = None
            
            if rubro.tipo_calculo == 'fijo':
                # Usar monto por defecto del rubro o manual
                if monto_manual:
                    monto_calculado = float(monto_manual)
                elif rubro.monto_default:
                    monto_calculado = rubro.monto_default
                else:
                    messages.error(request, 'Debe especificar un monto para este rubro.')
                    return redirect('payroll:payroll_select_rubro', payroll_pk=payroll.pk)
            
            elif rubro.tipo_calculo == 'porcentaje':
                # Calcular porcentaje del salario base
                porcentaje = rubro.porcentaje_default if rubro.porcentaje_default else 0
                if porcentaje > 0:
                    monto_calculado = (payroll.base_salary * porcentaje) / 100
                    porcentaje_aplicado = porcentaje
                else:
                    messages.error(request, 'El rubro no tiene un porcentaje configurado.')
                    return redirect('payroll:payroll_select_rubro', payroll_pk=payroll.pk)
            
            elif rubro.tipo_calculo == 'porcentaje_bruto':
                # Calcular porcentaje del salario bruto
                porcentaje = rubro.porcentaje_default if rubro.porcentaje_default else 0
                if porcentaje > 0:
                    salario_bruto = payroll.base_salary + payroll.overtime_pay
                    monto_calculado = (salario_bruto * porcentaje) / 100
                    porcentaje_aplicado = porcentaje
                else:
                    messages.error(request, 'El rubro no tiene un porcentaje configurado.')
                    return redirect('payroll:payroll_select_rubro', payroll_pk=payroll.pk)
            
            # Crear el rubro aplicado
            rubro_aplicado = PayrollRubro.objects.create(
                payroll=payroll,
                rubro=rubro,
                monto=monto_calculado,
                porcentaje=porcentaje_aplicado,
                observaciones=observaciones
            )
            
            # Mensaje de éxito
            if rubro.tipo_calculo in ['porcentaje', 'porcentaje_bruto']:
                messages.success(
                    request,
                    f'Rubro "{rubro.nombre}" aplicado: {porcentaje_aplicado}% = ${monto_calculado:.2f}'
                )
            else:
                messages.success(
                    request,
                    f'Rubro "{rubro.nombre}" aplicado: ${monto_calculado:.2f}'
                )
            
            return redirect('payroll:payroll_detail', pk=payroll.pk)
        
        except Rubro.DoesNotExist:
            messages.error(request, 'Rubro no encontrado.')
        except ValueError:
            messages.error(request, 'Monto inválido.')
        except Exception as e:
            messages.error(request, f'Error al aplicar rubro: {str(e)}')
    
    # Obtener rubros disponibles (no aplicados)
    rubros_disponibles = Rubro.objects.filter(
        is_active=True
    ).exclude(
        id__in=rubros_aplicados_ids
    ).select_related('tipo_rubro').order_by('tipo_rubro__tipo', 'nombre')
    
    # Agrupar por tipo
    rubros_por_tipo = {}
    for rubro in rubros_disponibles:
        tipo = rubro.tipo_rubro.get_tipo_display()
        if tipo not in rubros_por_tipo:
            rubros_por_tipo[tipo] = []
        rubros_por_tipo[tipo].append(rubro)
    
    context = {
        'payroll': payroll,
        'rubros_por_tipo': rubros_por_tipo,
        'total_disponibles': rubros_disponibles.count(),
    }
    
    return render(request, 'pages/admin/payroll/select_rubro.html', context)

# También necesitas una función auxiliar para AJAX
@login_required
def get_rubro_info(request, rubro_id):
    """API para obtener información de un rubro"""
    try:
        rubro = Rubro.objects.get(id=rubro_id, is_active=True)
        data = {
            'success': True,
            'rubro': {
                'id': rubro.id,
                'nombre': rubro.nombre,
                'tipo_calculo': rubro.tipo_calculo,
                'porcentaje_default': rubro.porcentaje_default,
                'monto_default': rubro.monto_default,
                'descripcion': rubro.descripcion,
                'tipo_rubro': rubro.tipo_rubro.get_tipo_display(),
            }
        }
        return JsonResponse(data)
    except Rubro.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Rubro no encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def payroll_remove_rubro(request, payroll_pk, rubro_pk):
    """Eliminar rubro de nómina"""
    payroll = get_object_or_404(Payroll, pk=payroll_pk)
    rubro_aplicado = get_object_or_404(PayrollRubro, pk=rubro_pk, payroll=payroll)
    
    # Verificar que la nómina no esté pagada
    if payroll.is_paid:
        messages.error(request, 'No se puede eliminar rubros de una nómina ya pagada.')
        return redirect('payroll:payroll_detail', pk=payroll.pk)
    
    # Verificar permisos
    if not request.user.has_perm('payroll.change_payroll'):
        messages.error(request, 'No tienes permisos para eliminar rubros.')
        return redirect('payroll:payroll_detail', pk=payroll.pk)
    
    if request.method == 'POST':
        rubro_nombre = rubro_aplicado.rubro.nombre
        rubro_monto = rubro_aplicado.monto
        
        try:
            # Si es un adelanto, liberar el adelanto para que pueda ser aplicado nuevamente
            if rubro_aplicado.es_adelanto:
                # Buscar el adelanto relacionado y marcarlo como no descontado
                adelantos = AdelantoQuincena.objects.filter(
                    employee=payroll.employee,
                    monto=rubro_aplicado.monto,
                    payroll_descuento=payroll,
                    is_descontado=True
                )
                for adelanto in adelantos:
                    adelanto.is_descontado = False
                    adelanto.payroll_descuento = None
                    adelanto.save()
            
            # Eliminar el rubro
            rubro_aplicado.delete()
            
            # Mensaje de éxito
            messages.success(
                request, 
                f'Rubro "{rubro_nombre}" (${rubro_monto:.2f}) eliminado correctamente. '
                f'La nómina se ha recalculado automáticamente.'
            )
            
        except Exception as e:
            logger.error(f"Error eliminando rubro {rubro_pk} de nómina {payroll_pk}: {str(e)}")
            messages.error(request, f'Error al eliminar el rubro: {str(e)}')
        
        return redirect('payroll:payroll_detail', pk=payroll.pk)
    
    # Si es GET, mostrar confirmación (opcional, ya que lo manejamos con JavaScript)
    context = {
        'payroll': payroll,
        'rubro_aplicado': rubro_aplicado,
    }
    
    return render(request, 'pages/admin/payroll/confirm_delete_rubro.html', context)


def create_adelanto_rubro(payroll, monto, motivo, fecha_adelanto):
    """Función helper para crear rubro de adelanto"""
    
    # ✅ CORREGIDO: Los adelantos son EGRESOS (descuentos de la nómina)
    tipo_adelanto, created = TipoRubro.objects.get_or_create(
        nombre='Adelantos',
        tipo='egreso',  # <-- Cambiado a 'egreso'
        defaults={
            'descripcion': 'Adelantos de sueldo descontados a empleados',
            'is_active': True
        }
    )
    
    if created:
        logger.info(f"✅ Tipo de rubro 'Adelantos' creado como egreso")
    
    # Buscar o crear rubro específico
    rubro_adelanto, created = Rubro.objects.get_or_create(
        codigo='ADELANTO_DESC',  # Cambié el código para ser más claro
        defaults={
            'tipo_rubro': tipo_adelanto,
            'nombre': 'Descuento por Adelanto',  # Nombre más claro
            'descripcion': 'Descuento por adelanto previamente otorgado al empleado',
            'tipo_calculo': 'fijo',
            'es_obligatorio': False,
            'aplicar_automaticamente': False,
            'is_active': True
        }
    )
    
    if created:
        logger.info(f"✅ Rubro 'ADELANTO_DESC' creado")
    
    # Crear el rubro aplicado
    payroll_rubro = PayrollRubro.objects.create(
        payroll=payroll,
        rubro=rubro_adelanto,
        monto=monto,
        es_adelanto=True,
        fecha_adelanto=fecha_adelanto,
        observaciones=f'Descuento por adelanto: {motivo}' if motivo else 'Descuento por adelanto de sueldo'
    )
    
    logger.info(f"✅ PayrollRubro de adelanto creado: ${monto} descontado a {payroll.employee.user.get_full_name()}")
    return payroll_rubro

@login_required
def payroll_process_adelantos(request, pk):
    """Procesar adelantos para una nómina específica - VERSIÓN MEJORADA"""
    
    payroll = get_object_or_404(Payroll, pk=pk)
    
    # Verificar permisos
    if not (request.user.user_type in ['supervisor', 'admin'] or 
            request.user.is_superuser or 
            request.user.is_staff):
        messages.error(request, 'No tienes permisos para procesar adelantos.')
        return redirect('payroll:payroll_list')
    
    # Verificar que la nómina no esté pagada
    if payroll.is_paid:
        messages.error(request, 'No se pueden procesar adelantos en una nómina ya pagada.')
        return redirect('payroll:payroll_detail', pk=payroll.pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_new':
            # Crear nuevo adelanto
            return handle_create_new_adelanto(request, payroll)
        elif action == 'apply_existing':
            # Aplicar adelanto existente como descuento
            return handle_apply_existing_adelanto(request, payroll)
    
    # Obtener adelantos pendientes del empleado
    adelantos_pendientes = payroll.employee.adelantos_quincena.filter(
        is_descontado=False
    ).order_by('-fecha_adelanto')
    
    # Calcular total de adelantos pendientes
    total_adelantos_pendientes = adelantos_pendientes.aggregate(
        total=Sum('monto')
    )['total'] or 0
    
    context = {
        'payroll': payroll,
        'employee': payroll.employee,
        'max_adelanto': payroll.base_salary * Decimal('0.5'),
        'adelantos_pendientes': adelantos_pendientes,
        'total_adelantos_pendientes': total_adelantos_pendientes,
        'user_permissions': get_user_permissions_info(request.user)
    }
    
    return render(request, 'pages/admin/payroll/process_adelantos.html', context)


def handle_create_new_adelanto(request, payroll):
    """Manejar creación de nuevo adelanto"""
    monto = request.POST.get('monto')
    motivo = request.POST.get('motivo', '')
    
    try:
        monto = Decimal(monto)
        
        # Validaciones
        if monto <= 0:
            messages.error(request, 'El monto debe ser mayor a 0.')
            return redirect('payroll:payroll_process_adelantos', pk=payroll.pk)
        
        max_adelanto = payroll.base_salary * Decimal('0.5')
        if monto > max_adelanto:
            messages.error(
                request, 
                f'El monto no puede exceder ${max_adelanto} (50% del salario base)'
            )
            return redirect('payroll:payroll_process_adelantos', pk=payroll.pk)
        
        # Crear el adelanto
        adelanto = AdelantoQuincena.objects.create(
            employee=payroll.employee,
            monto=monto,
            fecha_adelanto=timezone.now().date(),
            motivo=motivo,
            created_by=request.user,
            is_descontado=False
        )
        
        messages.success(
            request, 
            f'✅ Adelanto de ${monto} creado exitosamente. '
            f'Podrá ser descontado en próximas nóminas.'
        )
        
        return redirect('payroll:payroll_detail', pk=payroll.pk)
        
    except (ValueError, ValidationError) as e:
        messages.error(request, f'❌ Error al crear adelanto: {str(e)}')
        return redirect('payroll:payroll_process_adelantos', pk=payroll.pk)


def handle_apply_existing_adelanto(request, payroll):
    """Manejar aplicación de adelanto existente como descuento"""
    adelanto_ids = request.POST.getlist('adelanto_ids')
    
    if not adelanto_ids:
        messages.error(request, 'Debe seleccionar al menos un adelanto para descontar.')
        return redirect('payroll:payroll_process_adelantos', pk=payroll.pk)
    
    try:
        total_descontado = 0
        adelantos_procesados = []
        
        for adelanto_id in adelanto_ids:
            adelanto = AdelantoQuincena.objects.get(
                id=adelanto_id,
                employee=payroll.employee,
                is_descontado=False
            )
            
            # Crear rubro de descuento
            create_adelanto_rubro(payroll, adelanto.monto, adelanto.motivo, adelanto.fecha_adelanto)
            
            # Marcar adelanto como descontado
            adelanto.is_descontado = True
            adelanto.payroll_descuento = payroll
            adelanto.save()
            
            total_descontado += adelanto.monto
            adelantos_procesados.append(adelanto)
        
        messages.success(
            request,
            f'✅ Se descontaron {len(adelantos_procesados)} adelantos por un total de ${total_descontado}. '
            f'La nómina se ha recalculado automáticamente.'
        )
        
        return redirect('payroll:payroll_detail', pk=payroll.pk)
        
    except AdelantoQuincena.DoesNotExist:
        messages.error(request, 'Adelanto no encontrado o ya fue descontado.')
        return redirect('payroll:payroll_process_adelantos', pk=payroll.pk)
    except Exception as e:
        messages.error(request, f'❌ Error al procesar adelantos: {str(e)}')
        return redirect('payroll:payroll_process_adelantos', pk=payroll.pk)
    
def get_user_type_display(user):
    """Obtener descripción amigable del tipo de usuario"""
    if user.is_superuser:
        return f"{user.get_full_name()} (Superusuario)"
    elif hasattr(user, 'user_type') and user.user_type == 'admin':
        return f"{user.get_full_name()} (Administrador)"
    elif hasattr(user, 'user_type') and user.user_type == 'supervisor':
        return f"{user.get_full_name()} (Supervisor)"
    elif user.is_staff:
        return f"{user.get_full_name()} (Staff)"
    else:
        return f"{user.get_full_name()} (Usuario)"


def get_user_permissions_info(user):
    """Obtener información detallada de permisos del usuario"""
    user_type = getattr(user, 'user_type', 'employee')
    
    return {
        'is_superuser': user.is_superuser,
        'is_staff': user.is_staff,
        'user_type': user_type,
        'can_process_adelantos': (
            user_type in ['supervisor', 'admin'] or 
            user.is_superuser or 
            user.is_staff
        ),
        'can_edit_payroll': (
            user_type in ['supervisor', 'admin'] or 
            user.is_superuser or 
            user.is_staff or
            user.has_perm('payroll.change_payroll')
        ),
        'can_view_payroll': (
            user_type in ['supervisor', 'admin', 'employee'] or 
            user.is_superuser or 
            user.is_staff or
            user.has_perm('payroll.view_payroll')
        ),
        'can_delete_payroll': (
            user_type in ['admin'] or 
            user.is_superuser or
            user.has_perm('payroll.delete_payroll')
        ),
        'user_display': get_user_type_display(user)
    }


def can_user_process_adelantos(user):
    """
    Función utilitaria para verificar si un usuario puede procesar adelantos
    Reutilizable en otras vistas
    """
    user_type = getattr(user, 'user_type', 'employee')
    return (
        user_type in ['supervisor', 'admin'] or 
        user.is_superuser or 
        user.is_staff
    )


@login_required
def payroll_mark_paid(request, pk):
    """Marcar nómina como pagada y enviar notificación por email"""
    payroll = get_object_or_404(Payroll, pk=pk)
    
    if request.method == 'POST':
        payroll.is_paid = True
        payroll.payment_date = timezone.now().date()
        payroll.payment_method = request.POST.get('payment_method', 'Transferencia bancaria')
        payroll.save()
        
        # Preparar datos para el email usando los nuevos campos y métodos
        payroll_data = {
            'period': payroll.period.name,
            'period_full': f"{payroll.period.start_date.strftime('%d/%m/%Y')} - {payroll.period.end_date.strftime('%d/%m/%Y')}",
            'base_salary': payroll.base_salary,
            'overtime_pay': payroll.overtime_pay,
            'bonus': 0,  # Ya no existe, se maneja por rubros
            'commission': 0,  # Ya no existe, se maneja por rubros
            'allowances': 0,  # Ya no existe, se maneja por rubros
            'gross_pay': payroll.gross_pay,
            'income_tax': 0,  # Ya no existe, se maneja por rubros
            'social_security': 0,  # Ya no existe, se maneja por rubros
            'health_insurance': 0,  # Ya no existe, se maneja por rubros
            'other_deductions': 0,  # Ya no existe, se maneja por rubros
            'total_deductions': payroll.total_deductions,
            'net_pay': payroll.net_pay,
            'payment_date': payroll.payment_date,
            'payment_method': payroll.payment_method,
            'payroll_id': payroll.id,
        }
        
        # Obtener rubros adicionales
        ingresos_adicionales = payroll.rubros_aplicados.filter(
            rubro__tipo_rubro__tipo='ingreso'
        ).select_related('rubro')
        
        egresos_adicionales = payroll.rubros_aplicados.filter(
            rubro__tipo_rubro__tipo='egreso'
        ).select_related('rubro')
        
        payroll_data['ingresos_adicionales'] = [
            {
                'nombre': rubro.rubro.nombre,
                'monto': rubro.monto,
                'observaciones': rubro.observaciones
            }
            for rubro in ingresos_adicionales
        ]
        
        payroll_data['egresos_adicionales'] = [
            {
                'nombre': rubro.rubro.nombre,
                'monto': rubro.monto,
                'observaciones': rubro.observaciones,
                'es_adelanto': rubro.es_adelanto,
                'fecha_adelanto': rubro.fecha_adelanto
            }
            for rubro in egresos_adicionales
        ]
        
        # Enviar notificación por email
        try:
            email_sent = send_payroll_notification_email(payroll.employee, payroll_data)
            if email_sent:
                messages.success(
                    request, 
                    f'Nómina marcada como pagada y notificación enviada a {payroll.employee.user.email}.'
                )
            else:
                messages.warning(
                    request, 
                    'Nómina marcada como pagada, pero no se pudo enviar la notificación por email. '
                    'Verifique la configuración de email.'
                )
        except Exception as e:
            logger.error(f"Error enviando notificación de pago: {str(e)}")
            messages.warning(
                request, 
                f'Nómina marcada como pagada, pero ocurrió un error al enviar la notificación: {str(e)}'
            )
        
        return redirect('payroll:payroll_detail', pk=payroll.pk)
    
    return redirect('payroll:payroll_detail', pk=pk)


@login_required
def payroll_bulk_mark_paid(request):
    """Marcar múltiples nóminas como pagadas"""
    if request.method == 'POST':
        payroll_ids = request.POST.getlist('payroll_ids')
        payment_method = request.POST.get('payment_method', 'Transferencia bancaria')
        
        success_count = 0
        email_success_count = 0
        
        for payroll_id in payroll_ids:
            try:
                payroll = Payroll.objects.get(id=payroll_id)
                
                if not payroll.is_paid:  # Solo procesar si no está pagada
                    payroll.is_paid = True
                    payroll.payment_date = timezone.now().date()
                    payroll.payment_method = payment_method
                    payroll.save()
                    success_count += 1
                    
                    # Preparar datos para el email usando los nuevos campos
                    payroll_data = {
                        'period': payroll.period.name,
                        'period_full': f"{payroll.period.start_date.strftime('%d/%m/%Y')} - {payroll.period.end_date.strftime('%d/%m/%Y')}",
                        'base_salary': payroll.base_salary,
                        'overtime_pay': payroll.overtime_pay,
                        'bonus': 0,  # Ya no existe, se maneja por rubros
                        'commission': 0,  # Ya no existe, se maneja por rubros
                        'allowances': 0,  # Ya no existe, se maneja por rubros
                        'gross_pay': payroll.gross_pay,
                        'income_tax': 0,  # Ya no existe, se maneja por rubros
                        'social_security': 0,  # Ya no existe, se maneja por rubros
                        'health_insurance': 0,  # Ya no existe, se maneja por rubros
                        'other_deductions': 0,  # Ya no existe, se maneja por rubros
                        'total_deductions': payroll.total_deductions,
                        'net_pay': payroll.net_pay,
                        'payment_date': payroll.payment_date,
                        'payment_method': payroll.payment_method,
                        'payroll_id': payroll.id,
                    }
                    
                    # Obtener rubros adicionales
                    ingresos_adicionales = payroll.rubros_aplicados.filter(
                        rubro__tipo_rubro__tipo='ingreso'
                    ).select_related('rubro')
                    
                    egresos_adicionales = payroll.rubros_aplicados.filter(
                        rubro__tipo_rubro__tipo='egreso'
                    ).select_related('rubro')
                    
                    payroll_data['ingresos_adicionales'] = [
                        {
                            'nombre': rubro.rubro.nombre,
                            'monto': rubro.monto,
                            'observaciones': rubro.observaciones
                        }
                        for rubro in ingresos_adicionales
                    ]
                    
                    payroll_data['egresos_adicionales'] = [
                        {
                            'nombre': rubro.rubro.nombre,
                            'monto': rubro.monto,
                            'observaciones': rubro.observaciones,
                            'es_adelanto': rubro.es_adelanto,
                            'fecha_adelanto': rubro.fecha_adelanto
                        }
                        for rubro in egresos_adicionales
                    ]
                    
                    try:
                        if send_payroll_notification_email(payroll.employee, payroll_data):
                            email_success_count += 1
                    except Exception as e:
                        logger.error(f"Error enviando email a {payroll.employee.user.email}: {str(e)}")
                
            except Payroll.DoesNotExist:
                logger.warning(f"Nómina con ID {payroll_id} no encontrada")
            except Exception as e:
                logger.error(f"Error procesando nómina {payroll_id}: {str(e)}")
        
        if success_count > 0:
            messages.success(
                request, 
                f'Se marcaron {success_count} nóminas como pagadas. '
                f'Se enviaron {email_success_count} notificaciones por email.'
            )
        else:
            messages.warning(request, 'No se procesaron nóminas.')
        
        return redirect('payroll:payroll_list')
    
    return redirect('payroll:payroll_list')