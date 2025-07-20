from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone
from datetime import date, timedelta
from core.employees.models import Department, Employee, Position
from core.leaves.models import LeaveType, LeaveRequest, LeaveBalance
from core.attendance.models import WorkSchedule, EmployeeSchedule, Holiday, AttendanceRule
from core.users.models import Company  # Agregar esta importación

@login_required
def parameters_view(request):
    """
    Vista del perfil del usuario + estadísticas del dashboard
    """
    
    # Definir fecha actual al inicio
    today = date.today()
    current_year = today.year
    future_90_days = today + timedelta(days=90)
    future_30_days = today + timedelta(days=30)

    # ============ ESTADÍSTICAS DE EMPRESAS ============
    companies_stats = {
        'total': Company.objects.count(),
        'active': Company.objects.filter(is_active=True).count(),
        'inactive': Company.objects.filter(is_active=False).count(),
    }
    
    # Obtener la empresa activa
    active_company = Company.get_active_company()

    # Estadísticas de Departamentos
    departments_stats = {
        'total': Department.objects.count(),
        'active': Department.objects.filter(is_active=True).count(),
        'inactive': Department.objects.filter(is_active=False).count(),
    }

    # Estadísticas de Empleados
    # Using 'status' field instead of 'is_active' since Employee model doesn't have is_active
    employees_stats = {
        'total': Employee.objects.count(),
        'active': Employee.objects.filter(status='active').count(),
        'inactive': Employee.objects.exclude(status='active').count(),
    }
    
    # Estadísticas de Tipos de Permisos
    leaves_stats = {
        'total': LeaveType.objects.count(),
        'active': LeaveType.objects.filter(is_active=True).count(),
        'inactive': LeaveType.objects.filter(is_active=False).count(),
    }

    # Estadísticas de Posiciones/Cargos
    positions_stats = {
        'total': Position.objects.count(),
        'active': Position.objects.filter(is_active=True).count(),
        'inactive': Position.objects.filter(is_active=False).count(),
    }

    # ============ ESTADÍSTICAS DE ASISTENCIA ============
    
    # Estadísticas de Horarios de Trabajo
    schedules_stats = {
        'total': WorkSchedule.objects.count(),
        'active': WorkSchedule.objects.filter(is_active=True).count(),
        'inactive': WorkSchedule.objects.filter(is_active=False).count(),
        'by_type': {
            'fixed': WorkSchedule.objects.filter(schedule_type='fixed').count(),
            'flexible': WorkSchedule.objects.filter(schedule_type='flexible').count(),
            'shift': WorkSchedule.objects.filter(schedule_type='shift').count(),
        }
    }

    # Estadísticas de Asignaciones de Horarios
    employee_schedules_stats = {
        'total': EmployeeSchedule.objects.count(),
        'active': EmployeeSchedule.objects.filter(is_active=True).count(),
        'inactive': EmployeeSchedule.objects.filter(is_active=False).count(),
    }

    # Estadísticas de Feriados
    holidays_stats = {
        'total': Holiday.objects.count(),
        'active': Holiday.objects.filter(is_active=True).count(),
        'inactive': Holiday.objects.filter(is_active=False).count(),
        'current_year': Holiday.objects.filter(date__year=current_year).count(),
        'upcoming': Holiday.objects.filter(
            is_active=True,
            date__gte=today,
            date__lte=future_90_days
        ).count(),
        'recurring': Holiday.objects.filter(is_recurring=True).count(),
        'paid': Holiday.objects.filter(is_paid=True).count(),
    }

    # Estadísticas de Reglas de Asistencia
    attendance_rules_stats = {
        'total': AttendanceRule.objects.count(),
        'active': AttendanceRule.objects.filter(is_active=True).count(),
        'inactive': AttendanceRule.objects.filter(is_active=False).count(),
        'with_justification': AttendanceRule.objects.filter(require_justification=True).count(),
        'without_justification': AttendanceRule.objects.filter(require_justification=False).count(),
    }

    # ============ ESTADÍSTICAS DETALLADAS ============

    # Departamentos con más detalles (Top 5 activos)
    departments_detail = Department.objects.select_related('manager').annotate(
        employees_count=Count('employees', distinct=True),
        positions_count=Count('positions', distinct=True)
    ).filter(is_active=True)[:5]

    # Horarios más utilizados (Top 5)
    popular_schedules = WorkSchedule.objects.annotate(
        employees_count=Count('employee_assignments', distinct=True)
    ).filter(is_active=True).order_by('-employees_count')[:5]

    # Próximos feriados (próximos 5)
    upcoming_holidays = Holiday.objects.filter(
        is_active=True,
        date__gte=today
    ).order_by('date')[:5]

    # Empleados sin asignación de horario activa
    employees_without_schedule = Employee.objects.filter(
        status='active'
    ).exclude(
        Q(schedules__is_active=True,
          schedules__start_date__lte=today,
          schedules__end_date__gte=today) |
        Q(schedules__is_active=True,
          schedules__start_date__lte=today,
          schedules__end_date__isnull=True)
    ).count()

    # Asignaciones que expiran pronto (próximos 30 días)
    expiring_assignments = EmployeeSchedule.objects.filter(
        is_active=True,
        end_date__gte=today,
        end_date__lte=future_30_days
    ).select_related('employee__user', 'schedule').count()

    # ============ RESUMEN GENERAL DE ASISTENCIA ============
    
    attendance_summary = {
        'total_schedules': schedules_stats['total'],
        'active_assignments': employee_schedules_stats['active'],
        'upcoming_holidays': holidays_stats['upcoming'],
        'active_rules': attendance_rules_stats['active'],
        'employees_without_schedule': employees_without_schedule,
        'expiring_assignments': expiring_assignments,
    }

    context = {
        'user': request.user,
        
        # Estadísticas de empresas (NUEVO)
        'companies_stats': companies_stats,
        'active_company': active_company,
        
        # Estadísticas existentes
        'departments_stats': departments_stats,
        'employees_stats': employees_stats,
        'positions_stats': positions_stats,
        'leaves_stats': leaves_stats,
        'departments_detail': departments_detail,
        
        # Estadísticas de asistencia
        'schedules_stats': schedules_stats,
        'employee_schedules_stats': employee_schedules_stats,
        'holidays_stats': holidays_stats,
        'attendance_rules_stats': attendance_rules_stats,
        'attendance_summary': attendance_summary,
        
        # Detalles adicionales
        'popular_schedules': popular_schedules,
        'upcoming_holidays': upcoming_holidays,
        'employees_without_schedule': employees_without_schedule,
        'expiring_assignments': expiring_assignments,
    }

    return render(request, 'components/parameters/parameters.html', context)