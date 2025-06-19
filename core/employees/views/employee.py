# core/employees/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views import View

from core.employees.utils import send_employee_credentials_email
from core.employees.models import Employee, Department, Position, EmployeeDocument
from core.employees.forms.EmployeeForm import EmployeeForm, UserEmployeeForm, EmployeeDocumentForm

User = get_user_model()


class EmployeeListView(LoginRequiredMixin, ListView):
    """Vista para listar todos los empleados"""
    model = Employee
    template_name = 'pages/admin/employees/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Employee.objects.select_related(
            'user', 'department', 'position', 'supervisor'
        ).order_by('-created_at')
        
        # Filtros de búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(employee_number__icontains=search) |
                Q(national_id__icontains=search)
            )
        
        # Filtro por departamento
        department = self.request.GET.get('department')
        if department:
            queryset = queryset.filter(department_id=department)
        
        # Filtro por estado
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.filter(is_active=True)
        context['status_choices'] = Employee.STATUS_CHOICES
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_department'] = self.request.GET.get('department', '')
        context['selected_status'] = self.request.GET.get('status', '')
        return context


class EmployeeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para crear un nuevo empleado"""
    model = Employee
    form_class = EmployeeForm
    template_name = 'pages/admin/employees/employee_form.html'
    success_url = reverse_lazy('employees:employee_list')
    permission_required = 'employees.add_employee'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['user_form'] = UserEmployeeForm(
                self.request.POST, 
                self.request.FILES,
                is_new_employee=True
            )
        else:
            context['user_form'] = UserEmployeeForm(is_new_employee=True)
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        user_form = context['user_form']
        
        if user_form.is_valid():
            try:
                with transaction.atomic():
                    # Crear el usuario
                    user = user_form.save(commit=False)
                    user.user_type = 'employee'
                    user.is_active = True
                    
                    # NUEVO: Marcar que necesita cambiar contraseña si se generó una temporal
                    if hasattr(user, '_generated_password'):
                        user.needs_password_change = True
                    
                    user.save()
                    
                    # Crear el empleado
                    employee = form.save(commit=False)
                    employee.user = user
                    employee.save()
                    
                    # Enviar credenciales por email si el usuario tiene contraseña generada
                    if hasattr(user, '_generated_password'):
                        email_sent = send_employee_credentials_email(user, user._generated_password)
                        if email_sent:
                            messages.success(
                                self.request, 
                                f'Empleado {employee.user.get_full_name()} creado exitosamente. '
                                f'Las credenciales de acceso han sido enviadas a {user.email}.'
                            )
                        else:
                            messages.warning(
                                self.request, 
                                f'Empleado {employee.user.get_full_name()} creado exitosamente. '
                                f'Sin embargo, hubo un problema enviando las credenciales por email. '
                                f'Contraseña temporal: {user._generated_password}'
                            )
                    else:
                        messages.success(
                            self.request, 
                            f'Empleado {employee.user.get_full_name()} creado exitosamente.'
                        )
                    
                    return redirect(self.success_url)
                    
            except Exception as e:
                messages.error(self.request, f'Error al crear el empleado: {str(e)}')
                return self.form_invalid(form)
        else:
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Por favor corrige los errores en el formulario.')
        return super().form_invalid(form)

class EmployeeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para actualizar un empleado"""
    model = Employee
    form_class = EmployeeForm
    template_name = 'pages/admin/employees/employee_form.html'
    permission_required = 'employees.change_employee'
    
    def get_success_url(self):
        return reverse_lazy('employees:employee_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            # CORREGIDO: Pasar request.FILES y is_new_employee=False
            context['user_form'] = UserEmployeeForm(
                self.request.POST, 
                self.request.FILES,
                instance=self.object.user,
                is_new_employee=False
            )
        else:
            context['user_form'] = UserEmployeeForm(
                instance=self.object.user,
                is_new_employee=False
            )
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        user_form = context['user_form']
        
        if user_form.is_valid():
            try:
                with transaction.atomic():
                    user_form.save()
                    form.save()
                    messages.success(
                        self.request, 
                        f'Empleado {self.object.user.get_full_name()} actualizado exitosamente.'
                    )
            except Exception as e:
                messages.error(self.request, f'Error al actualizar el empleado: {str(e)}')
                return self.form_invalid(form)
        else:
            return self.form_invalid(form)
        
        return super().form_valid(form)


class EmployeeDetailView(LoginRequiredMixin, DetailView):
    """Vista para mostrar detalles de un empleado"""
    model = Employee
    template_name = 'pages/admin/employees/employee_detail.html'
    context_object_name = 'employee'
    
    def get_queryset(self):
        return Employee.objects.select_related(
            'user', 'department', 'position', 'supervisor'
        ).prefetch_related('documents', 'subordinates')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['documents'] = self.object.documents.all()
        context['subordinates'] = self.object.subordinates.filter(status='active')
        return context


class EmployeeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista para eliminar un empleado"""
    model = Employee
    template_name = 'pages/admin/employees/employee_confirm_delete.html'
    success_url = reverse_lazy('employees:employee_list')
    permission_required = 'employees.delete_employee'
    
    def delete(self, request, *args, **kwargs):
        employee = self.get_object()
        try:
            with transaction.atomic():
                employee.status = 'terminated'
                employee.user.is_active = False
                employee.save()
                employee.user.save()
                
                messages.success(
                    request, 
                    f'Empleado {employee.user.get_full_name()} desactivado exitosamente.'
                )
        except Exception as e:
            messages.error(request, f'Error al desactivar el empleado: {str(e)}')
        
        return redirect(self.success_url)


class EmployeeDocumentCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para subir documentos de empleado"""
    model = EmployeeDocument
    form_class = EmployeeDocumentForm
    template_name = 'employees/employee_document_create.html'
    permission_required = 'employees.add_employeedocument'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee'] = get_object_or_404(Employee, pk=self.kwargs['employee_pk'])
        return context
    
    def form_valid(self, form):
        employee = get_object_or_404(Employee, pk=self.kwargs['employee_pk'])
        form.instance.employee = employee
        messages.success(self.request, 'Documento subido exitosamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('employees:employee_detail', kwargs={'pk': self.kwargs['employee_pk']})


class EmployeeAjaxSearchView(LoginRequiredMixin, View):
    """Vista AJAX para búsqueda de empleados"""
    
    def get(self, request):
        query = request.GET.get('q', '')
        employees = []
        
        if len(query) >= 2:
            employee_list = Employee.objects.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(employee_number__icontains=query),
                status='active'
            ).select_related('user', 'position')[:10]
            
            employees = [{
                'id': emp.id,
                'text': f"{emp.user.get_full_name()} ({emp.employee_number})",
                'position': emp.position.title,
                'department': emp.department.name
            } for emp in employee_list]
        
        return JsonResponse({'results': employees})


class EmployeeStatsView(LoginRequiredMixin, View):
    """Vista para estadísticas de empleados (para dashboard)"""
    
    def get(self, request):
        from django.db.models import Count, Q
        from datetime import date, timedelta
        
        # Estadísticas básicas
        total_employees = Employee.objects.count()
        active_employees = Employee.objects.filter(status='active').count()
        
        # Empleados por departamento
        dept_stats = Department.objects.annotate(
            employee_count=Count('employees', filter=Q(employees__status='active'))
        ).values('name', 'employee_count')
        
        # Empleados contratados en los últimos 30 días
        thirty_days_ago = date.today() - timedelta(days=30)
        recent_hires = Employee.objects.filter(
            hire_date__gte=thirty_days_ago
        ).count()
        
        # Empleados próximos a cumplir años (próximos 30 días)
        today = date.today()
        next_month = today + timedelta(days=30)
        
        upcoming_birthdays = Employee.objects.filter(
            birth_date__month__gte=today.month,
            birth_date__day__gte=today.day,
            birth_date__month__lte=next_month.month,
            birth_date__day__lte=next_month.day,
            status='active'
        ).count()
        
        data = {
            'total_employees': total_employees,
            'active_employees': active_employees,
            'inactive_employees': total_employees - active_employees,
            'recent_hires': recent_hires,
            'upcoming_birthdays': upcoming_birthdays,
            'department_stats': list(dept_stats),
            'active_percentage': round((active_employees / total_employees * 100) if total_employees > 0 else 0, 1)
        }
        
        return JsonResponse(data)


# Vista para el dashboard principal
class DashboardView(LoginRequiredMixin, View):
    """Vista principal del dashboard"""
    template_name = 'dashboard/dashboard.html'
    
    def get(self, request):
        from datetime import date, timedelta
        
        # Estadísticas para el dashboard
        total_employees = Employee.objects.count()
        active_employees = Employee.objects.filter(status='active').count()
        active_percentage = round((active_employees / total_employees * 100) if total_employees > 0 else 0, 1)
        
        # Empleados recientes (últimos 10)
        recent_employees = Employee.objects.select_related(
            'user', 'department', 'position'
        ).order_by('-created_at')[:10]
        
        # Nómina del mes (placeholder - implementar según tu lógica)
        monthly_payroll = 0  # Implementar cálculo real
        
        # Solicitudes pendientes (placeholder)
        pending_requests = 0  # Implementar según tu lógica
        
        context = {
            'total_employees': total_employees,
            'active_employees': active_employees,
            'active_percentage': active_percentage,
            'monthly_payroll': monthly_payroll,
            'pending_requests': pending_requests,
            'recent_employees': recent_employees,
        }
        
        return render(request, self.template_name, context)