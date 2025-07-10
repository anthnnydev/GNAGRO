from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from core.employees.models import Employee, Department, Position

User = get_user_model()

@receiver(post_save, sender=User)
def create_employee_profile_for_admin(sender, instance, created, **kwargs):
    """Crear automáticamente employee_profile para usuarios staff"""
    
    # Solo para usuarios recién creados que son staff
    if not created or not instance.is_staff:
        return
    
    # Solo si no tiene employee_profile ya
    if hasattr(instance, 'employee_profile'):
        return
    
    try:
        # Obtener o crear departamento administrativo
        admin_dept, _ = Department.objects.get_or_create(
            name='Administración',
            defaults={
                'description': 'Departamento Administrativo',
                'is_active': True
            }
        )
        
        # Obtener o crear posición de administrador
        admin_position, _ = Position.objects.get_or_create(
            title='Administrador del Sistema',
            defaults={
                'description': 'Administrador del Sistema',
                'is_active': True
            }
        )
        
        # Generar número de empleado único
        last_employee = Employee.objects.order_by('-employee_number').first()
        if last_employee and last_employee.employee_number.isdigit():
            next_number = int(last_employee.employee_number) + 1
        else:
            next_number = 1000
        
        # Crear el employee_profile
        Employee.objects.create(
            user=instance,
            employee_number=str(next_number),
            department=admin_dept,
            position=admin_position,
            hire_date=instance.date_joined.date() if instance.date_joined else None,
            status='active'
        )
        
    except Exception as e:
        # Log del error pero no fallar
        print(f"Error creando employee_profile para admin {instance.email}: {e}")