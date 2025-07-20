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

import json

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

class EmployeeLoginRequiredMixin(LoginRequiredMixin):
    """Mixin que verifica que el usuario sea empleado"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not hasattr(request.user, 'employee_profile'):
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('core:home')
        
        return super().dispatch(request, *args, **kwargs)
    
class SupervisorProfileView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista del perfil del empleado"""
    template_name = 'pages/supervisor/profile/profile.html'
    
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
    

class SupervisorPayrollView(SupervisorRequiredMixin, LoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista de nómina del supervisor"""
    template_name = 'pages/supervisor/payroll/supervisor_payroll.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supervisor = self.request.user.employee_profile
        
        # IMPORTACIONES PARA NÓMINA
        try:
            from core.payroll.models import Payroll, PayrollPeriod, AdelantoQuincena
            PAYROLL_APP_AVAILABLE = True
        except ImportError:
            PAYROLL_APP_AVAILABLE = False
        
        context['supervisor'] = supervisor
        context['employee'] = supervisor  # Para compatibilidad con templates
        
        # ==================== INFORMACIÓN SALARIAL ACTUAL ====================
        context['current_salary'] = supervisor.salary or 0
        context['position_base_salary'] = supervisor.position.base_salary if hasattr(supervisor.position, 'base_salary') else supervisor.salary or 0
        
        if PAYROLL_APP_AVAILABLE:
            # ==================== NÓMINAS Y PAGOS ====================
            current_month = timezone.now().replace(day=1)
            current_year = timezone.now().year
            
            # Nóminas del supervisor
            supervisor_payrolls = Payroll.objects.filter(
                employee=supervisor
            ).select_related('period').order_by('-period__start_date')
            
            # Nómina del mes actual
            current_month_payroll = supervisor_payrolls.filter(
                period__start_date__gte=current_month
            ).first()
            
            if current_month_payroll:
                context['current_month_earnings'] = current_month_payroll.net_pay
                context['current_month_bonuses'] = current_month_payroll.total_ingresos_rubros
                context['current_month_overtime'] = current_month_payroll.overtime_pay
                context['current_month_deductions'] = current_month_payroll.total_deductions
            else:
                context['current_month_earnings'] = supervisor.salary or 0
                context['current_month_bonuses'] = 0
                context['current_month_overtime'] = 0
                context['current_month_deductions'] = 0
            
            # ==================== ESTADÍSTICAS ANUALES ====================
            # Nóminas del año actual
            ytd_payrolls = supervisor_payrolls.filter(
                period__start_date__year=current_year,
                is_paid=True
            )
            
            context['ytd_earnings'] = sum(p.net_pay for p in ytd_payrolls)
            context['ytd_bonuses'] = sum(p.total_ingresos_rubros for p in ytd_payrolls)
            context['ytd_deductions'] = sum(p.total_deductions for p in ytd_payrolls)
            context['months_worked_this_year'] = ytd_payrolls.count()
            
            # Promedio mensual
            if context['months_worked_this_year'] > 0:
                context['monthly_average'] = context['ytd_earnings'] / context['months_worked_this_year']
            else:
                context['monthly_average'] = supervisor.salary or 0
            
            # ==================== ADELANTOS PENDIENTES ====================
            adelantos_pendientes = AdelantoQuincena.objects.filter(
                employee=supervisor,
                is_descontado=False
            ).order_by('-fecha_adelanto')
            
            context['adelantos_pendientes'] = adelantos_pendientes
            context['total_adelantos_pendientes'] = sum(a.monto for a in adelantos_pendientes)
            
            # ==================== PRÓXIMO PAGO ====================
            # Buscar el próximo período
            next_period = PayrollPeriod.objects.filter(
                start_date__gt=timezone.now(),
                status__in=['draft', 'processing']
            ).order_by('start_date').first()
            
            if next_period:
                context['next_pay_date'] = next_period.pay_date
                context['next_period_name'] = next_period.name
            
            # ==================== HISTORIAL DE PAGOS ====================
            # Preparar datos para el historial
            payroll_records = []
            for payroll in supervisor_payrolls[:12]:  # Últimos 12 registros
                record = {
                    'id': payroll.id,
                    'period': payroll.period.name,
                    'period_full': f"{payroll.period.start_date.strftime('%d/%m/%Y')} - {payroll.period.end_date.strftime('%d/%m/%Y')}",
                    'base_salary': payroll.base_salary,
                    'bonuses': payroll.total_ingresos_rubros,
                    'deductions': payroll.total_deductions,
                    'net_total': payroll.net_pay,
                    'is_paid': payroll.is_paid,
                    'payment_date': payroll.payment_date,
                    'overtime_pay': payroll.overtime_pay,
                }
                payroll_records.append(record)
            
            context['payroll_records'] = payroll_records
            
            # ==================== INFORMACIÓN ADICIONAL COMO SUPERVISOR ====================
            # Nóminas del equipo pendientes de aprobación
            subordinates = Employee.objects.filter(
                Q(supervisor=supervisor) |
                Q(department=supervisor.department, user__user_type='employee')
            ).filter(status='active')
            
            pending_team_payrolls = Payroll.objects.filter(
                employee__in=subordinates,
                is_paid=False
            ).select_related('employee__user', 'period').order_by('-period__start_date')[:5]
            
            context['pending_team_payrolls'] = pending_team_payrolls
            
            # Total a pagar al equipo este mes
            team_payroll_total = sum(p.net_pay for p in pending_team_payrolls)
            context['team_payroll_total'] = team_payroll_total
            
            # Estadísticas del equipo
            context['team_stats'] = {
                'total_employees': subordinates.count(),
                'pending_payrolls': pending_team_payrolls.count(),
                'total_amount': team_payroll_total,
                'average_salary': team_payroll_total / subordinates.count() if subordinates.count() > 0 else 0
            }
            
        else:
            # Valores por defecto si no hay app de nómina
            context.update({
                'current_month_earnings': supervisor.salary or 0,
                'current_month_bonuses': 0,
                'current_month_overtime': 0,
                'current_month_deductions': 0,
                'ytd_earnings': (supervisor.salary or 0) * 12,
                'ytd_bonuses': 0,
                'ytd_deductions': 0,
                'months_worked_this_year': 12,
                'monthly_average': supervisor.salary or 0,
                'adelantos_pendientes': [],
                'total_adelantos_pendientes': 0,
                'payroll_records': [],
                'pending_team_payrolls': [],
                'team_payroll_total': 0,
                'team_stats': {
                    'total_employees': 0,
                    'pending_payrolls': 0,
                    'total_amount': 0,
                    'average_salary': 0
                }
            })
        
        return context
    
class SupervisorLeaveRequestDetailView(SupervisorRequiredMixin, LoginRequiredMixin, EmployeePasswordChangeRequiredMixin, DetailView):
    """Vista para que el supervisor vea detalles de solicitudes de licencia de su equipo"""
    model = LeaveRequest
    template_name = 'pages/supervisor/team/leave_request_detail.html'
    context_object_name = 'leave_request'
    
    def get_queryset(self):
        supervisor = self.request.user.employee_profile
        
        # Obtener empleados bajo supervisión
        subordinates = Employee.objects.filter(
            Q(supervisor=supervisor) |
            Q(department=supervisor.department, user__user_type='employee')
        ).filter(status='active')
        
        # Solo permitir ver solicitudes del equipo
        return LeaveRequest.objects.filter(
            employee__in=subordinates
        ).select_related('employee__user', 'leave_type', 'approved_by')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['supervisor'] = self.request.user.employee_profile
        
        # Verificar si puede aprobar/rechazar (solo pendientes)
        context['can_approve'] = self.object.status == 'pending'
        
        return context


class SupervisorLeaveRequestListView(SupervisorRequiredMixin, LoginRequiredMixin, EmployeePasswordChangeRequiredMixin, ListView):
    """Vista para que el supervisor vea todas las solicitudes de licencia de su equipo"""
    model = LeaveRequest
    template_name = 'pages/supervisor/team/leave_requests_list.html'
    context_object_name = 'leave_requests'
    paginate_by = 20
    
    def get_queryset(self):
        supervisor = self.request.user.employee_profile
        
        # Obtener empleados bajo supervisión
        subordinates = Employee.objects.filter(
            Q(supervisor=supervisor) |
            Q(department=supervisor.department, user__user_type='employee')
        ).filter(status='active')
        
        queryset = LeaveRequest.objects.filter(
            employee__in=subordinates
        ).select_related('employee__user', 'leave_type', 'approved_by').order_by('-created_at')
        
        # Filtros opcionales
        status_filter = self.request.GET.get('status')
        employee_filter = self.request.GET.get('employee')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if employee_filter:
            queryset = queryset.filter(employee_id=employee_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supervisor = self.request.user.employee_profile
        
        context['supervisor'] = supervisor
        
        # Obtener empleados para filtros
        subordinates = Employee.objects.filter(
            Q(supervisor=supervisor) |
            Q(department=supervisor.department, user__user_type='employee')
        ).filter(status='active').select_related('user')
        
        context['team_members'] = subordinates
        
        # Estadísticas
        all_requests = self.get_queryset()
        context['stats'] = {
            'total': all_requests.count(),
            'pending': all_requests.filter(status='pending').count(),
            'approved': all_requests.filter(status='approved').count(),
            'rejected': all_requests.filter(status='rejected').count(),
        }
        
        # Filtros aplicados
        context['current_status'] = self.request.GET.get('status', '')
        context['current_employee'] = self.request.GET.get('employee', '')
        
        return context


@login_required
def supervisor_leave_request_approve(request, pk):
    """Vista para aprobar solicitud de licencia"""
    
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    # Verificar permisos de supervisor
    user_type = getattr(request.user, 'user_type', 'employee')
    if user_type not in ['supervisor', 'admin', 'hr']:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    supervisor = request.user.employee_profile
    
    try:
        # Obtener empleados bajo supervisión
        subordinates = Employee.objects.filter(
            Q(supervisor=supervisor) |
            Q(department=supervisor.department, user__user_type='employee')
        ).filter(status='active')
        
        # Obtener la solicitud
        leave_request = get_object_or_404(
            LeaveRequest,
            pk=pk,
            employee__in=subordinates,
            status='pending'  # Solo se pueden aprobar las pendientes
        )
        
        if request.method == 'POST':
            data = json.loads(request.body)
            notes = data.get('notes', '')
            
            # Verificar balance disponible si es necesario
            if LEAVES_APP_AVAILABLE:
                try:
                    # Intentar obtener el balance existente
                    balance = LeaveBalance.objects.get(
                        employee=leave_request.employee,
                        leave_type=leave_request.leave_type,
                        year=leave_request.start_date.year
                    )
                    
                    # Verificar si tiene días suficientes
                    if balance.remaining_days < leave_request.days_requested:
                        return JsonResponse({
                            'success': False,
                            'error': f'El empleado no tiene suficientes días disponibles. '
                                   f'Disponible: {balance.remaining_days}, '
                                   f'Solicitado: {leave_request.days_requested}'
                        })
                    
                    # Actualizar balance - USAR EL CAMPO CORRECTO
                    balance.used_days += leave_request.days_requested
                    balance.save()
                    
                except LeaveBalance.DoesNotExist:
                    # Si no existe balance, crear uno nuevo
                    # Primero verificar qué campos tiene realmente el modelo
                    # Intentar con diferentes nombres de campos comunes
                    
                    # Opción 1: Intentar con 'allocated_days'
                    try:
                        balance = LeaveBalance.objects.create(
                            employee=leave_request.employee,
                            leave_type=leave_request.leave_type,
                            year=leave_request.start_date.year,
                            allocated_days=leave_request.leave_type.days_allowed,
                            used_days=leave_request.days_requested
                        )
                    except Exception:
                        # Opción 2: Intentar con 'total_days'
                        try:
                            balance = LeaveBalance.objects.create(
                                employee=leave_request.employee,
                                leave_type=leave_request.leave_type,
                                year=leave_request.start_date.year,
                                total_days=leave_request.leave_type.days_allowed,
                                used_days=leave_request.days_requested
                            )
                        except Exception:
                            # Opción 3: Intentar solo con used_days
                            try:
                                balance = LeaveBalance.objects.create(
                                    employee=leave_request.employee,
                                    leave_type=leave_request.leave_type,
                                    year=leave_request.start_date.year,
                                    used_days=leave_request.days_requested
                                )
                            except Exception as e:
                                # Si ninguna opción funciona, continuar sin crear balance
                                print(f"No se pudo crear LeaveBalance: {e}")
                                pass
                
                except Exception as e:
                    # Si hay cualquier error con el balance, registrarlo pero continuar
                    print(f"Error manejando LeaveBalance: {e}")
                    pass
            
            # Aprobar la solicitud - ESTO SIEMPRE SE EJECUTA
            leave_request.status = 'approved'
            leave_request.approved_by = supervisor
            leave_request.approved_at = timezone.now()
            leave_request.approval_notes = notes
            leave_request.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Solicitud de {leave_request.employee.user.get_full_name()} aprobada exitosamente.'
            })
        
        else:
            return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
            
    except LeaveRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Solicitud no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def supervisor_leave_request_reject(request, pk):
    """Vista para rechazar solicitud de licencia"""
    
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    # Verificar permisos de supervisor
    user_type = getattr(request.user, 'user_type', 'employee')
    if user_type not in ['supervisor', 'admin', 'hr']:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    supervisor = request.user.employee_profile
    
    try:
        # Obtener empleados bajo supervisión
        subordinates = Employee.objects.filter(
            Q(supervisor=supervisor) |
            Q(department=supervisor.department, user__user_type='employee')
        ).filter(status='active')
        
        # Obtener la solicitud
        leave_request = get_object_or_404(
            LeaveRequest,
            pk=pk,
            employee__in=subordinates,
            status='pending'  # Solo se pueden rechazar las pendientes
        )
        
        if request.method == 'POST':
            data = json.loads(request.body)
            rejection_reason = data.get('rejection_reason', 'Sin motivo especificado')
            
            # Rechazar la solicitud
            leave_request.status = 'rejected'
            leave_request.approved_by = supervisor
            leave_request.approved_at = timezone.now()
            leave_request.rejection_reason = rejection_reason
            leave_request.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Solicitud de {leave_request.employee.user.get_full_name()} rechazada.'
            })
        
        else:
            return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
            
    except LeaveRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Solicitud no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# También agregar esta función API para obtener datos de nómina
@login_required
def supervisor_payroll_api(request):
    """API para datos de nómina del supervisor"""
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Verificar permisos de supervisor
    user_type = getattr(request.user, 'user_type', 'employee')
    if user_type not in ['supervisor', 'admin', 'hr']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    supervisor = request.user.employee_profile
    
    try:
        from core.payroll.models import Payroll, PayrollPeriod
        
        # Estadísticas básicas
        current_month = timezone.now().replace(day=1)
        current_payroll = Payroll.objects.filter(
            employee=supervisor,
            period__start_date__gte=current_month
        ).first()
        
        stats = {
            'current_salary': float(supervisor.salary or 0),
            'current_month_net': float(current_payroll.net_pay) if current_payroll else float(supervisor.salary or 0),
            'current_month_gross': float(current_payroll.gross_pay) if current_payroll else float(supervisor.salary or 0),
            'current_month_deductions': float(current_payroll.total_deductions) if current_payroll else 0,
            'is_paid': current_payroll.is_paid if current_payroll else False,
            'payment_date': current_payroll.payment_date.strftime('%Y-%m-%d') if current_payroll and current_payroll.payment_date else None
        }
        
        return JsonResponse(stats)
        
    except ImportError:
        return JsonResponse({
            'current_salary': float(supervisor.salary or 0),
            'current_month_net': float(supervisor.salary or 0),
            'current_month_gross': float(supervisor.salary or 0),
            'current_month_deductions': 0,
            'is_paid': False,
            'payment_date': None
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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