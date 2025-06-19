# core/users/views/dashboard.py (actualizar la función home_redirect)

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta

try:
    from core.employees.models import Employee, Department
except ImportError:
    Employee = None
    Department = None

def home_redirect(request):
    """
    Redirige según el estado de autenticación y tipo de usuario
    """
    if not request.user.is_authenticated:
        return redirect('users:login')
    
    user = request.user
    
    # Verificar si necesita cambiar contraseña temporal
    if getattr(user, 'needs_password_change', False):
        return redirect('employees:employee_change_password')
    
    # Redirección basada en el tipo de usuario
    if hasattr(user, 'employee_profile'):
        # Es un empleado regular
        return redirect('employees:employee_dashboard')
    
    elif (user.is_superuser or user.is_staff or 
          getattr(user, 'user_type', '') in ['admin', 'hr', 'supervisor']):
        # Es administrador/staff
        return redirect('users:dashboard')
    
    else:
        # Usuario sin perfil específico
        return redirect('users:login')


@login_required
def dashboard_view(request):
    """
    Vista principal del dashboard ADMINISTRATIVO con estadísticas y datos resumidos
    """
    # Verificar que el usuario tenga permisos administrativos
    if (not request.user.is_superuser and not request.user.is_staff and 
        getattr(request.user, 'user_type', '') not in ['admin', 'hr', 'supervisor']):
        # Si es un empleado regular, redirigir a su dashboard
        if hasattr(request.user, 'employee_profile'):
            return redirect('employees:employee_dashboard')
        else:
            return redirect('users:login')
    
    context = {
        'user': request.user,
    }
    
    # Solo agregar estadísticas si los modelos están disponibles
    if Employee:
        try:
            # Estadísticas generales
            total_employees = Employee.objects.count()
            active_employees = Employee.objects.filter(status='active').count()
            
            # Calcular porcentaje de empleados activos
            if total_employees > 0:
                active_percentage = round((active_employees / total_employees) * 100, 1)
            else:
                active_percentage = 0
            
            # Empleados recientes (últimos 30 días)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            recent_employees = Employee.objects.filter(
                hire_date__gte=thirty_days_ago
            ).select_related('user', 'department', 'position').order_by('-hire_date')[:5]
            
            # Nómina del mes (simulada - ajustar según tu modelo de nómina)
            monthly_payroll = Employee.objects.filter(
                status='active'
            ).aggregate(total=Sum('salary'))['total'] or 0
            
            # Solicitudes pendientes (simulado - implementar según tus modelos)
            pending_requests = 8  # Placeholder
            
            # Empleados por departamento
            employees_by_department = Employee.objects.values(
                'department__name'
            ).annotate(
                count=Count('id')
            ).order_by('-count')
            
            context.update({
                'total_employees': total_employees,
                'active_employees': active_employees,
                'active_percentage': active_percentage,
                'recent_employees': recent_employees,
                'monthly_payroll': monthly_payroll,
                'pending_requests': pending_requests,
                'employees_by_department': employees_by_department,
            })
            
        except Exception as e:
            # En caso de error, usar valores por defecto
            print(f"Error al cargar estadísticas: {e}")
            context.update({
                'total_employees': 0,
                'active_employees': 0,
                'active_percentage': 0,
                'recent_employees': [],
                'monthly_payroll': 0,
                'pending_requests': 0,
                'employees_by_department': [],
            })
    else:
        # Valores por defecto cuando los modelos no están disponibles
        context.update({
            'total_employees': 0,
            'active_employees': 0,
            'active_percentage': 0,
            'recent_employees': [],
            'monthly_payroll': 0,
            'pending_requests': 0,
            'employees_by_department': [],
        })
    
    return render(request, 'pages/admin/dashboard.html', context)


@login_required
def profile_view(request):
    """
    Vista del perfil del usuario (administrativa)
    """
    # Si es empleado, redirigir a su perfil específico
    if hasattr(request.user, 'employee_profile'):
        return redirect('employees:employee_profile')
    
    return render(request, 'profile.html', {'user': request.user})