# core/employees/context_processors.py
from django.db.models import Count
from .models import Department, Employee, Position

def dashboard_stats(request):
    """
    Context processor que proporciona estadísticas básicas
    para usar en cualquier template
    """
    # Solo cargar las estadísticas si el usuario está autenticado
    if not request.user.is_authenticated:
        return {}
    
    try:
        return {
            'dashboard_stats': {
                'departments': {
                    'total': Department.objects.count(),
                    'active': Department.objects.filter(is_active=True).count(),
                    'inactive': Department.objects.filter(is_active=False).count(),
                },
                'employees': {
                    'total': Employee.objects.count(),
                    'active': Employee.objects.filter(is_active=True).count(),
                    'inactive': Employee.objects.filter(is_active=False).count(),
                },
                'positions': {
                    'total': Position.objects.count(),
                    'active': Position.objects.filter(is_active=True).count(),
                    'inactive': Position.objects.filter(is_active=False).count(),
                }
            }
        }
    except Exception:
        # En caso de error (ej: base de datos no inicializada)
        return {
            'dashboard_stats': {
                'departments': {'total': 0, 'active': 0, 'inactive': 0},
                'employees': {'total': 0, 'active': 0, 'inactive': 0},
                'positions': {'total': 0, 'active': 0, 'inactive': 0}
            }
        }