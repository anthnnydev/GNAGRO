# core/employees/views/position.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.http import JsonResponse

from ..models import Position, Department
from core.employees.forms.Position import PositionForm, PositionFilterForm


class PositionListView(LoginRequiredMixin, ListView):
    """
    Vista para listar cargos/posiciones con filtros y paginación
    """
    model = Position
    template_name = 'components/parameters/position/list.html'
    context_object_name = 'positions'
    paginate_by = 10

    def get_queryset(self):
        queryset = Position.objects.select_related('department').annotate(
            employees_count=Count('employees', distinct=True)
        )
        
        # Aplicar filtros
        search = self.request.GET.get('search')
        department_id = self.request.GET.get('department')
        status = self.request.GET.get('status')
        salary_min = self.request.GET.get('salary_min')
        salary_max = self.request.GET.get('salary_max')
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(department__name__icontains=search)
            )
        
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        if salary_min:
            queryset = queryset.filter(base_salary__gte=salary_min)
        
        if salary_max:
            queryset = queryset.filter(base_salary__lte=salary_max)
        
        return queryset.order_by('department__name', 'title')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = PositionFilterForm(self.request.GET)
        context['total_positions'] = Position.objects.count()
        context['active_positions'] = Position.objects.filter(is_active=True).count()
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        return context


class PositionCreateView(LoginRequiredMixin, CreateView):
    """
    Vista para crear nuevos cargos/posiciones
    """
    model = Position
    form_class = PositionForm
    template_name = 'components/parameters/position/form.html'
    success_url = reverse_lazy('employees:position_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cargo creado exitosamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor, corrige los errores en el formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Cargo'
        context['button_text'] = 'Crear Cargo'
        return context


class PositionUpdateView(LoginRequiredMixin, UpdateView):
    """
    Vista para actualizar cargos/posiciones existentes
    """
    model = Position
    form_class = PositionForm
    template_name = 'components/parameters/position/form.html'
    success_url = reverse_lazy('employees:position_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cargo actualizado exitosamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor, corrige los errores en el formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Cargo'
        context['button_text'] = 'Actualizar Cargo'
        return context


class PositionDeleteView(LoginRequiredMixin, DeleteView):
    """
    Vista para eliminar cargos/posiciones
    """
    model = Position
    template_name = 'components/parameters/position/delete.html'
    success_url = reverse_lazy('employees:position_list')

    def delete(self, request, *args, **kwargs):
        position = self.get_object()
        
        # Verificar si el cargo tiene empleados asociados
        if position.employees.exists():
            messages.error(request, 'No se puede eliminar el cargo porque tiene empleados asociados.')
            return redirect('employees:position_list')
        
        messages.success(request, f'Cargo "{position.title}" eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        position = self.get_object()
        context['employees_count'] = position.employees.count()
        return context


# Vistas AJAX para carga dinámica
@login_required
def get_positions_by_department(request):
    """
    Vista AJAX para obtener cargos por departamento
    """
    department_id = request.GET.get('department_id')
    if department_id:
        positions = Position.objects.filter(
            department_id=department_id,
            is_active=True
        ).values('id', 'title', 'base_salary')
        return JsonResponse({'positions': list(positions)})
    return JsonResponse({'positions': []})


@login_required
def department_stats(request):
    """
    Vista AJAX para obtener estadísticas de departamentos
    """
    stats = {
        'total_departments': Department.objects.count(),
        'active_departments': Department.objects.filter(is_active=True).count(),
        'departments_with_manager': Department.objects.filter(manager__isnull=False).count(),
        'total_positions': Position.objects.count(),
        'active_positions': Position.objects.filter(is_active=True).count(),
    }
    return JsonResponse(stats)