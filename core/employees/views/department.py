
# core/employees/views/department.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.http import JsonResponse
from django.core.paginator import Paginator

from ..models import Department
from core.employees.forms.Position import DepartmentForm, DepartmentFilterForm


class DepartmentListView(LoginRequiredMixin, ListView):
    """
    Vista para listar departamentos con filtros y paginación
    """
    model = Department
    template_name = 'components/parameters/department/list.html'
    context_object_name = 'departments'
    paginate_by = 10

    def get_queryset(self):
        queryset = Department.objects.select_related('manager').annotate(
            employees_count=Count('employees', distinct=True),
            positions_count=Count('positions', distinct=True)
        )
        
        # Aplicar filtros
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(manager__first_name__icontains=search) |
                Q(manager__last_name__icontains=search)
            )
        
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = DepartmentFilterForm(self.request.GET)
        context['total_departments'] = Department.objects.count()
        context['active_departments'] = Department.objects.filter(is_active=True).count()
        return context


class DepartmentCreateView(LoginRequiredMixin, CreateView):
    """
    Vista para crear nuevos departamentos
    """
    model = Department
    form_class = DepartmentForm
    template_name = 'components/parameters/department/form.html'
    success_url = reverse_lazy('employees:department_list')

    def form_valid(self, form):
        messages.success(self.request, 'Departamento creado exitosamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor, corrige los errores en el formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Departamento'
        context['button_text'] = 'Crear Departamento'
        return context


class DepartmentUpdateView(LoginRequiredMixin, UpdateView):
    """
    Vista para actualizar departamentos existentes
    """
    model = Department
    form_class = DepartmentForm
    template_name = 'components/parameters/department/form.html'
    success_url = reverse_lazy('employees:department_list')

    def form_valid(self, form):
        messages.success(self.request, 'Departamento actualizado exitosamente.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Por favor, corrige los errores en el formulario.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Departamento'
        context['button_text'] = 'Actualizar Departamento'
        return context


class DepartmentDeleteView(LoginRequiredMixin, DeleteView):
    """
    Vista para eliminar departamentos
    """
    model = Department
    template_name = 'components/parameters/department/delete.html'
    success_url = reverse_lazy('employees:department_list')

    def delete(self, request, *args, **kwargs):
        department = self.get_object()
        
        # Verificar si el departamento tiene empleados o cargos asociados
        if department.employees.exists():
            messages.error(request, 'No se puede eliminar el departamento porque tiene empleados asociados.')
            return redirect('employees:department_list')
        
        if department.positions.exists():
            messages.error(request, 'No se puede eliminar el departamento porque tiene cargos asociados.')
            return redirect('employees:department_list')
        
        messages.success(request, f'Departamento "{department.name}" eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        department = self.get_object()
        context['employees_count'] = department.employees.count()
        context['positions_count'] = department.positions.count()
        return context