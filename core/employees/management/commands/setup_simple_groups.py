# core/employees/management/commands/setup_simple_groups.py
"""
Comando para configurar solo 3 grupos básicos: Admin, Supervisor, Empleado
python manage.py setup_simple_groups
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Configura 3 grupos básicos: Admin, Supervisor, Empleado'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Elimina y recrea todos los grupos',
        )
    
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Eliminando grupos existentes...')
            Group.objects.filter(name__in=['Administradores', 'Supervisores', 'Empleados']).delete()
        
        # Configuración simplificada - 3 grupos
        groups_config = {
            'Administradores': {
                'description': 'Acceso completo al sistema',
                'user_types': ['admin'],
                'permissions': 'all'  # Todos los permisos
            },
            
            'Supervisores': {
                'description': 'Gestión de equipo, tareas y licencias',
                'user_types': ['supervisor'],
                'permissions': [
                    # ===== EMPLEADOS =====
                    'employees.view_employee',          # Ver empleados de su equipo
                    'employees.change_employee',        # Editar info básica de su equipo
                    
                    # ===== TAREAS =====
                    'tasks.add_task',                   # Crear tareas
                    'tasks.change_task',                # Editar tareas
                    'tasks.delete_task',                # Eliminar tareas
                    'tasks.view_task',                  # Ver tareas
                    'tasks.add_taskassignment',         # Asignar tareas
                    'tasks.change_taskassignment',      # Cambiar asignaciones
                    'tasks.delete_taskassignment',      # Quitar asignaciones
                    'tasks.view_taskassignment',        # Ver asignaciones
                    'tasks.add_taskprogress',           # Registrar progreso
                    'tasks.view_taskprogress',          # Ver progreso
                    'tasks.add_taskcomment',            # Comentar tareas
                    'tasks.view_taskcomment',           # Ver comentarios
                    'tasks.add_taskcategory',           # Crear categorías
                    'tasks.change_taskcategory',        # Editar categorías
                    'tasks.view_taskcategory',          # Ver categorías
                    
                    # ===== LICENCIAS =====
                    'leaves.view_leaverequest',         # Ver solicitudes de licencia
                    'leaves.change_leaverequest',       # APROBAR/RECHAZAR licencias ⭐
                    'leaves.view_leavebalance',         # Ver balances de licencias
                    'leaves.change_leavebalance',       # Ajustar balances si es necesario
                    
                    # ===== ASISTENCIA =====
                    'attendance.view_attendance',       # Ver asistencia del equipo
                    'attendance.change_attendance',     # Corregir asistencia
                    'attendance.view_employeeschedule', # Ver horarios
                    'attendance.change_employeeschedule', # Modificar horarios
                    
                    # ===== NÓMINA (Vista) =====
                    'payroll.view_payroll',             # Ver nómina de su equipo
                ]
            },
            
            'Empleados': {
                'description': 'Acceso básico - solo su información',
                'user_types': ['employee'],
                'permissions': [
                    # ===== SU PERFIL =====
                    'employees.view_employee',          # Solo ver su propio perfil
                    
                    # ===== SUS TAREAS =====
                    'tasks.view_task',                  # Ver sus tareas asignadas
                    'tasks.view_taskassignment',        # Ver sus asignaciones
                    'tasks.change_taskassignment',      # Actualizar progreso de sus tareas
                    'tasks.add_taskprogress',           # Reportar progreso
                    'tasks.view_taskprogress',          # Ver su progreso
                    'tasks.add_taskcomment',            # Comentar en sus tareas
                    'tasks.view_taskcomment',           # Ver comentarios
                    
                    # ===== SUS LICENCIAS =====
                    'leaves.add_leaverequest',          # Solicitar licencias
                    'leaves.view_leaverequest',         # Ver sus solicitudes
                    'leaves.view_leavebalance',         # Ver su balance de días
                    
                    # ===== SU ASISTENCIA =====
                    'attendance.add_attendance',        # Marcar entrada/salida
                    'attendance.view_attendance',       # Ver su asistencia
                    'attendance.view_employeeschedule', # Ver su horario
                    
                    # ===== SU NÓMINA =====
                    'payroll.view_payroll',             # Ver su propia nómina
                ]
            }
        }
        
        self.stdout.write('Configurando grupos simplificados...')
        
        for group_name, config in groups_config.items():
            group, created = Group.objects.get_or_create(name=group_name)
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Grupo creado: {group_name}')
                )
            else:
                self.stdout.write(f'🔄 Actualizando grupo: {group_name}')
            
            # Limpiar permisos existentes
            group.permissions.clear()
            
            # Asignar permisos
            if config['permissions'] == 'all':
                # Administradores: todos los permisos
                all_permissions = Permission.objects.all()
                group.permissions.set(all_permissions)
                self.stdout.write(f'   📋 Asignados TODOS los permisos ({all_permissions.count()})')
            else:
                # Supervisores y Empleados: permisos específicos
                permissions_added = 0
                permissions_not_found = []
                
                for perm_codename in config['permissions']:
                    try:
                        app_label, codename = perm_codename.split('.')
                        permission = Permission.objects.get(
                            codename=codename,
                            content_type__app_label=app_label
                        )
                        group.permissions.add(permission)
                        permissions_added += 1
                    except Permission.DoesNotExist:
                        permissions_not_found.append(perm_codename)
                    except ValueError:
                        self.stdout.write(
                            self.style.ERROR(f'   ❌ Formato incorrecto: {perm_codename}')
                        )
                
                self.stdout.write(f'   📋 Asignados {permissions_added} permisos')
                
                if permissions_not_found:
                    self.stdout.write(
                        self.style.WARNING(f'   ⚠️  Permisos no encontrados: {len(permissions_not_found)}')
                    )
                    for perm in permissions_not_found:
                        self.stdout.write(f'      - {perm}')
        
        self.stdout.write(
            self.style.SUCCESS('\n🎉 ¡Configuración completada!')
        )
        self.print_next_steps()
    
    def print_next_steps(self):
        """Instrucciones para el siguiente paso"""
        guide = """
🚀 SIGUIENTES PASOS:

1. ASIGNAR USUARIOS A GRUPOS:
   python manage.py assign_simple_groups

2. VERIFICAR DESDE DJANGO ADMIN:
   👥 Autenticación y autorización → Grupos
   - Administradores (todos los permisos)
   - Supervisores (gestión de equipo)
   - Empleados (acceso básico)

3. ASIGNAR MANUALMENTE (Alternativa):
   👤 Usuarios → [Seleccionar usuario] → Grupos → Agregar grupo

4. VERIFICAR PERMISOS DE LICENCIAS:
   ✅ Supervisores deben tener: leaves.change_leaverequest
   ✅ Esto resuelve el error de /leaves/requests/3/approve/

📋 ROLES CONFIGURADOS:
   🔴 admin → Administradores
   🟡 supervisor → Supervisores  
   🟢 employee → Empleados
        """
        self.stdout.write(guide)