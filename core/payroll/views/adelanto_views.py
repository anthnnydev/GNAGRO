from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from ..models import AdelantoQuincena
from ..forms.adelanto_forms import AdelantoQuincenaForm
from core.employees.models import Employee


@login_required
def adelanto_list(request):
    """Lista de adelantos de quincena"""
    adelantos = AdelantoQuincena.objects.select_related('employee', 'created_by').all()
    
    # Filtros
    employee_id = request.GET.get('employee')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if employee_id:
        adelantos = adelantos.filter(employee_id=employee_id)
    
    if status == 'pending':
        adelantos = adelantos.filter(is_descontado=False)
    elif status == 'processed':
        adelantos = adelantos.filter(is_descontado=True)
    
    if search:
        adelantos = adelantos.filter(
            Q(employee__user__first_name__icontains=search) |
            Q(employee__user__last_name__icontains=search) |
            Q(motivo__icontains=search)
        )
    
    paginator = Paginator(adelantos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas
    stats = AdelantoQuincena.objects.aggregate(
        total_pending=Count('id', filter=Q(is_descontado=False)),
        total_processed=Count('id', filter=Q(is_descontado=True)),
        total_amount=Sum('monto')
    )
    
    context = {
        'page_obj': page_obj,
        'employees': Employee.objects.filter(status='active'),
        'current_filters': {
            'employee': employee_id,
            'status': status,
            'search': search,
        },
        'stats': stats,
    }
    
    return render(request, 'pages/admin/adelantos/list.html', context)


@login_required
def adelanto_form(request, pk=None):
    """Crear o editar adelanto de quincena"""
    adelanto = get_object_or_404(AdelantoQuincena, pk=pk) if pk else None
    
    if request.method == 'POST':
        form = AdelantoQuincenaForm(request.POST, instance=adelanto)
        if form.is_valid():
            adelanto = form.save(commit=False)
            if not pk:
                adelanto.created_by = request.user
            adelanto.save()
            
            messages.success(request, 'Adelanto guardado correctamente.')
            return redirect('payroll:adelanto_list')
        else:
            messages.error(request, 'Error al guardar el adelanto.')
    else:
        form = AdelantoQuincenaForm(instance=adelanto)
    
    context = {
        'form': form,
        'adelanto': adelanto,
        'is_edit': pk is not None,
    }
    
    return render(request, 'pages/admin/adelantos/form.html', context)