# core/employees/views/employee_portal.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.views.generic import TemplateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from datetime import date, timedelta

from core.employees.models import Employee, EmployeeDocument
from core.employees.forms.EmployeePortalForms import EmployeePasswordChangeForm, EmployeeProfileForm
from django.contrib.auth.forms import PasswordChangeForm


class EmployeePasswordChangeRequiredMixin:
    """Mixin que redirige a cambio de contraseña si es necesario"""
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'employee_profile'):
            # Verificar si necesita cambiar contraseña temporal
            if hasattr(request.user, 'needs_password_change') and request.user.needs_password_change:
                # Solo permitir acceso a la vista de cambio de contraseña
                if request.resolver_match.url_name != 'employee_change_password':
                    return redirect('employees:employee_change_password')
        return super().dispatch(request, *args, **kwargs)


class EmployeeLoginRequiredMixin(LoginRequiredMixin):
    """Mixin que verifica que el usuario sea empleado"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not hasattr(request.user, 'employee_profile'):
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('core:home')
        
        return super().dispatch(request, *args, **kwargs)


@login_required
def employee_change_password_view(request):
    """Vista para cambio de contraseña temporal del empleado"""
    
    if not hasattr(request.user, 'employee_profile'):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('core:home')
    
    # Verificar si necesita cambiar contraseña
    needs_change = getattr(request.user, 'needs_password_change', False)
    
    if request.method == 'POST':
        form = EmployeePasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Marcar que ya no necesita cambiar contraseña
            user.needs_password_change = False
            user.save()
            
            # Mantener la sesión activa después del cambio
            update_session_auth_hash(request, user)
            
            messages.success(request, 'Tu contraseña ha sido cambiada exitosamente.')
            return redirect('employees:employee_dashboard')
    else:
        form = EmployeePasswordChangeForm(request.user)
    
    context = {
        'form': form,
        'needs_change': needs_change,
        'employee': request.user.employee_profile
    }
    
    return render(request, 'pages/employee/auth/change_password.html', context)


class EmployeeDashboardView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Dashboard principal del empleado"""
    template_name = 'pages/employee/dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        # Información básica del empleado
        context['employee'] = employee
        
        # Estadísticas personales
        context['years_of_service'] = employee.years_of_service
        context['days_until_birthday'] = self.get_days_until_birthday(employee)
        
        # Información del departamento
        context['department_colleagues'] = Employee.objects.filter(
            department=employee.department,
            status='active'
        ).exclude(id=employee.id).count()
        
        # Documentos del empleado
        context['document_count'] = employee.documents.count()
        context['recent_documents'] = employee.documents.order_by('-upload_date')[:3]
        
        # Información de supervisión
        if employee.subordinates.exists():
            context['subordinates_count'] = employee.subordinates.filter(status='active').count()
            context['subordinates'] = employee.subordinates.filter(status='active')[:5]
        
        # Próximos eventos (placeholder para futuras funcionalidades)
        context['upcoming_events'] = []
        
        return context
    
    def get_days_until_birthday(self, employee):
        """Calcula días hasta el próximo cumpleaños"""
        today = date.today()
        birthday_this_year = employee.birth_date.replace(year=today.year)
        
        if birthday_this_year < today:
            birthday_next_year = employee.birth_date.replace(year=today.year + 1)
            return (birthday_next_year - today).days
        else:
            return (birthday_this_year - today).days


class EmployeeProfileView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista del perfil del empleado"""
    template_name = 'pages/employee/profile/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        context['employee'] = employee
        context['user'] = self.request.user
        
        # Información adicional
        context['supervisor'] = employee.supervisor
        context['subordinates'] = employee.subordinates.filter(status='active')
        context['department_info'] = employee.department
        context['position_info'] = employee.position
        
        return context


class EmployeeDocumentsView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista de documentos del empleado"""
    template_name = 'pages/employee/documents/documents.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        # Obtener documentos del empleado
        documents = employee.documents.all().order_by('-upload_date')
        
        # Agrupar por tipo de documento
        documents_by_type = {}
        for doc in documents:
            doc_type = doc.get_document_type_display()
            if doc_type not in documents_by_type:
                documents_by_type[doc_type] = []
            documents_by_type[doc_type].append(doc)
        
        context['employee'] = employee
        context['documents'] = documents
        context['documents_by_type'] = documents_by_type
        context['document_types'] = EmployeeDocument.DOCUMENT_TYPES
        
        return context


class EmployeePayrollView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista de información de nómina del empleado"""
    template_name = 'pages/employee/payroll/payroll.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        context['employee'] = employee
        
        # Información salarial básica
        context['current_salary'] = employee.salary
        context['position_base_salary'] = employee.position.base_salary
        
        # Placeholder para registros de nómina (implementar según tu modelo de nómina)
        context['payroll_records'] = []  # Aquí irían los registros reales
        context['current_month_earnings'] = employee.salary  # Cálculo real según tu lógica
        context['ytd_earnings'] = employee.salary * 12  # Placeholder
        
        return context


class EmployeeTimeView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista de control de tiempo/asistencia del empleado"""
    template_name = 'pages/employee/time/time.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        context['employee'] = employee
        
        # Placeholder para registros de asistencia
        context['attendance_records'] = []
        context['monthly_hours'] = 0
        context['overtime_hours'] = 0
        
        return context


class EmployeeRequestsView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista de solicitudes del empleado (vacaciones, permisos, etc.)"""
    template_name = 'pages/employee/requests/requests.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        context['employee'] = employee
        
        # Placeholder para solicitudes
        context['pending_requests'] = []
        context['approved_requests'] = []
        context['vacation_balance'] = 15  # Días de vacaciones disponibles
        
        return context


class EmployeeSettingsView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, UpdateView):
    """Vista de configuración del empleado"""
    template_name = 'pages/employee/settings/settings.html'
    form_class = EmployeeProfileForm
    success_url = reverse_lazy('employees:employee_settings')
    
    def get_object(self):
        return self.request.user.employee_profile
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee'] = self.get_object()
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Tu información ha sido actualizada exitosamente.')
        return super().form_valid(form)


class EmployeeNotificationsView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista de notificaciones del empleado"""
    template_name = 'pages/employee/notifications/notifications.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        context['employee'] = employee
        
        # Placeholder para notificaciones
        context['notifications'] = [
            {
                'id': 1,
                'title': 'Bienvenido al sistema',
                'message': 'Tu cuenta ha sido creada exitosamente.',
                'type': 'info',
                'date': timezone.now(),
                'read': False
            }
        ]
        
        return context


# Vista AJAX para marcar notificaciones como leídas
class EmployeeMarkNotificationReadView(EmployeeLoginRequiredMixin, View):
    """Vista AJAX para marcar notificaciones como leídas"""
    
    def post(self, request):
        notification_id = request.POST.get('notification_id')
        # Implementar lógica para marcar notificación como leída
        return JsonResponse({'success': True})


# Vista para descargar documentos del empleado
@login_required
def employee_download_document(request, document_id):
    """Vista para descargar documentos del empleado"""
    
    if not hasattr(request.user, 'employee_profile'):
        messages.error(request, 'No tienes permisos para acceder a este documento.')
        return redirect('core:home')
    
    document = get_object_or_404(
        EmployeeDocument, 
        id=document_id, 
        employee=request.user.employee_profile
    )
    
    # Implementar lógica de descarga de archivo
    # return FileResponse(document.file, as_attachment=True)
    
    messages.info(request, f'Descargando documento: {document.name}')
    return redirect('employees:employee_documents')