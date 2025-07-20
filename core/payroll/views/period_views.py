# core/payroll/views/period_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from ..models import PayrollPeriod, Payroll, Rubro, PayrollRubro
from ..forms.period_forms import PayrollPeriodForm
from core.employees.models import Employee
import csv
import io
import logging

logger = logging.getLogger(__name__)


@login_required
def period_list(request):
    """Lista de períodos de nómina"""
    periods = PayrollPeriod.objects.all().order_by('-created_at')
    
    # Filtros
    status = request.GET.get('status')
    period_type = request.GET.get('period_type')
    search = request.GET.get('search')
    
    if status:
        periods = periods.filter(status=status)
    
    if period_type:
        periods = periods.filter(period_type=period_type)
    
    if search:
        periods = periods.filter(name__icontains=search)
    
    paginator = Paginator(periods, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'current_filters': {
            'status': status,
            'period_type': period_type,
            'search': search,
        }
    }
    
    return render(request, 'pages/admin/periods/list.html', context)

def create_biweekly_periods(name, start_date, end_date, pay_date, created_by):
    """
    Crear automáticamente dos períodos quincenales a partir de un rango mensual
    """
    from datetime import datetime, timedelta
    from calendar import monthrange
    
    # Calcular fechas de las quincenas
    year = start_date.year
    month = start_date.month
    
    # Primera quincena: día 1 al 15
    first_start = start_date.replace(day=1)
    first_end = start_date.replace(day=15)
    
    # Segunda quincena: día 16 al último día del mes
    last_day = monthrange(year, month)[1]
    second_start = start_date.replace(day=16)
    second_end = start_date.replace(day=last_day)
    
    # Calcular fechas de pago (por ejemplo, 5 días después del fin de cada quincena)
    first_pay_date = first_end + timedelta(days=5)
    second_pay_date = second_end + timedelta(days=5)
    
    # Crear los dos períodos
    period_1 = PayrollPeriod.objects.create(
        name=f"1ra Quincena - {start_date.strftime('%B %Y')}",
        period_type='biweekly',
        start_date=first_start,
        end_date=first_end,
        pay_date=first_pay_date,
        status='draft',
        created_by=created_by,
        notes=f"Primera quincena generada automáticamente del período: {name}"
    )
    
    period_2 = PayrollPeriod.objects.create(
        name=f"2da Quincena - {start_date.strftime('%B %Y')}",
        period_type='biweekly',
        start_date=second_start,
        end_date=second_end,
        pay_date=second_pay_date,
        status='draft',
        created_by=created_by,
        notes=f"Segunda quincena generada automáticamente del período: {name}"
    )
    
    return period_1, period_2


@login_required
def period_form(request, pk=None):
    """Crear o editar período de nómina con soporte quincenal OPTIMIZADO"""
    period = get_object_or_404(PayrollPeriod, pk=pk) if pk else None
    
    if request.method == 'POST':
        form = PayrollPeriodForm(request.POST, instance=period)
        if form.is_valid():
            period_data = form.cleaned_data
            
            # Si es quincenal y es creación nueva, crear automáticamente las dos quincenas
            if (period_data['period_type'] == 'biweekly' and not pk):
                try:
                    period_1, period_2 = create_biweekly_periods(
                        name=period_data['name'],
                        start_date=period_data['start_date'],
                        end_date=period_data['end_date'],
                        pay_date=period_data['pay_date'],
                        created_by=request.user
                    )
                    
                    messages.success(
                        request, 
                        f'✅ ¡Períodos quincenales creados exitosamente!\n\n'
                        f'📅 {period_1.name}: {period_1.start_date.strftime("%d/%m")} - {period_1.end_date.strftime("%d/%m/%Y")}\n'
                        f'📅 {period_2.name}: {period_2.start_date.strftime("%d/%m")} - {period_2.end_date.strftime("%d/%m/%Y")}\n\n'
                        f'💰 Los salarios y rubros se dividirán automáticamente entre 2.'
                    )
                    
                    # Redirigir a la lista con filtro de búsqueda para mostrar ambos períodos
                    return redirect(f"{reverse('payroll:period_list')}?search={period_data['start_date'].strftime('%B %Y')}")
                
                except Exception as e:
                    messages.error(request, f'Error creando períodos quincenales: {str(e)}')
                    return redirect('payroll:period_list')
            
            else:
                # Creación/edición normal
                period = form.save(commit=False)
                if not pk:
                    period.created_by = request.user
                period.save()
                
                messages.success(request, 'Período guardado correctamente.')
                return redirect('payroll:period_detail', pk=period.pk)
        else:
            messages.error(request, 'Error al guardar el período.')
    else:
        form = PayrollPeriodForm(instance=period)
    
    context = {
        'form': form,
        'period': period,
        'is_edit': pk is not None,
    }
    
    return render(request, 'pages/admin/periods/form.html', context)


@login_required
def period_detail(request, pk):
    """Detalle del período con nóminas - CORREGIDO"""
    period = get_object_or_404(PayrollPeriod, pk=pk)
    payrolls = period.payroll_entries.select_related(
        'employee__user', 
        'employee__department', 
        'employee__position'
    ).prefetch_related('rubros_aplicados__rubro').all()
    
    # ✅ CORREGIDO: Calcular totales correctamente
    total_gross_pay = sum(payroll.gross_pay for payroll in payrolls)
    total_net_pay = sum(payroll.net_pay for payroll in payrolls)
    total_deductions = sum(payroll.total_deductions for payroll in payrolls)
    
    # ✅ NUEVO: Verificar si todas las nóminas están pagadas y actualizar estado
    if payrolls.exists():
        all_paid = all(payroll.is_paid for payroll in payrolls)
        
        # Si todas están pagadas y el período no está en estado "paid", actualizarlo
        if all_paid and period.status != 'paid':
            period.status = 'paid'
            period.save()
            messages.success(
                request, 
                '✅ Todas las nóminas están pagadas. El período se marcó automáticamente como "Pagado".'
            )
    
    context = {
        'period': period,
        'payrolls': payrolls,
        'total_employees': payrolls.count(),
        'total_gross_pay': total_gross_pay,
        'total_net_pay': total_net_pay,
        'total_deductions': total_deductions,
    }
    
    return render(request, 'pages/admin/periods/detail.html', context)

def update_period_status_if_needed(period):
    """Actualizar estado del período basado en el estado de las nóminas"""
    payrolls = period.payroll_entries.all()
    
    if not payrolls.exists():
        # No hay nóminas, mantener en draft
        if period.status != 'draft':
            period.status = 'draft'
            period.save()
        return
    
    all_paid = all(payroll.is_paid for payroll in payrolls)
    
    if all_paid and period.status != 'paid':
        # Todas las nóminas están pagadas
        period.status = 'paid'
        period.save()
        logger.info(f"Período {period.name} marcado automáticamente como 'paid'")
    elif not all_paid and period.status == 'paid':
        # Si alguna nómina no está pagada, volver a processing
        period.status = 'processing'
        period.save()
        logger.info(f"Período {period.name} vuelto a 'processing' porque hay nóminas sin pagar")
        

@login_required
def period_mark_all_paid(request, pk):
    """Marcar todas las nóminas de un período como pagadas"""
    period = get_object_or_404(PayrollPeriod, pk=pk)
    
    if request.method == 'POST':
        unpaid_payrolls = period.payroll_entries.filter(is_paid=False)
        
        if not unpaid_payrolls.exists():
            messages.info(request, 'Todas las nóminas ya están marcadas como pagadas.')
            return redirect('payroll:period_detail', pk=pk)
        
        # Marcar todas como pagadas
        payment_date = timezone.now().date()
        payment_method = request.POST.get('payment_method', 'Transferencia bancaria')
        
        updated_count = 0
        for payroll in unpaid_payrolls:
            payroll.is_paid = True
            payroll.payment_date = payment_date
            payroll.payment_method = payment_method
            payroll.save()
            updated_count += 1
        
        # Actualizar estado del período
        period.status = 'paid'
        period.save()
        
        messages.success(
            request,
            f'✅ Se marcaron {updated_count} nóminas como pagadas. '
            f'El período se actualizó automáticamente a "Pagado".'
        )
    
    return redirect('payroll:period_detail', pk=pk)
        

@login_required
def period_form(request, pk=None):
    """Crear o editar período de nómina con soporte quincenal OPTIMIZADO"""
    period = get_object_or_404(PayrollPeriod, pk=pk) if pk else None
    
    if request.method == 'POST':
        form = PayrollPeriodForm(request.POST, instance=period)
        if form.is_valid():
            period_data = form.cleaned_data
            
            # Si es quincenal y es creación nueva, crear automáticamente las dos quincenas
            if (period_data['period_type'] == 'biweekly' and not pk):
                try:
                    period_1, period_2 = create_biweekly_periods(
                        name=period_data['name'],
                        start_date=period_data['start_date'],
                        end_date=period_data['end_date'],
                        pay_date=period_data['pay_date'],
                        created_by=request.user
                    )
                    
                    messages.success(
                        request, 
                        f'✅ ¡Períodos quincenales creados exitosamente!\n\n'
                        f'📅 {period_1.name}: {period_1.start_date.strftime("%d/%m")} - {period_1.end_date.strftime("%d/%m/%Y")}\n'
                        f'📅 {period_2.name}: {period_2.start_date.strftime("%d/%m")} - {period_2.end_date.strftime("%d/%m/%Y")}\n\n'
                        f'💰 Los salarios y rubros se dividirán automáticamente entre 2.'
                    )
                    
                    # Redirigir a la lista con filtro de búsqueda para mostrar ambos períodos
                    return redirect(f"{reverse('payroll:period_list')}?search={period_data['start_date'].strftime('%B %Y')}")
                
                except Exception as e:
                    messages.error(request, f'Error creando períodos quincenales: {str(e)}')
                    return redirect('payroll:period_list')
            
            else:
                # Creación/edición normal
                period = form.save(commit=False)
                if not pk:
                    period.created_by = request.user
                period.save()
                
                messages.success(request, 'Período guardado correctamente.')
                return redirect('payroll:period_detail', pk=period.pk)
        else:
            messages.error(request, 'Error al guardar el período.')
    else:
        form = PayrollPeriodForm(instance=period)
    
    context = {
        'form': form,
        'period': period,
        'is_edit': pk is not None,
    }
    
    return render(request, 'pages/admin/periods/form.html', context)


@login_required
def period_generate_payrolls(request, pk):
    """Generar nóminas MEJORADO para soportar quincenas"""
    period = get_object_or_404(PayrollPeriod, pk=pk)
    
    if period.status not in ['draft', 'processing']:
        messages.error(request, 'Solo se pueden generar nóminas en períodos en borrador o procesamiento.')
        return redirect('payroll:period_detail', pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'generate':
            # Detectar si es quincenal y ajustar la generación
            if period.period_type == 'biweekly':
                return _generate_biweekly_payrolls(request, period)
            else:
                return _generate_payrolls(request, period)
        elif action == 'generate_report':
            return _generate_payrolls_html_report(request, period)
        elif action == 'export_csv':
            return _export_payrolls_csv(request, period)
        elif action == 'export_pdf':
            return _generate_payrolls_html_report(request, period)
    
    # Obtener empleados activos
    active_employees = Employee.objects.filter(status='active').select_related(
        'user', 'department', 'position'
    )
    
    # Obtener IDs de empleados que ya tienen nómina en este período
    existing_payroll_employee_ids = set(
        period.payroll_entries.values_list('employee_id', flat=True)
    )
    
    # Marcar empleados que ya tienen nómina
    for employee in active_employees:
        employee.has_payroll = employee.id in existing_payroll_employee_ids
    
    # Obtener rubros automáticos
    automatic_rubros = Rubro.objects.filter(
        aplicar_automaticamente=True, 
        is_active=True
    ).select_related('tipo_rubro')
    
    # Calcular estimados basados en rubros reales
    total_salary = sum(emp.salary or 0 for emp in active_employees)
    
    # AJUSTAR CÁLCULOS PARA QUINCENAS
    salary_divisor = 2 if period.period_type == 'biweekly' else 1
    adjusted_total_salary = total_salary / salary_divisor
    
    # Calcular deducciones estimadas
    estimated_deductions = calculate_estimated_deductions(adjusted_total_salary, automatic_rubros)
    estimated_additional_income = calculate_estimated_additional_income(adjusted_total_salary, automatic_rubros)
    
    # Calcular totales estimados
    estimated_gross = adjusted_total_salary + estimated_additional_income
    estimated_net = estimated_gross - estimated_deductions
    
    # Calcular empleados pendientes
    pending_employees_count = max(0, active_employees.count() - period.payroll_entries.count())
    
    # Calcular promedios por empleado
    employee_count = active_employees.count()
    if employee_count > 0:
        average_gross_per_employee = estimated_gross / employee_count
        average_deductions_per_employee = estimated_deductions / employee_count
        average_net_per_employee = estimated_net / employee_count
    else:
        average_gross_per_employee = 0
        average_deductions_per_employee = 0
        average_net_per_employee = 0
    
    context = {
        'period': period,
        'active_employees': active_employees,
        'active_employees_count': active_employees.count(),
        'existing_payrolls_count': period.payroll_entries.count(),
        'pending_employees_count': pending_employees_count,
        'automatic_rubros': automatic_rubros,
        'can_generate': period.status in ['draft', 'processing'],
        
        # INFORMACIÓN ESPECÍFICA PARA QUINCENAS
        'is_biweekly': period.period_type == 'biweekly',
        'salary_divisor': salary_divisor,
        'period_label': f"quincena ({salary_divisor}ª parte del salario mensual)" if salary_divisor == 2 else "mes completo",
        
        # Cálculos estimados ajustados
        'total_estimated_salary': adjusted_total_salary,
        'estimated_additional_income': estimated_additional_income,
        'estimated_gross': estimated_gross,
        'estimated_deductions': estimated_deductions,
        'estimated_net': estimated_net,
        
        # Promedios por empleado
        'average_gross_per_employee': average_gross_per_employee,
        'average_deductions_per_employee': average_deductions_per_employee,
        'average_net_per_employee': average_net_per_employee,
        
        # Desglose para mostrar en template
        'deductions_breakdown': get_deductions_breakdown(adjusted_total_salary, automatic_rubros),
        'income_breakdown': get_income_breakdown(adjusted_total_salary, automatic_rubros),
    }
    
    return render(request, 'pages/admin/periods/generate_payrolls.html', context)


def _generate_biweekly_payrolls(request, period):
    """Generar nóminas específicamente para períodos quincenales"""
    with transaction.atomic():
        employees = Employee.objects.filter(status='active').select_related('user')
        created_count = 0
        updated_count = 0
        errors = []
        
        # Determinar número de quincena basado en las fechas
        quincena_numero = 1 if period.start_date.day <= 15 else 2
        
        for employee in employees:
            try:
                # Verificar si ya existe nómina
                payroll, created = Payroll.objects.get_or_create(
                    employee=employee,
                    period=period,
                    defaults={
                        'base_salary': getattr(employee, 'salary', 0) or 0,
                        'quincena_numero': quincena_numero,  # NUEVO CAMPO
                        'created_by': request.user,
                    }
                )
                
                if created:
                    # Aplicar rubros automáticos (ya se ajustarán por el divisor)
                    payroll.aplicar_rubros_automaticos()
                    payroll.aplicar_deducciones_legales()
                    created_count += 1
                    logger.info(f"Nómina quincenal creada para {employee.user.get_full_name()} - Quincena {quincena_numero}")
                else:
                    # Actualizar si es necesario
                    if hasattr(employee, 'salary') and employee.salary != payroll.base_salary:
                        payroll.base_salary = employee.salary
                        payroll.quincena_numero = quincena_numero
                        payroll.save()
                        updated_count += 1
                
            except Exception as e:
                error_msg = f"Error con {employee.user.get_full_name()}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Actualizar estado del período
        if period.status == 'draft':
            period.status = 'processing'
            period.save()
        
        # Mensajes específicos para quincenas
        if created_count > 0:
            messages.success(
                request, 
                f'✅ Se crearon {created_count} nóminas quincenales correctamente.\n'
                f'💰 Salarios y rubros divididos automáticamente entre 2.\n'
                f'📅 Quincena #{quincena_numero} del período {period.name}'
            )
        
        if updated_count > 0:
            messages.info(request, f'Se actualizaron {updated_count} nóminas existentes.')
        
        if errors:
            for error in errors[:5]:
                messages.error(request, error)
            
            if len(errors) > 5:
                messages.error(request, f'Y {len(errors) - 5} errores adicionales.')
    
    return redirect('payroll:period_detail', pk=period.pk)


@login_required
def period_generate_payrolls(request, pk):
    """Generar nóminas MEJORADO para soportar quincenas"""
    period = get_object_or_404(PayrollPeriod, pk=pk)
    
    if period.status not in ['draft', 'processing']:
        messages.error(request, 'Solo se pueden generar nóminas en períodos en borrador o procesamiento.')
        return redirect('payroll:period_detail', pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'generate':
            # Detectar si es quincenal y ajustar la generación
            if period.period_type == 'biweekly':
                return _generate_biweekly_payrolls(request, period)
            else:
                return _generate_payrolls(request, period)
        elif action == 'generate_report':
            return _generate_payrolls_html_report(request, period)
        elif action == 'export_csv':
            return _export_payrolls_csv(request, period)
        elif action == 'export_pdf':
            return _generate_payrolls_html_report(request, period)
    
    # Obtener empleados activos
    active_employees = Employee.objects.filter(status='active').select_related(
        'user', 'department', 'position'
    )
    
    # Obtener IDs de empleados que ya tienen nómina en este período
    existing_payroll_employee_ids = set(
        period.payroll_entries.values_list('employee_id', flat=True)
    )
    
    # Marcar empleados que ya tienen nómina
    for employee in active_employees:
        employee.has_payroll = employee.id in existing_payroll_employee_ids
    
    # Obtener rubros automáticos
    automatic_rubros = Rubro.objects.filter(
        aplicar_automaticamente=True, 
        is_active=True
    ).select_related('tipo_rubro')
    
    # Calcular estimados basados en rubros reales
    total_salary = sum(emp.salary or 0 for emp in active_employees)
    
    # AJUSTAR CÁLCULOS PARA QUINCENAS
    salary_divisor = 2 if period.period_type == 'biweekly' else 1
    adjusted_total_salary = total_salary / salary_divisor
    
    # Calcular deducciones estimadas
    estimated_deductions = calculate_estimated_deductions(adjusted_total_salary, automatic_rubros)
    estimated_additional_income = calculate_estimated_additional_income(adjusted_total_salary, automatic_rubros)
    
    # Calcular totales estimados
    estimated_gross = adjusted_total_salary + estimated_additional_income
    estimated_net = estimated_gross - estimated_deductions
    
    # Calcular empleados pendientes
    pending_employees_count = max(0, active_employees.count() - period.payroll_entries.count())
    
    # Calcular promedios por empleado
    employee_count = active_employees.count()
    if employee_count > 0:
        average_gross_per_employee = estimated_gross / employee_count
        average_deductions_per_employee = estimated_deductions / employee_count
        average_net_per_employee = estimated_net / employee_count
    else:
        average_gross_per_employee = 0
        average_deductions_per_employee = 0
        average_net_per_employee = 0
    
    context = {
        'period': period,
        'active_employees': active_employees,
        'active_employees_count': active_employees.count(),
        'existing_payrolls_count': period.payroll_entries.count(),
        'pending_employees_count': pending_employees_count,
        'automatic_rubros': automatic_rubros,
        'can_generate': period.status in ['draft', 'processing'],
        
        # INFORMACIÓN ESPECÍFICA PARA QUINCENAS
        'is_biweekly': period.period_type == 'biweekly',
        'salary_divisor': salary_divisor,
        'period_label': f"quincena ({salary_divisor}ª parte del salario mensual)" if salary_divisor == 2 else "mes completo",
        
        # Cálculos estimados ajustados
        'total_estimated_salary': adjusted_total_salary,
        'estimated_additional_income': estimated_additional_income,
        'estimated_gross': estimated_gross,
        'estimated_deductions': estimated_deductions,
        'estimated_net': estimated_net,
        
        # Promedios por empleado
        'average_gross_per_employee': average_gross_per_employee,
        'average_deductions_per_employee': average_deductions_per_employee,
        'average_net_per_employee': average_net_per_employee,
        
        # Desglose para mostrar en template
        'deductions_breakdown': get_deductions_breakdown(adjusted_total_salary, automatic_rubros),
        'income_breakdown': get_income_breakdown(adjusted_total_salary, automatic_rubros),
    }
    
    return render(request, 'pages/admin/periods/generate_payrolls.html', context)


def calculate_estimated_deductions(total_salary, automatic_rubros):
    """Calcular deducciones estimadas basadas en rubros automáticos"""
    total_deductions = 0
    
    for rubro in automatic_rubros:
        if rubro.tipo_rubro.tipo == 'egreso':  # Solo egresos/deducciones
            if rubro.tipo_calculo == 'fijo':
                # Monto fijo aplicado a todos los empleados
                employee_count = Employee.objects.filter(status='active').count()
                total_deductions += (rubro.monto_default or 0) * employee_count
                
            elif rubro.tipo_calculo == 'porcentaje':
                # Porcentaje del salario base
                if rubro.porcentaje_default:
                    total_deductions += total_salary * (rubro.porcentaje_default / 100)
                    
            elif rubro.tipo_calculo == 'porcentaje_bruto':
                # Porcentaje del salario bruto (aproximado como salario base para estimado)
                if rubro.porcentaje_default:
                    total_deductions += total_salary * (rubro.porcentaje_default / 100)
    
    return total_deductions


def calculate_estimated_additional_income(total_salary, automatic_rubros):
    """Calcular ingresos adicionales estimados basados en rubros automáticos"""
    total_additional_income = 0
    
    for rubro in automatic_rubros:
        if rubro.tipo_rubro.tipo == 'ingreso':  # Solo ingresos
            if rubro.tipo_calculo == 'fijo':
                # Monto fijo aplicado a todos los empleados
                employee_count = Employee.objects.filter(status='active').count()
                total_additional_income += (rubro.monto_default or 0) * employee_count
                
            elif rubro.tipo_calculo == 'porcentaje':
                # Porcentaje del salario base
                if rubro.porcentaje_default:
                    total_additional_income += total_salary * (rubro.porcentaje_default / 100)
                    
            elif rubro.tipo_calculo == 'porcentaje_bruto':
                # Porcentaje del salario bruto (aproximado como salario base para estimado)
                if rubro.porcentaje_default:
                    total_additional_income += total_salary * (rubro.porcentaje_default / 100)
    
    return total_additional_income


def get_deductions_breakdown(total_salary, automatic_rubros):
    """Obtener desglose de deducciones para mostrar en template"""
    breakdown = []
    
    for rubro in automatic_rubros:
        if rubro.tipo_rubro.tipo == 'egreso':
            amount = 0
            description = ""
            
            if rubro.tipo_calculo == 'fijo':
                employee_count = Employee.objects.filter(status='active').count()
                amount = (rubro.monto_default or 0) * employee_count
                description = f"${rubro.monto_default or 0} × {employee_count} empleados"
                
            elif rubro.tipo_calculo in ['porcentaje', 'porcentaje_bruto']:
                if rubro.porcentaje_default:
                    amount = total_salary * (rubro.porcentaje_default / 100)
                    description = f"{rubro.porcentaje_default}% de salarios"
            
            if amount > 0:
                breakdown.append({
                    'name': rubro.nombre,
                    'amount': amount,
                    'description': description,
                    'code': rubro.codigo
                })
    
    return breakdown


def get_income_breakdown(total_salary, automatic_rubros):
    """Obtener desglose de ingresos adicionales para mostrar en template"""
    breakdown = []
    
    for rubro in automatic_rubros:
        if rubro.tipo_rubro.tipo == 'ingreso':
            amount = 0
            description = ""
            
            if rubro.tipo_calculo == 'fijo':
                employee_count = Employee.objects.filter(status='active').count()
                amount = (rubro.monto_default or 0) * employee_count
                description = f"${rubro.monto_default or 0} × {employee_count} empleados"
                
            elif rubro.tipo_calculo in ['porcentaje', 'porcentaje_bruto']:
                if rubro.porcentaje_default:
                    amount = total_salary * (rubro.porcentaje_default / 100)
                    description = f"{rubro.porcentaje_default}% de salarios"
            
            if amount > 0:
                breakdown.append({
                    'name': rubro.nombre,
                    'amount': amount,
                    'description': description,
                    'code': rubro.codigo
                })
    
    return breakdown


def _generate_payrolls(request, period):
    """Generar nóminas individuales"""
    with transaction.atomic():
        employees = Employee.objects.filter(status='active').select_related('user')
        created_count = 0
        updated_count = 0
        errors = []
        
        for employee in employees:
            try:
                # Verificar si ya existe nómina
                payroll, created = Payroll.objects.get_or_create(
                    employee=employee,
                    period=period,
                    defaults={
                        'base_salary': getattr(employee, 'salary', 0) or 0,
                        'created_by': request.user,
                    }
                )
                
                if created:
                    # Aplicar rubros automáticos
                    payroll.aplicar_rubros_automaticos()
                    payroll.aplicar_deducciones_legales()
                    created_count += 1
                    logger.info(f"Nómina creada para {employee.user.get_full_name()}")
                else:
                    # Actualizar salario base si cambió
                    if hasattr(employee, 'salary') and employee.salary != payroll.base_salary:
                        payroll.base_salary = employee.salary
                        payroll.save()
                        updated_count += 1
                
            except Exception as e:
                error_msg = f"Error con {employee.user.get_full_name()}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Actualizar estado del período
        if period.status == 'draft':
            period.status = 'processing'
            period.save()
        
        # Mensajes de resultado
        if created_count > 0:
            messages.success(request, f'Se crearon {created_count} nóminas correctamente.')
        
        if updated_count > 0:
            messages.info(request, f'Se actualizaron {updated_count} nóminas existentes.')
        
        if errors:
            for error in errors[:5]:  # Mostrar máximo 5 errores
                messages.error(request, error)
            
            if len(errors) > 5:
                messages.error(request, f'Y {len(errors) - 5} errores adicionales.')
    
    return redirect('payroll:period_detail', pk=period.pk)


def _generate_payrolls_html_report(request, period):
    """Generar reporte HTML que se puede imprimir como PDF"""
    payrolls = period.payroll_entries.select_related(
        'employee__user', 
        'employee__department', 
        'employee__position'
    ).prefetch_related('rubros_aplicados__rubro__tipo_rubro').all()
    
    if not payrolls.exists():
        messages.warning(request, 'No hay nóminas en este período para generar reporte.')
        return redirect('payroll:period_detail', pk=period.pk)
    
    # Calcular totales
    total_gross = sum(p.gross_pay for p in payrolls)
    total_deductions = sum(p.total_deductions for p in payrolls)
    total_net = sum(p.net_pay for p in payrolls)
    
    context = {
        'period': period,
        'payrolls': payrolls,
        'total_gross': total_gross,
        'total_deductions': total_deductions,
        'total_net': total_net,
        'generation_date': timezone.now(),
        'is_print_view': True,
    }
    
    # Crear respuesta HTML para imprimir
    response = HttpResponse(content_type='text/html')
    response['Content-Disposition'] = f'inline; filename="reporte_nominas_{period.name.replace(" ", "_")}.html"'
    
    html_content = render_to_string('pages/admin/periods/payroll_report.html', context)
    response.write(html_content)
    
    logger.info(f"Reporte HTML generado para período {period.name} por usuario {request.user.username}")
    return response


def _export_payrolls_csv(request, period):
    """Exportar nóminas a CSV"""
    payrolls = period.payroll_entries.select_related(
        'employee__user', 
        'employee__department', 
        'employee__position'
    ).prefetch_related('rubros_aplicados__rubro').all()
    
    if not payrolls.exists():
        messages.warning(request, 'No hay nóminas en este período para exportar.')
        return redirect('payroll:period_detail', pk=period.pk)
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="nominas_{period.name.replace(" ", "_")}.csv"'
    
    # Agregar BOM para UTF-8 (para Excel)
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # Encabezados
    headers = [
        'ID Nómina', 'Empleado', 'Número Empleado', 'Departamento', 'Cargo',
        'Email', 'Salario Base', 'Horas Extra', 'Pago Horas Extra',
        'Pago Bruto', 'Total Deducciones', 'Pago Neto',
        'Estado Pago', 'Fecha Pago', 'Método Pago', 'Rubros Adicionales'
    ]
    writer.writerow(headers)
    
    # Datos
    for payroll in payrolls:
        # Obtener rubros adicionales
        rubros_adicionales = []
        for rubro_aplicado in payroll.rubros_aplicados.all():
            tipo_signo = "+" if rubro_aplicado.rubro.tipo_rubro.tipo == 'ingreso' else "-"
            rubros_adicionales.append(f"{rubro_aplicado.rubro.nombre}: {tipo_signo}${rubro_aplicado.monto:.2f}")
        
        row = [
            payroll.id,
            payroll.employee.user.get_full_name(),
            payroll.employee.employee_number,
            payroll.employee.department.name if payroll.employee.department else '',
            payroll.employee.position.title if payroll.employee.position else '',
            payroll.employee.user.email,
            payroll.base_salary,
            payroll.overtime_hours,
            payroll.overtime_pay,
            payroll.gross_pay,
            payroll.total_deductions,
            payroll.net_pay,
            'Pagada' if payroll.is_paid else 'Pendiente',
            payroll.payment_date.strftime('%d/%m/%Y') if payroll.payment_date else '',
            payroll.payment_method or '',
            '; '.join(rubros_adicionales)
        ]
        writer.writerow(row)
    
    logger.info(f"CSV exportado para período {period.name} por usuario {request.user.username}")
    return response


@login_required
def period_close(request, pk):
    """Cerrar período de nómina"""
    period = get_object_or_404(PayrollPeriod, pk=pk)
    
    if request.method == 'POST':
        if period.status in ['completed', 'paid']:
            with transaction.atomic():
                period.is_closed = True
                period.status = 'paid'
                period.save()
                
                messages.success(request, f'Período {period.name} cerrado correctamente.')
        else:
            messages.error(request, 'Solo se pueden cerrar períodos completados o pagados.')
    
    return redirect('payroll:period_detail', pk=pk)


@login_required 
def period_reopen(request, pk):
    """Reabrir período de nómina"""
    period = get_object_or_404(PayrollPeriod, pk=pk)
    
    if request.method == 'POST':
        if period.is_closed:
            with transaction.atomic():
                period.is_closed = False
                period.status = 'processing'
                period.save()
                
                messages.success(request, f'Período {period.name} reabierto correctamente.')
        else:
            messages.error(request, 'El período ya está abierto.')
    
    return redirect('payroll:period_detail', pk=pk)