# core/employees/views/employee_portal.py (ACTUALIZADO)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.views.generic import TemplateView, UpdateView, CreateView, DetailView
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum, Count  # Agregar Sum y Count
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from datetime import date, timedelta

from core.employees.models import Employee, EmployeeDocument
from core.employees.forms.EmployeePortalForms import EmployeePasswordChangeForm, EmployeeProfileForm
from django.contrib.auth.forms import PasswordChangeForm

# IMPORTACIONES PARA TAREAS
try:
    from core.tasks.models import TaskAssignment, TaskProgress, TaskComment, Task
    TASKS_APP_AVAILABLE = True
except ImportError:
    TASKS_APP_AVAILABLE = False

# IMPORTACIONES PARA ASISTENCIA - AGREGAR ESTO
try:
    from core.attendance.models import Attendance, EmployeeSchedule, WorkSchedule
    ATTENDANCE_APP_AVAILABLE = True
except ImportError:
    ATTENDANCE_APP_AVAILABLE = False
    
# IMPORTACIONES PARA LICENCIAS - AGREGAR ESTO AL INICIO DEL ARCHIVO
try:
    from core.leaves.models import LeaveRequest, LeaveBalance, LeaveType
    from core.leaves.forms.LeavesForm import LeaveRequestForm
    LEAVES_APP_AVAILABLE = True
except ImportError:
    LEAVES_APP_AVAILABLE = False 


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
    """Dashboard principal del empleado UNIFICADO (Personal + Tareas)"""
    template_name = 'pages/employee/dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        # ==================== INFORMACIÓN PERSONAL ====================
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
        
        # ==================== INFORMACIÓN DE TAREAS ====================
        if TASKS_APP_AVAILABLE:
            # Estadísticas de tareas del empleado
            assignments_stats = TaskAssignment.objects.filter(employee=employee).aggregate(
                total=Count('id'),
                pending=Count('id', filter=Q(status='pending')),
                accepted=Count('id', filter=Q(status='accepted')),
                in_progress=Count('id', filter=Q(status='in_progress')),
                completed=Count('id', filter=Q(status='completed')),
                rejected=Count('id', filter=Q(status='rejected')),
                total_hours=Sum('hours_worked') or 0,
                total_units=Sum('units_completed') or 0
            )
            context['assignments_stats'] = assignments_stats
            
            # Tareas urgentes asignadas
            urgent_assignments = TaskAssignment.objects.filter(
                employee=employee,
                status__in=['pending', 'accepted', 'in_progress'],
                task__priority='urgent'
            ).select_related('task', 'task__category').order_by('task__end_date')[:3]
            context['urgent_assignments'] = urgent_assignments
            
            # Actividad reciente del empleado
            recent_progress = TaskProgress.objects.filter(
                assignment__employee=employee
            ).select_related('assignment__task').order_by('-timestamp')[:5]
            context['recent_progress'] = recent_progress
            
            # Tareas próximas a vencer (próximas 24 horas)
            upcoming_deadline = TaskAssignment.objects.filter(
                employee=employee,
                status__in=['pending', 'accepted', 'in_progress'],
                task__end_date__range=[
                    timezone.now(),
                    timezone.now() + timedelta(hours=24)
                ]
            ).select_related('task').order_by('task__end_date')[:5]
            context['upcoming_deadline'] = upcoming_deadline
            
            # Tareas recientes (últimas 5 asignaciones)
            recent_assignments = TaskAssignment.objects.filter(
                employee=employee
            ).select_related('task', 'task__category').order_by('-assigned_at')[:5]
            context['recent_assignments'] = recent_assignments
            
            # Earnings del mes (calculado basado en tareas completadas)
            current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_earnings = 0
            completed_assignments_this_month = TaskAssignment.objects.filter(
                employee=employee,
                status='completed',
                completed_at__gte=current_month_start
            )
            
            for assignment in completed_assignments_this_month:
                monthly_earnings += assignment.calculated_payment
            
            context['monthly_earnings'] = monthly_earnings
            
            # Indicador de si tiene tareas (para mostrar/ocultar secciones)
            context['has_tasks'] = assignments_stats['total'] > 0
            
            # Progreso estadísticas para gráficos
            if assignments_stats['total'] > 0:
                context['completion_rate'] = int((assignments_stats['completed'] / assignments_stats['total']) * 100)
            else:
                context['completion_rate'] = 100
        else:
            # Si no hay app de tareas, establecer valores por defecto
            context['assignments_stats'] = {
                'total': 0, 'pending': 0, 'accepted': 0, 'in_progress': 0, 
                'completed': 0, 'rejected': 0, 'total_hours': 0, 'total_units': 0
            }
            context['urgent_assignments'] = []
            context['recent_progress'] = []
            context['upcoming_deadline'] = []
            context['recent_assignments'] = []
            context['monthly_earnings'] = 0
            context['has_tasks'] = False
            context['completion_rate'] = 100
        
        # Próximos eventos (placeholder para futuras funcionalidades)
        context['upcoming_events'] = []
        
        return context
    
    def get_days_until_birthday(self, employee):
        """Calcula días hasta el próximo cumpleaños"""
        if not employee.birth_date:
            return None
            
        today = date.today()
        birthday_this_year = employee.birth_date.replace(year=today.year)
        
        if birthday_this_year < today:
            birthday_next_year = employee.birth_date.replace(year=today.year + 1)
            return (birthday_next_year - today).days
        else:
            return (birthday_this_year - today).days


# ==================== RESTO DE VISTAS SIN CAMBIOS ====================

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
    """Vista de control de tiempo/asistencia del empleado ACTUALIZADA"""
    template_name = 'pages/employee/time/time.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        context['employee'] = employee
        
        # Obtener el horario actual del empleado
        today = timezone.now().date()
        current_schedule = None
        
        try:
            from core.attendance.models import EmployeeSchedule
            employee_schedule = EmployeeSchedule.objects.filter(
                employee=employee,
                is_active=True,
                start_date__lte=today,
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=today)
            ).select_related('schedule').first()
            
            if employee_schedule:
                current_schedule = employee_schedule.schedule
        except ImportError:
            pass
        
        context['current_schedule'] = current_schedule
        
        # Obtener registros del mes actual
        month_start = today.replace(day=1)
        
        try:
            from core.attendance.models import Attendance
            attendance_records = Attendance.objects.filter(
                employee=employee,
                date__gte=month_start,
                date__lte=today
            ).order_by('-date')
            
            context['attendance_records'] = attendance_records
            
            # Estadísticas del mes
            monthly_stats = attendance_records.aggregate(
                total_hours=Sum('total_hours'),
                total_overtime=Sum('overtime_hours'),
                total_days=Count('id'),
                days_present=Count('id', filter=Q(status='present')),
                days_late=Count('id', filter=Q(status='late')),
            )
            
            context['monthly_hours'] = monthly_stats['total_hours'] or 0
            context['overtime_hours'] = monthly_stats['total_overtime'] or 0
            context['days_worked'] = monthly_stats['total_days'] or 0
            context['days_present'] = monthly_stats['days_present'] or 0
            context['days_late'] = monthly_stats['days_late'] or 0
            
            # Verificar si hay registro activo hoy
            today_record = attendance_records.filter(date=today).first()
            context['today_record'] = today_record
            
            # Determinar estado actual
            if today_record:
                if today_record.clock_in and not today_record.clock_out:
                    context['is_working'] = True
                    context['work_start_time'] = today_record.clock_in
                    # Verificar si está en descanso
                    context['is_on_break'] = (today_record.break_start and not today_record.break_end)
                else:
                    context['is_working'] = False
                    context['is_on_break'] = False
            else:
                context['is_working'] = False
                context['is_on_break'] = False
            
        except ImportError:
            # Si no existe la app de attendance, usar valores por defecto
            context['attendance_records'] = []
            context['monthly_hours'] = 0
            context['overtime_hours'] = 0
            context['days_worked'] = 0
            context['is_working'] = False
            context['is_on_break'] = False
            context['today_record'] = None
        
        # Calcular promedio diario
        if context['days_worked'] > 0:
            context['daily_average'] = round(float(context['monthly_hours']) / context['days_worked'], 1)
        else:
            context['daily_average'] = 0.0
        
        return context


class EmployeeRequestsView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista de solicitudes del empleado (vacaciones, permisos, etc.) ACTUALIZADA"""
    template_name = 'pages/employee/requests/requests.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        context['employee'] = employee
        
        if LEAVES_APP_AVAILABLE:
            # Solicitudes de licencia del empleado
            leave_requests = LeaveRequest.objects.filter(
                employee=employee
            ).select_related('leave_type', 'approved_by').order_by('-created_at')
            
            context['leave_requests'] = leave_requests
            
            # Estadísticas de solicitudes
            requests_stats = {
                'total': leave_requests.count(),
                'pending': leave_requests.filter(status='pending').count(),
                'approved': leave_requests.filter(status='approved').count(),
                'rejected': leave_requests.filter(status='rejected').count()
            }
            context['requests_stats'] = requests_stats
            
            # Balance de licencias del año actual
            current_year = timezone.now().year
            leave_balances = LeaveBalance.objects.filter(
                employee=employee,
                year=current_year
            ).select_related('leave_type')
            
            context['leave_balances'] = leave_balances
            
            # Tipos de licencia disponibles
            available_leave_types = LeaveType.objects.filter(is_active=True)
            context['available_leave_types'] = available_leave_types
            
            # Solicitudes urgentes o próximas
            urgent_requests = leave_requests.filter(
                status='pending',
                start_date__lte=timezone.now().date() + timedelta(days=7)
            )[:3]
            context['urgent_requests'] = urgent_requests
            
            # Calcular balance de vacaciones específico
            vacation_balance = 15  # Valor por defecto
            for balance in leave_balances:
                if balance.leave_type.code == 'VAC':  # Código para vacaciones
                    vacation_balance = balance.remaining_days
                    break
            context['vacation_balance'] = vacation_balance
            
        else:
            # Si no hay app de licencias, establecer valores por defecto
            context['leave_requests'] = []
            context['requests_stats'] = {
                'total': 0, 'pending': 0, 'approved': 0, 'rejected': 0
            }
            context['leave_balances'] = []
            context['available_leave_types'] = []
            context['urgent_requests'] = []
            context['vacation_balance'] = 15
        
        # Placeholder para otros tipos de solicitudes futuras
        context['other_requests'] = []
        
        return context


# AGREGAR ESTA NUEVA VISTA DESPUÉS DE EmployeeRequestsView:

# REEMPLAZAR LA CLASE EmployeeLeaveRequestCreateView CON ESTA VERSIÓN MEJORADA:

class EmployeeLeaveRequestCreateView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, CreateView):
    """Vista para que el empleado cree solicitudes de licencia desde su portal"""
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'pages/employee/requests/create_leave_request.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        try:
            # Asignar el empleado actual
            form.instance.employee = self.request.user.employee_profile
            
            # Calcular días solicitados automáticamente
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            if start_date and end_date:
                form.instance.days_requested = (end_date - start_date).days + 1
            
            # Validaciones adicionales
            leave_type = form.cleaned_data['leave_type']
            
            # Validar anticipación para vacaciones
            if leave_type.code == 'VAC':  # Código para vacaciones
                days_ahead = (start_date - timezone.now().date()).days
                if days_ahead < 15:
                    messages.error(
                        self.request, 
                        'Las vacaciones deben solicitarse con al menos 15 días de anticipación.'
                    )
                    return self.form_invalid(form)
            
            # Validar balance disponible
            if LEAVES_APP_AVAILABLE:
                try:
                    balance = LeaveBalance.objects.get(
                        employee=form.instance.employee,
                        leave_type=leave_type,
                        year=start_date.year
                    )
                    if balance.remaining_days < form.instance.days_requested:
                        messages.error(
                            self.request, 
                            f'No tienes suficientes días disponibles. '
                            f'Disponible: {balance.remaining_days} días, '
                            f'Solicitado: {form.instance.days_requested} días.'
                        )
                        return self.form_invalid(form)
                except LeaveBalance.DoesNotExist:
                    # Si no existe balance, usar los días permitidos del tipo
                    if leave_type.days_allowed < form.instance.days_requested:
                        messages.error(
                            self.request, 
                            f'Los días solicitados ({form.instance.days_requested}) '
                            f'exceden el límite permitido ({leave_type.days_allowed} días).'
                        )
                        return self.form_invalid(form)
            
            # Intentar guardar
            response = super().form_valid(form)
            
            messages.success(
                self.request, 
                f'Tu solicitud de {leave_type.name} ha sido enviada correctamente. '
                f'Será revisada por tu supervisor.'
            )
            
            return response
            
        except Exception as e:
            # Debug: mostrar el error específico
            messages.error(
                self.request, 
                f'Error al crear la solicitud: {str(e)}'
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        # Debug: mostrar errores específicos del formulario
        if form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(
                        self.request, 
                        f'Error en {field}: {error}'
                    )
        
        # Debug: mostrar errores no relacionados con campos
        if form.non_field_errors():
            for error in form.non_field_errors():
                messages.error(self.request, f'Error: {error}')
        
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse('employees:employee_requests')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee'] = self.request.user.employee_profile
        context['title'] = 'Nueva Solicitud de Licencia'
        
        # Obtener balances disponibles
        if LEAVES_APP_AVAILABLE:
            current_year = timezone.now().year
            context['leave_balances'] = LeaveBalance.objects.filter(
                employee=self.request.user.employee_profile,
                year=current_year
            ).select_related('leave_type')
        else:
            context['leave_balances'] = []
        
        return context


# AGREGAR ESTA VISTA PARA VER DETALLES DE UNA SOLICITUD:

class EmployeeLeaveRequestDetailView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, DetailView):
    """Vista para ver detalles de una solicitud de licencia del empleado"""
    model = LeaveRequest
    template_name = 'pages/employee/requests/leave_request_detail.html'
    context_object_name = 'leave_request'
    
    def get_queryset(self):
        # Solo permitir ver propias solicitudes
        return LeaveRequest.objects.filter(
            employee=self.request.user.employee_profile
        ).select_related('leave_type', 'approved_by')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee'] = self.request.user.employee_profile
        
        # Verificar si se puede editar (solo pendientes)
        context['can_edit'] = self.object.status == 'pending'
        
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


# ==================== APIS PARA TAREAS (OPCIONALES) ====================

@login_required
def employee_task_stats_api(request):
    """API para estadísticas de tareas del empleado"""
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if not TASKS_APP_AVAILABLE:
        return JsonResponse({'error': 'Tasks app not available'}, status=404)
    
    employee = request.user.employee_profile
    
    # Estadísticas por estado
    status_stats = TaskAssignment.objects.filter(employee=employee).values('status').annotate(
        count=Count('id')
    )
    
    # Productividad semanal (últimas 4 semanas)
    weeks_data = []
    for i in range(4):
        week_start = timezone.now() - timedelta(weeks=i+1)
        week_end = timezone.now() - timedelta(weeks=i)
        
        completed = TaskAssignment.objects.filter(
            employee=employee,
            status='completed',
            completed_at__range=[week_start, week_end]
        ).count()
        
        hours_worked = TaskProgress.objects.filter(
            assignment__employee=employee,
            timestamp__range=[week_start, week_end]
        ).aggregate(Sum('hours_worked_session'))['hours_worked_session__sum'] or 0
        
        weeks_data.append({
            'week': f'Semana {4-i}',
            'completed': completed,
            'hours': float(hours_worked)
        })
    
    # Distribución por categoría
    category_stats = TaskAssignment.objects.filter(employee=employee).values(
        'task__category__name', 'task__category__color'
    ).annotate(count=Count('id'))
    
    # Earnings por mes (últimos 6 meses)
    earnings_data = []
    for i in range(6):
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30*i)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_end = month_end - timedelta(days=month_end.day)
        
        completed_assignments = TaskAssignment.objects.filter(
            employee=employee,
            status='completed',
            completed_at__range=[month_start, month_end]
        )
        
        month_earnings = sum(assignment.calculated_payment for assignment in completed_assignments)
        
        earnings_data.append({
            'month': month_start.strftime('%B %Y'),
            'earnings': float(month_earnings)
        })
    
    return JsonResponse({
        'status_stats': list(status_stats),
        'productivity': weeks_data,
        'category_stats': list(category_stats),
        'earnings': list(reversed(earnings_data))
    })