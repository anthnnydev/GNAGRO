# core/payroll/views/rubro_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from ..models import Rubro, TipoRubro
from ..forms.rubro_forms import RubroForm, TipoRubroForm


@login_required
def rubro_list(request):
    """Lista de rubros"""
    rubros = Rubro.objects.select_related('tipo_rubro').all()
    
    # Filtros
    tipo_id = request.GET.get('tipo')
    search = request.GET.get('search')
    status = request.GET.get('status')
    
    if tipo_id:
        rubros = rubros.filter(tipo_rubro_id=tipo_id)
    
    if search:
        rubros = rubros.filter(
            Q(nombre__icontains=search) |
            Q(codigo__icontains=search)
        )
    
    if status == 'active':
        rubros = rubros.filter(is_active=True)
    elif status == 'inactive':
        rubros = rubros.filter(is_active=False)
    
    paginator = Paginator(rubros, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calcular estadísticas
    total_ingresos = rubros.filter(tipo_rubro__tipo='ingreso').count()
    total_egresos = rubros.filter(tipo_rubro__tipo='egreso').count()
    total_automaticos = rubros.filter(aplicar_automaticamente=True).count()
    
    context = {
        'page_obj': page_obj,
        'tipos_rubro': TipoRubro.objects.filter(is_active=True),
        'current_filters': {
            'tipo': tipo_id,
            'search': search,
            'status': status,
        },
        'estadisticas': {
            'total_ingresos': total_ingresos,
            'total_egresos': total_egresos, 
            'total_automaticos': total_automaticos,
        }
    }
    
    return render(request, 'pages/admin/rubros/list.html', context)


@login_required
def rubro_form(request, pk=None):
    """Crear o editar rubro"""
    rubro = get_object_or_404(Rubro, pk=pk) if pk else None
    
    # Obtener tipos de rubro disponibles ANTES de procesar el formulario
    tipos_rubro = TipoRubro.objects.filter(is_active=True).order_by('tipo', 'nombre')
    
    # Si no hay tipos de rubro, crear algunos por defecto
    if not tipos_rubro.exists():
        # Crear tipos básicos automáticamente
        tipo_egreso = TipoRubro.objects.create(
            nombre='Deducciones Legales',
            tipo='egreso',
            descripcion='Deducciones obligatorias como IESS, impuestos, etc.',
            is_active=True
        )
        
        tipo_ingreso = TipoRubro.objects.create(
            nombre='Beneficios Adicionales', 
            tipo='ingreso',
            descripcion='Ingresos adicionales como bonos, comisiones, etc.',
            is_active=True
        )
        
        messages.info(request, 'Se crearon tipos de rubro básicos automáticamente.')
        tipos_rubro = TipoRubro.objects.filter(is_active=True).order_by('tipo', 'nombre')
    
    if request.method == 'POST':
        form = RubroForm(request.POST, instance=rubro)
        if form.is_valid():
            nuevo_rubro = form.save()
            messages.success(request, f'Rubro "{nuevo_rubro.nombre}" guardado correctamente.')
            return redirect('payroll:rubro_list')
        else:
            messages.error(request, 'Error al guardar el rubro. Revise los campos marcados.')
    else:
        form = RubroForm(instance=rubro)
    
    # Preparar datos para el template
    tipos_choices = []
    for tipo in tipos_rubro:
        tipos_choices.append({
            'id': tipo.pk,
            'nombre': tipo.nombre,
            'tipo': tipo.tipo,
            'tipo_display': tipo.get_tipo_display(),
            'descripcion': tipo.descripcion
        })
    
    context = {
        'form': form,
        'rubro': rubro,
        'is_edit': pk is not None,
        'tipos_rubro': tipos_rubro,
        'tipos_choices': tipos_choices,  # Para usar en JavaScript si es necesario
        'tipos_count': tipos_rubro.count(),
    }
    
    return render(request, 'pages/admin/rubros/form.html', context)


@login_required
def tipo_rubro_list(request):
    """Lista de tipos de rubro"""
    tipos = TipoRubro.objects.all().order_by('tipo', 'nombre')
    
    # Agregar estadísticas a cada tipo
    for tipo in tipos:
        tipo.total_rubros = tipo.rubros.count()
        tipo.rubros_activos = tipo.rubros.filter(is_active=True).count()
        tipo.rubros_automaticos = tipo.rubros.filter(aplicar_automaticamente=True).count()
    
    # Estadísticas generales
    total_tipos = tipos.count()
    tipos_ingreso = tipos.filter(tipo='ingreso').count()
    tipos_egreso = tipos.filter(tipo='egreso').count()
    
    context = {
        'tipos': tipos,
        'estadisticas': {
            'total_tipos': total_tipos,
            'tipos_ingreso': tipos_ingreso,
            'tipos_egreso': tipos_egreso,
        }
    }
    
    return render(request, 'pages/admin/rubros/tipos/list.html', context)


@login_required
def tipo_rubro_form(request, pk=None):
    """Crear o editar tipo de rubro"""
    tipo = get_object_or_404(TipoRubro, pk=pk) if pk else None
    
    if request.method == 'POST':
        form = TipoRubroForm(request.POST, instance=tipo)
        if form.is_valid():
            nuevo_tipo = form.save()
            messages.success(request, f'Tipo de rubro "{nuevo_tipo.nombre}" guardado correctamente.')
            return redirect('payroll:tipo_rubro_list')
        else:
            messages.error(request, 'Error al guardar el tipo de rubro.')
    else:
        form = TipoRubroForm(instance=tipo)
    
    # Calcular estadísticas si estamos editando
    if tipo:
        tipo.rubros_activos = tipo.rubros.filter(is_active=True).count()
        tipo.rubros_automaticos = tipo.rubros.filter(aplicar_automaticamente=True).count()
    
    context = {
        'form': form,
        'tipo': tipo,
        'is_edit': pk is not None,
    }
    
    return render(request, 'pages/admin/rubros/tipos/form.html', context)


@login_required
def rubro_toggle_status(request, pk):
    """Toggle del estado activo/inactivo de un rubro"""
    if request.method == 'POST':
        try:
            rubro = get_object_or_404(Rubro, pk=pk)
            rubro.is_active = not rubro.is_active
            rubro.save()
            
            status = 'activado' if rubro.is_active else 'desactivado'
            messages.success(request, f'Rubro "{rubro.nombre}" {status} correctamente.')
            
            return JsonResponse({
                'success': True,
                'message': f'Rubro {status}',
                'new_status': rubro.is_active
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


# Función auxiliar para crear tipos de rubro por defecto
def crear_tipos_rubro_por_defecto():
    """Crea tipos de rubro básicos si no existen"""
    tipos_default = [
        {
            'nombre': 'Deducciones Legales',
            'tipo': 'egreso',
            'descripcion': 'Deducciones obligatorias por ley (IESS, impuestos, etc.)'
        },
        {
            'nombre': 'Beneficios Adicionales',
            'tipo': 'ingreso', 
            'descripcion': 'Ingresos adicionales al salario base (bonos, comisiones, etc.)'
        },
        {
            'nombre': 'Deducciones Voluntarias',
            'tipo': 'egreso',
            'descripcion': 'Deducciones opcionales (préstamos, seguros privados, etc.)'
        },
        {
            'nombre': 'Horas Adicionales',
            'tipo': 'ingreso',
            'descripcion': 'Pagos por horas extra, suplementarias y extraordinarias'
        }
    ]
    
    created_count = 0
    for tipo_data in tipos_default:
        tipo, created = TipoRubro.objects.get_or_create(
            nombre=tipo_data['nombre'],
            defaults={
                'tipo': tipo_data['tipo'],
                'descripcion': tipo_data['descripcion'],
                'is_active': True
            }
        )
        if created:
            created_count += 1
    
    return created_count