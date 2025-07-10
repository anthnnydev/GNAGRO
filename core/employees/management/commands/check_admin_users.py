from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.employees.models import Employee

User = get_user_model()

class Command(BaseCommand):
    help = 'Verifica y corrige usuarios administradores'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Corregir automáticamente los problemas encontrados',
        )
        parser.add_argument(
            '--user-email',
            type=str,
            help='Verificar un usuario específico por email',
        )
    
    def handle(self, *args, **options):
        fix_issues = options['fix']
        user_email = options.get('user_email')
        
        if user_email:
            # Verificar usuario específico
            try:
                user = User.objects.get(email=user_email)
                self.check_user(user, fix_issues)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Usuario con email {user_email} no encontrado')
                )
        else:
            # Verificar todos los usuarios staff
            staff_users = User.objects.filter(is_staff=True)
            
            self.stdout.write(f'Verificando {staff_users.count()} usuarios staff...\n')
            
            for user in staff_users:
                self.check_user(user, fix_issues)
    
    def check_user(self, user, fix_issues=False):
        self.stdout.write(f'\n=== USUARIO: {user.email} ===')
        self.stdout.write(f'Nombre: {user.get_full_name()}')
        self.stdout.write(f'is_staff: {user.is_staff}')
        self.stdout.write(f'is_superuser: {user.is_superuser}')
        self.stdout.write(f'user_type: {getattr(user, "user_type", "NO_USER_TYPE")}')
        
        has_employee = hasattr(user, 'employee_profile')
        self.stdout.write(f'Tiene employee_profile: {has_employee}')
        
        issues = []
        
        # Verificar si es staff pero no tiene employee_profile
        if user.is_staff and not has_employee:
            issues.append('Staff sin employee_profile')
            
            if fix_issues:
                self.create_employee_profile(user)
        
        # Verificar si tiene employee_profile pero user_type no coincide con permisos
        elif has_employee:
            employee = user.employee_profile
            self.stdout.write(f'Employee ID: {employee.id}')
            self.stdout.write(f'Employee Number: {employee.employee_number}')
            
            # Si es staff pero user_type es 'employee', sugerir cambio
            if user.is_staff and user.user_type == 'employee':
                issues.append('Staff con user_type="employee" (debería ser admin)')
                
                if fix_issues:
                    old_type = user.user_type
                    user.user_type = 'admin'
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ user_type cambiado de {old_type} a admin')
                    )
        
        if issues:
            self.stdout.write(
                self.style.WARNING('Problemas encontrados:')
            )
            for issue in issues:
                self.stdout.write(f'  - {issue}')
        else:
            self.stdout.write(
                self.style.SUCCESS('✓ Usuario configurado correctamente')
            )
    
    def create_employee_profile(self, user):
        from core.employees.models import Department, Position
        
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
            employee = Employee.objects.create(
                user=user,
                employee_number=str(next_number),
                department=admin_dept,
                position=admin_position,
                hire_date=user.date_joined.date() if user.date_joined else None,
                status='active'
            )
            
            # Asegurar que user_type sea 'admin'
            if user.user_type != 'admin':
                user.user_type = 'admin'
                user.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Employee profile creado (#{employee.employee_number})')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creando employee_profile: {e}')
            )