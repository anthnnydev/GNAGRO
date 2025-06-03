from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta

try:
    from core.employees.models import Employee, Department
except ImportError:
    # En caso de que aún no hayas creado los modelos
    Employee = None
    Department = None

@login_required
def dashboard_view(request):
    """
    Vista principal del dashboard con estadísticas y datos resumidos
    """
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
    Vista del perfil del usuario
    """
    return render(request, 'profile.html', {'user': request.user})


# Vista para redirigir la página principal al dashboard si está autenticado
def home_redirect(request):
    """
    Redirige a dashboard si está autenticado, sino al login
    """
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    else:
        return redirect('users:login')