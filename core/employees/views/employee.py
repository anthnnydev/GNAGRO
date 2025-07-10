# core/employees/views.py (SECCIÓN CORREGIDA)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.urls import reverse_lazy
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponseRedirect
from django.views import View

from core.employees.utils import send_employee_credentials_email
from core.employees.models import Employee, Department, Position, EmployeeDocument
from core.employees.forms.EmployeeForm import EmployeeForm, UserEmployeeForm, EmployeeDocumentForm

User = get_user_model()

class EmployeeLoginRequiredMixin(LoginRequiredMixin):
    """Mixin que verifica que el usuario tenga employee_profile"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # CORREGIDO: Verificar employee_profile en lugar de admin_profile
        if not hasattr(request.user, 'employee_profile'):
            messages.error(request, 'No tienes un perfil de empleado asociado.')
            if request.user.is_staff:
                return redirect('users:dashboard')
            else:
                return redirect('users:login')
        
        return super().dispatch(request, *args, **kwargs)
    
class EmployeePasswordChangeRequiredMixin:
    """Mixin que redirige a cambio de contraseña si es necesario"""
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'admin_profile'):
            # Verificar si necesita cambiar contraseña temporal
            if hasattr(request.user, 'needs_password_change') and request.user.needs_password_change:
                # Solo permitir acceso a la vista de cambio de contraseña
                if request.resolver_match.url_name != 'employee_change_password':
                    return redirect('employees:employee_change_password')
        return super().dispatch(request, *args, **kwargs)


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
        
        # CORREGIDO: Lógica de filtrado por estado
        status = self.request.GET.get('status')
        show_all = self.request.GET.get('show_all')
        
        # Prioridad: show_all > status específico > default (solo activos)
        if show_all == '1':
            # Mostrar todos los empleados, sin filtrar por estado
            pass
        elif status and status != 'all':
            # Filtrar por un estado específico
            queryset = queryset.filter(status=status)
        elif status == 'all':
            # Mostrar todos (equivalente a show_all=1)
            pass
        else:
            # Por defecto, mostrar solo activos
            queryset = queryset.filter(status='active')
        
        # Filtro por tipo de usuario
        user_type = self.request.GET.get('user_type')
        if user_type:
            queryset = queryset.filter(user__user_type=user_type)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Datos básicos
        context['departments'] = Department.objects.filter(is_active=True)
        context['status_choices'] = Employee.STATUS_CHOICES
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_department'] = self.request.GET.get('department', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_user_type'] = self.request.GET.get('user_type', '')
        context['show_all'] = self.request.GET.get('show_all', '')
        
        # Estadísticas para el dashboard (sin filtros aplicados)
        all_employees = Employee.objects.select_related('user')
        
        context['total_employees'] = all_employees.count()
        context['active_employees'] = all_employees.filter(status='active').count()
        context['inactive_employees'] = all_employees.exclude(status='active').count()
        context['supervisor_count'] = all_employees.filter(user__user_type='supervisor').count()
        context['admin_count'] = all_employees.filter(
            user__user_type__in=['admin', 'hr']
        ).count()
        
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
                    user.is_active = True
                    
                    # Marcar que necesita cambiar contraseña si se generó una temporal
                    if hasattr(user, '_generated_password'):
                        user.needs_password_change = True
                    
                    user.save()
                    
                    # Crear el empleado
                    employee = form.save(commit=False)
                    employee.user = user
                    employee.save()
                    
                    # Mensaje personalizado según el tipo de usuario
                    user_type_messages = {
                        'employee': 'empleado',
                        'supervisor': 'supervisor',
                        'hr': 'personal de Recursos Humanos',
                        'admin': 'administrador'
                    }
                    
                    user_type_msg = user_type_messages.get(user.user_type, 'empleado')
                    
                    # Enviar credenciales por email si el usuario tiene contraseña generada
                    if hasattr(user, '_generated_password'):
                        email_sent = send_employee_credentials_email(user, user._generated_password)
                        if email_sent:
                            messages.success(
                                self.request, 
                                f'{user_type_msg.capitalize()} {employee.user.get_full_name()} creado exitosamente. '
                                f'Las credenciales de acceso han sido enviadas a {user.email}.'
                            )
                        else:
                            messages.warning(
                                self.request, 
                                f'{user_type_msg.capitalize()} {employee.user.get_full_name()} creado exitosamente. '
                                f'Sin embargo, hubo un problema enviando las credenciales por email. '
                                f'Contraseña temporal: {user._generated_password}'
                            )
                    else:
                        messages.success(
                            self.request, 
                            f'{user_type_msg.capitalize()} {employee.user.get_full_name()} creado exitosamente.'
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
    
class AdminProfileView(LoginRequiredMixin, TemplateView):
    """Vista del perfil del empleado - funciona para todos los tipos de usuario"""
    template_name = 'pages/admin/profile/profile.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Verificar que tiene employee_profile
        if not hasattr(request.user, 'employee_profile'):
            messages.error(request, 'No tienes un perfil de empleado asociado.')
            if request.user.is_staff:
                return redirect('users:dashboard')
            else:
                return redirect('users:login')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        context['employee'] = employee
        context['user'] = self.request.user
        
        # Información adicional
        context['supervisor'] = employee.supervisor
        context['subordinates'] = employee.subordinates.filter(status='active') if hasattr(employee, 'subordinates') else None
        context['department_info'] = employee.department
        context['position_info'] = employee.position
        
        # Información específica para admins
        if self.request.user.is_staff:
            context['is_admin'] = True
            context['admin_permissions'] = self.request.user.get_all_permissions()
        
        return context


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
                    # Guardar el usuario (incluyendo cambios en user_type)
                    old_user_type = self.object.user.user_type
                    user = user_form.save()
                    new_user_type = user.user_type
                    
                    # Guardar el empleado
                    form.save()
                    
                    # Mensaje especial si cambió el tipo de usuario
                    if old_user_type != new_user_type:
                        user_type_messages = {
                            'employee': 'empleado',
                            'supervisor': 'supervisor',
                            'hr': 'personal de Recursos Humanos',
                            'admin': 'administrador'
                        }
                        
                        old_type_msg = user_type_messages.get(old_user_type, 'empleado')
                        new_type_msg = user_type_messages.get(new_user_type, 'empleado')
                        
                        messages.success(
                            self.request, 
                            f'{self.object.user.get_full_name()} actualizado exitosamente. '
                            f'Tipo de usuario cambiado de {old_type_msg} a {new_type_msg}.'
                        )
                    else:
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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_reactivate'] = self.object.status == 'terminated'
        return context
    
    def post(self, request, *args, **kwargs):
        """Maneja la desactivación del empleado cuando se envía el formulario"""
        employee = self.get_object()
        
        try:
            with transaction.atomic():
                # Obtener datos del formulario
                termination_reason = request.POST.get('termination_reason', '').strip()
                termination_type = request.POST.get('termination_type', '')
                confirm_deactivation = request.POST.get('confirm_deactivation', '')
                
                # Verificar que se confirmó la desactivación
                if not confirm_deactivation:
                    messages.error(request, 'Debe confirmar la desactivación marcando la casilla.')
                    return self.get(request, *args, **kwargs)
                
                # Cambiar el estado del empleado
                employee.status = 'terminated'
                employee.user.is_active = False
                
                # Guardar cambios
                employee.save()
                employee.user.save()
                
                # Mensaje personalizado según el tipo de usuario
                user_type_messages = {
                    'employee': 'Empleado',
                    'supervisor': 'Supervisor',
                    'hr': 'Personal de RH',
                    'admin': 'Administrador'
                }
                
                user_type_msg = user_type_messages.get(employee.user.user_type, 'Empleado')
                
                messages.success(
                    request, 
                    f'{user_type_msg} {employee.user.get_full_name()} desactivado exitosamente.'
                )
                
                # Guardar información adicional si se proporcionó motivo
                # Si tienes un campo para motivo en el modelo, descomenta estas líneas:
                # if termination_reason:
                #     employee.termination_reason = termination_reason
                #     employee.termination_type = termination_type
                #     employee.save()
                
        except Exception as e:
            messages.error(request, f'Error al desactivar el empleado: {str(e)}')
            return self.get(request, *args, **kwargs)
        
        return HttpResponseRedirect(self.success_url)
    
    def delete(self, request, *args, **kwargs):
        """Método delete que redirige a post para consistencia"""
        return self.post(request, *args, **kwargs)


# NUEVA: Vista para reactivar empleados
class EmployeeReactivateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Vista para reactivar un empleado desactivado"""
    permission_required = 'employees.change_employee'
    
    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)
        
        try:
            with transaction.atomic():
                employee.status = 'active'
                employee.user.is_active = True
                employee.save()
                employee.user.save()
                
                messages.success(
                    request, 
                    f'Empleado {employee.user.get_full_name()} reactivado exitosamente.'
                )
        except Exception as e:
            messages.error(request, f'Error al reactivar el empleado: {str(e)}')
        
        return redirect('employees:employee_detail', pk=pk)


# APIs mejoradas con información de tipos de usuario
class EmployeeStatsView(LoginRequiredMixin, View):
    """Vista para estadísticas de empleados (para dashboard)"""
    
    def get(self, request):
        from django.db.models import Count, Q
        from datetime import date, timedelta
        
        # Estadísticas básicas
        total_employees = Employee.objects.count()
        active_employees = Employee.objects.filter(status='active').count()
        inactive_employees = total_employees - active_employees
        
        # Estadísticas por tipo de usuario
        user_type_stats = Employee.objects.values('user__user_type').annotate(
            count=Count('id')
        ).order_by('user__user_type')
        
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
        
        # Distribución por tipo de usuario con nombres legibles
        user_type_names = {
            'employee': 'Empleados',
            'supervisor': 'Supervisores', 
            'hr': 'Recursos Humanos',
            'admin': 'Administradores'
        }
        
        formatted_user_types = []
        for stat in user_type_stats:
            user_type = stat['user__user_type']
            formatted_user_types.append({
                'type': user_type,
                'name': user_type_names.get(user_type, user_type.capitalize()),
                'count': stat['count']
            })
        
        data = {
            'total_employees': total_employees,
            'active_employees': active_employees,
            'inactive_employees': inactive_employees,
            'recent_hires': recent_hires,
            'upcoming_birthdays': upcoming_birthdays,
            'department_stats': list(dept_stats),
            'user_type_stats': formatted_user_types,
            'active_percentage': round((active_employees / total_employees * 100) if total_employees > 0 else 0, 1),
            'supervisor_count': Employee.objects.filter(user__user_type='supervisor').count(),
            'admin_count': Employee.objects.filter(user__user_type__in=['admin', 'hr']).count()
        }
        
        return JsonResponse(data)


class EmployeeAjaxSearchView(LoginRequiredMixin, View):
    """Vista AJAX para búsqueda de empleados con tipo de usuario"""
    
    def get(self, request):
        query = request.GET.get('q', '')
        user_type_filter = request.GET.get('user_type', '')
        include_inactive = request.GET.get('include_inactive', False)  # NUEVO
        employees = []
        
        if len(query) >= 2:
            employee_list = Employee.objects.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(employee_number__icontains=query)
            ).select_related('user', 'position')
            
            # Filtrar por estado
            if not include_inactive:
                employee_list = employee_list.filter(status='active')
            
            # Filtrar por tipo de usuario si se especifica
            if user_type_filter:
                employee_list = employee_list.filter(user__user_type=user_type_filter)
            
            employee_list = employee_list[:10]
            
            # Iconos para tipos de usuario
            user_type_icons = {
                'employee': 'fas fa-user',
                'supervisor': 'fas fa-user-tie',
                'hr': 'fas fa-users-cog',
                'admin': 'fas fa-crown'
            }
            
            employees = [{
                'id': emp.id,
                'text': f"{emp.user.get_full_name()} ({emp.employee_number})",
                'position': emp.position.title,
                'department': emp.department.name,
                'user_type': emp.user.user_type,
                'user_type_display': emp.user.get_user_type_display(),
                'user_type_icon': user_type_icons.get(emp.user.user_type, 'fas fa-user'),
                'status': emp.status,  # NUEVO
                'is_active': emp.status == 'active'  # NUEVO
            } for emp in employee_list]
        
        return JsonResponse({'results': employees})


# Vista para el dashboard principal (actualizada)
class DashboardView(LoginRequiredMixin, View):
    """Vista principal del dashboard"""
    template_name = 'dashboard/dashboard.html'
    
    def get(self, request):
        from datetime import date, timedelta
        
        # Estadísticas para el dashboard
        total_employees = Employee.objects.count()
        active_employees = Employee.objects.filter(status='active').count()
        inactive_employees = total_employees - active_employees
        active_percentage = round((active_employees / total_employees * 100) if total_employees > 0 else 0, 1)
        
        # Estadísticas por tipo de usuario
        supervisor_count = Employee.objects.filter(user__user_type='supervisor').count()
        admin_count = Employee.objects.filter(user__user_type__in=['admin', 'hr']).count()
        employee_count = Employee.objects.filter(user__user_type='employee').count()
        
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
            'inactive_employees': inactive_employees,  # NUEVO
            'active_percentage': active_percentage,
            'supervisor_count': supervisor_count,
            'admin_count': admin_count,
            'employee_count': employee_count,
            'monthly_payroll': monthly_payroll,
            'pending_requests': pending_requests,
            'recent_employees': recent_employees,
        }
        
        return render(request, self.template_name, context)
    
    
class EmployeeDocumentCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para subir documentos de empleado"""
    model = EmployeeDocument
    form_class = EmployeeDocumentForm
    template_name = 'pages/admin/employees/employee_document_create.html'
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