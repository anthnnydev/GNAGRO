# core/employees/views/supervisor_portal.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, ListView, DetailView
from django.urls import reverse_lazy
from django.db.models import Q, Count, Sum, Avg
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta

from core.employees.models import Employee
from core.employees.views.employee_portal import EmployeePasswordChangeRequiredMixin

# IMPORTACIONES PARA TAREAS
try:
    from core.tasks.models import Task, TaskAssignment, TaskProgress, TaskComment, TaskCategory
    TASKS_APP_AVAILABLE = True
except ImportError:
    TASKS_APP_AVAILABLE = False

# IMPORTACIONES PARA ASISTENCIA
try:
    from core.attendance.models import Attendance, EmployeeSchedule
    ATTENDANCE_APP_AVAILABLE = True
except ImportError:
    ATTENDANCE_APP_AVAILABLE = False

# IMPORTACIONES PARA LICENCIAS
try:
    from core.leaves.models import LeaveRequest, LeaveBalance
    LEAVES_APP_AVAILABLE = True
except ImportError:
    LEAVES_APP_AVAILABLE = False


class SupervisorRequiredMixin:
    """Mixin simplificado que verifica permisos de supervisor"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        
        if not hasattr(request.user, 'employee_profile'):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'No tienes un perfil de empleado asociado.',
                    'error_type': 'no_profile',
                    'redirect_url': reverse_lazy('employees:employee_dashboard')
                }, status=403)
            
            messages.error(request, 'No tienes un perfil de empleado asociado.')
            return redirect('employees:employee_dashboard')
        
        # Verificar permisos: por user_type O por grupo
        user_type = getattr(request.user, 'user_type', 'employee')
        is_supervisor_by_type = user_type in ['supervisor', 'admin']
        is_supervisor_by_group = request.user.groups.filter(
            name__in=['Supervisores', 'Administradores']
        ).exists()
        
        if not (is_supervisor_by_type or is_supervisor_by_group):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Solo supervisores y administradores pueden acceder a esta sección.',
                    'error_type': 'permission_denied',
                    'redirect_url': reverse_lazy('employees:employee_dashboard')
                }, status=403)
            
            messages.error(request, 'Solo supervisores y administradores pueden acceder a esta sección.')
            return redirect('employees:employee_dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class SupervisorDashboardView(SupervisorRequiredMixin, LoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Dashboard principal del supervisor UNIFICADO"""
    template_name = 'pages/supervisor/dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supervisor = self.request.user.employee_profile
        
        # ==================== INFORMACIÓN PERSONAL DEL SUPERVISOR ====================
        context['supervisor'] = supervisor
        context['employee'] = supervisor  # Para compatibilidad con templates
        
        # Información del departamento
        context['department_info'] = supervisor.department
        context['position_info'] = supervisor.position
        
        # Empleados bajo supervisión
        subordinates = Employee.objects.filter(
            Q(supervisor=supervisor) |
            Q(department=supervisor.department, user__user_type='employee')
        ).filter(status='active')
        
        context['subordinates_count'] = subordinates.count()
        context['subordinates'] = subordinates[:8]  # Mostrar los primeros 8
        
        # ==================== ESTADÍSTICAS DE TAREAS ====================
        if TASKS_APP_AVAILABLE:
            # Estadísticas de tareas como supervisor
            tasks_stats = Task.objects.filter(supervisor=supervisor).aggregate(
                total=Count('id'),
                active=Count('id', filter=Q(status__in=['assigned', 'in_progress'])),
                completed=Count('id', filter=Q(status='completed')),
                overdue=Count('id', filter=Q(
                    status__in=['assigned', 'in_progress'],
                    end_date__lt=timezone.now()
                )),
                draft=Count('id', filter=Q(status='draft'))
            )
            context['tasks_stats'] = tasks_stats
            
            # Tareas urgentes
            urgent_tasks = Task.objects.filter(
                supervisor=supervisor,
                priority='urgent',
                status__in=['assigned', 'in_progress']
            ).order_by('end_date')[:5]
            context['urgent_tasks'] = urgent_tasks
            
            # Tareas recientes creadas
            recent_tasks = Task.objects.filter(
                supervisor=supervisor
            ).select_related('category').prefetch_related('assigned_employees').order_by('-created_at')[:5]
            context['recent_tasks'] = recent_tasks
            
            # Actividad reciente de su equipo
            recent_activity = TaskProgress.objects.filter(
                assignment__task__supervisor=supervisor
            ).select_related(
                'assignment__employee__user',
                'assignment__task'
            ).order_by('-timestamp')[:8]
            context['recent_activity'] = recent_activity
            
            # Estadísticas de asignaciones de su equipo
            team_assignments_stats = TaskAssignment.objects.filter(
                task__supervisor=supervisor
            ).aggregate(
                total_assignments=Count('id'),
                pending_assignments=Count('id', filter=Q(status='pending')),
                in_progress_assignments=Count('id', filter=Q(status='in_progress')),
                completed_assignments=Count('id', filter=Q(status='completed')),
                total_hours_worked=Sum('hours_worked') or 0
            )
            context['team_assignments_stats'] = team_assignments_stats
            
            # Estadísticas por categoría
            category_stats = Task.objects.filter(supervisor=supervisor).values(
                'category__name', 'category__color'
            ).annotate(count=Count('id'))[:6]
            context['category_stats'] = category_stats
            
        else:
            # Valores por defecto si no hay app de tareas
            context['tasks_stats'] = {
                'total': 0, 'active': 0, 'completed': 0, 'overdue': 0, 'draft': 0
            }
            context['urgent_tasks'] = []
            context['recent_tasks'] = []
            context['recent_activity'] = []
            context['team_assignments_stats'] = {
                'total_assignments': 0, 'pending_assignments': 0, 
                'in_progress_assignments': 0, 'completed_assignments': 0, 'total_hours_worked': 0
            }
            context['category_stats'] = []
        
        # ==================== ESTADÍSTICAS DE ASISTENCIA DEL EQUIPO ====================
        if ATTENDANCE_APP_AVAILABLE:
            today = timezone.now().date()
            
            # Asistencia del equipo hoy
            team_attendance_today = Attendance.objects.filter(
                employee__in=subordinates,
                date=today
            ).aggregate(
                present_count=Count('id', filter=Q(status='present')),
                late_count=Count('id', filter=Q(status='late')),
                absent_count=Count('id', filter=Q(status='absent'))
            )
            context['team_attendance_today'] = team_attendance_today
            
            # Empleados actualmente trabajando
            working_now = Attendance.objects.filter(
                employee__in=subordinates,
                date=today,
                clock_in__isnull=False,
                clock_out__isnull=True
            ).select_related('employee__user')
            context['working_now'] = working_now
            
        else:
            context['team_attendance_today'] = {
                'present_count': 0, 'late_count': 0, 'absent_count': 0
            }
            context['working_now'] = []
        
        # ==================== SOLICITUDES DE LICENCIA PENDIENTES ====================
        if LEAVES_APP_AVAILABLE:
            pending_leave_requests = LeaveRequest.objects.filter(
                employee__in=subordinates,
                status='pending'
            ).select_related('employee__user', 'leave_type').order_by('created_at')[:5]
            context['pending_leave_requests'] = pending_leave_requests
            
            # Estadísticas de licencias
            leave_stats = LeaveRequest.objects.filter(
                employee__in=subordinates
            ).aggregate(
                total_requests=Count('id'),
                pending_requests=Count('id', filter=Q(status='pending')),
                approved_requests=Count('id', filter=Q(status='approved')),
                rejected_requests=Count('id', filter=Q(status='rejected'))
            )
            context['leave_stats'] = leave_stats
            
        else:
            context['pending_leave_requests'] = []
            context['leave_stats'] = {
                'total_requests': 0, 'pending_requests': 0, 
                'approved_requests': 0, 'rejected_requests': 0
            }
        
        # ==================== INFORMACIÓN ADICIONAL ====================
        
        # Cálculos de productividad del equipo
        if context['team_assignments_stats']['total_assignments'] > 0:
            context['team_completion_rate'] = int(
                (context['team_assignments_stats']['completed_assignments'] / 
                 context['team_assignments_stats']['total_assignments']) * 100
            )
        else:
            context['team_completion_rate'] = 100
        
        # Empleados más productivos (top 5)
        if TASKS_APP_AVAILABLE:
            top_employees = TaskAssignment.objects.filter(
                task__supervisor=supervisor,
                status='completed'
            ).values(
                'employee__user__first_name',
                'employee__user__last_name',
                'employee__id'
            ).annotate(
                completed_tasks=Count('id'),
                total_hours=Sum('hours_worked')
            ).order_by('-completed_tasks')[:5]
            context['top_employees'] = top_employees
        else:
            context['top_employees'] = []
        
        return context


class SupervisorTeamView(SupervisorRequiredMixin, LoginRequiredMixin, EmployeePasswordChangeRequiredMixin, ListView):
    """Vista del equipo del supervisor"""
    template_name = 'pages/supervisor/team/team_list.html'
    context_object_name = 'team_members'
    paginate_by = 20
    
    def get_queryset(self):
        supervisor = self.request.user.employee_profile
        return Employee.objects.filter(
            Q(supervisor=supervisor) |
            Q(department=supervisor.department, user__user_type='employee')
        ).filter(status='active').select_related('user', 'position', 'department')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supervisor = self.request.user.employee_profile
        context['supervisor'] = supervisor
        
        # Estadísticas del equipo
        team_members = self.get_queryset()
        context['total_team_members'] = team_members.count()
        
        # Distribución por posición
        position_distribution = team_members.values(
            'position__title'
        ).annotate(count=Count('id')).order_by('-count')
        context['position_distribution'] = position_distribution
        
        return context


class SupervisorEmployeeDetailView(SupervisorRequiredMixin, LoginRequiredMixin, EmployeePasswordChangeRequiredMixin, DetailView):
    """Vista detallada de un empleado del equipo"""
    model = Employee
    template_name = 'pages/supervisor/team/employee_detail.html'
    context_object_name = 'team_member'
    
    def get_queryset(self):
        supervisor = self.request.user.employee_profile
        return Employee.objects.filter(
            Q(supervisor=supervisor) |
            Q(department=supervisor.department, user__user_type='employee')
        ).select_related('user', 'position', 'department', 'supervisor')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supervisor = self.request.user.employee_profile
        employee = self.object
        
        context['supervisor'] = supervisor
        
        # Estadísticas de tareas del empleado
        if TASKS_APP_AVAILABLE:
            task_stats = TaskAssignment.objects.filter(
                employee=employee,
                task__supervisor=supervisor
            ).aggregate(
                total_tasks=Count('id'),
                completed_tasks=Count('id', filter=Q(status='completed')),
                pending_tasks=Count('id', filter=Q(status='pending')),
                in_progress_tasks=Count('id', filter=Q(status='in_progress')),
                total_hours=Sum('hours_worked') or 0
            )
            context['task_stats'] = task_stats
            
            # Tareas recientes del empleado
            recent_assignments = TaskAssignment.objects.filter(
                employee=employee,
                task__supervisor=supervisor
            ).select_related('task').order_by('-assigned_at')[:10]
            context['recent_assignments'] = recent_assignments
        else:
            context['task_stats'] = {
                'total_tasks': 0, 'completed_tasks': 0, 'pending_tasks': 0, 
                'in_progress_tasks': 0, 'total_hours': 0
            }
            context['recent_assignments'] = []
        
        # Estadísticas de asistencia del empleado
        if ATTENDANCE_APP_AVAILABLE:
            current_month = timezone.now().replace(day=1)
            attendance_stats = Attendance.objects.filter(
                employee=employee,
                date__gte=current_month
            ).aggregate(
                total_days=Count('id'),
                present_days=Count('id', filter=Q(status='present')),
                late_days=Count('id', filter=Q(status='late')),
                total_hours=Sum('total_hours') or 0
            )
            context['attendance_stats'] = attendance_stats
        else:
            context['attendance_stats'] = {
                'total_days': 0, 'present_days': 0, 'late_days': 0, 'total_hours': 0
            }
        
        return context


class SupervisorReportsView(SupervisorRequiredMixin, LoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista de reportes del supervisor"""
    template_name = 'pages/supervisor/reports/reports.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supervisor = self.request.user.employee_profile
        
        context['supervisor'] = supervisor
        
        # Obtener empleados del equipo
        subordinates = Employee.objects.filter(
            Q(supervisor=supervisor) |
            Q(department=supervisor.department, user__user_type='employee')
        ).filter(status='active')
        
        # Reportes de productividad
        if TASKS_APP_AVAILABLE:
            # Productividad por empleado
            productivity_by_employee = []
            for employee in subordinates:
                stats = TaskAssignment.objects.filter(
                    employee=employee,
                    task__supervisor=supervisor
                ).aggregate(
                    total_tasks=Count('id'),
                    completed_tasks=Count('id', filter=Q(status='completed')),
                    total_hours=Sum('hours_worked') or 0
                )
                stats['employee'] = employee
                if stats['total_tasks'] > 0:
                    stats['completion_rate'] = int((stats['completed_tasks'] / stats['total_tasks']) * 100)
                else:
                    stats['completion_rate'] = 0
                productivity_by_employee.append(stats)
            
            context['productivity_by_employee'] = sorted(
                productivity_by_employee, 
                key=lambda x: x['completion_rate'], 
                reverse=True
            )
            
            # Estadísticas por mes (últimos 6 meses)
            monthly_stats = []
            for i in range(6):
                month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
                month_end = month_start.replace(day=28) + timedelta(days=4)
                month_end = month_end - timedelta(days=month_end.day)
                
                stats = TaskAssignment.objects.filter(
                    task__supervisor=supervisor,
                    assigned_at__range=[month_start, month_end]
                ).aggregate(
                    assigned=Count('id'),
                    completed=Count('id', filter=Q(status='completed')),
                    total_hours=Sum('hours_worked') or 0
                )
                stats['month'] = month_start.strftime('%B %Y')
                monthly_stats.append(stats)
            
            context['monthly_stats'] = list(reversed(monthly_stats))
        else:
            context['productivity_by_employee'] = []
            context['monthly_stats'] = []
        
        return context


# APIs y funciones auxiliares
@login_required
def supervisor_stats_api(request):
    """API para estadísticas del supervisor"""
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Verificar permisos de supervisor
    user_type = getattr(request.user, 'user_type', 'employee')
    if user_type not in ['supervisor', 'admin', 'hr']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    supervisor = request.user.employee_profile
    
    # Obtener empleados del equipo
    subordinates = Employee.objects.filter(
        Q(supervisor=supervisor) |
        Q(department=supervisor.department, user__user_type='employee')
    ).filter(status='active')
    
    stats = {
        'team_size': subordinates.count(),
        'tasks_created': 0,
        'tasks_completed': 0,
        'team_productivity': 0,
        'pending_approvals': 0
    }
    
    if TASKS_APP_AVAILABLE:
        # Estadísticas de tareas
        task_stats = Task.objects.filter(supervisor=supervisor).aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed'))
        )
        stats['tasks_created'] = task_stats['total']
        stats['tasks_completed'] = task_stats['completed']
        
        # Productividad del equipo
        team_assignments = TaskAssignment.objects.filter(
            task__supervisor=supervisor
        ).aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed'))
        )
        
        if team_assignments['total'] > 0:
            stats['team_productivity'] = int(
                (team_assignments['completed'] / team_assignments['total']) * 100
            )
    
    if LEAVES_APP_AVAILABLE:
        # Solicitudes pendientes de aprobación
        stats['pending_approvals'] = LeaveRequest.objects.filter(
            employee__in=subordinates,
            status='pending'
        ).count()
    
    return JsonResponse(stats)


@login_required
def supervisor_team_performance_api(request):
    """API para rendimiento del equipo"""
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Verificar permisos de supervisor
    user_type = getattr(request.user, 'user_type', 'employee')
    if user_type not in ['supervisor', 'admin', 'hr']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    supervisor = request.user.employee_profile
    
    # Obtener empleados del equipo
    subordinates = Employee.objects.filter(
        Q(supervisor=supervisor) |
        Q(department=supervisor.department, user__user_type='employee')
    ).filter(status='active')
    
    performance_data = []
    
    if TASKS_APP_AVAILABLE:
        for employee in subordinates:
            stats = TaskAssignment.objects.filter(
                employee=employee,
                task__supervisor=supervisor
            ).aggregate(
                total_tasks=Count('id'),
                completed_tasks=Count('id', filter=Q(status='completed')),
                total_hours=Sum('hours_worked') or 0
            )
            
            completion_rate = 0
            if stats['total_tasks'] > 0:
                completion_rate = int((stats['completed_tasks'] / stats['total_tasks']) * 100)
            
            performance_data.append({
                'employee_name': employee.user.get_full_name(),
                'total_tasks': stats['total_tasks'],
                'completed_tasks': stats['completed_tasks'],
                'total_hours': float(stats['total_hours']),
                'completion_rate': completion_rate
            })
    
    return JsonResponse({'performance_data': performance_data})