# core/employees/management/commands/assign_simple_groups.py
"""
Comando para asignar usuarios a los 3 grupos según user_type
python manage.py assign_simple_groups
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Asigna usuarios a grupos según user_type (admin/supervisor/employee)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se haría sin ejecutar cambios',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Asignar solo un usuario específico (username)',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        specific_user = options['user']
        
        # Mapeo simple: user_type → grupo
        role_mapping = {
            'admin': 'Administradores',
            'supervisor': 'Supervisores', 
            'employee': 'Empleados',
        }
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 MODO SIMULACIÓN - No se realizarán cambios\n'))
        
        # Verificar que los grupos existen
        missing_groups = []
        for group_name in role_mapping.values():
            if not Group.objects.filter(name=group_name).exists():
                missing_groups.append(group_name)
        
        if missing_groups:
            self.stdout.write(
                self.style.ERROR(f'❌ Grupos faltantes: {", ".join(missing_groups)}')
            )
            self.stdout.write('🔧 Ejecuta primero: python manage.py setup_simple_groups')
            return
        
        # Filtrar usuarios
        if specific_user:
            users = User.objects.filter(username=specific_user, employee_profile__isnull=False)
            if not users.exists():
                self.stdout.write(
                    self.style.ERROR(f'❌ Usuario "{specific_user}" no encontrado o sin perfil de empleado')
                )
                return
        else:
            users = User.objects.filter(employee_profile__isnull=False)
        
        stats = {
            'processed': 0,
            'assigned': 0,
            'already_assigned': 0,
            'unknown_type': 0
        }
        
        self.stdout.write('👥 PROCESANDO USUARIOS:\n')
        
        for user in users:
            stats['processed'] += 1
            user_type = getattr(user, 'user_type', 'employee')
            target_group_name = role_mapping.get(user_type)
            
            if not target_group_name:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  {user.get_full_name()} - Tipo desconocido: {user_type}')
                )
                stats['unknown_type'] += 1
                continue
            
            try:
                target_group = Group.objects.get(name=target_group_name)
                
                # Verificar si ya está en el grupo
                if user.groups.filter(name=target_group_name).exists():
                    self.stdout.write(
                        f'ℹ️  {user.get_full_name()} ya está en "{target_group_name}"'
                    )
                    stats['already_assigned'] += 1
                else:
                    if not dry_run:
                        # Limpiar grupos anteriores relacionados con roles
                        user.groups.remove(*Group.objects.filter(name__in=role_mapping.values()))
                        # Asignar al grupo correcto
                        user.groups.add(target_group)
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ {user.get_full_name()} ({user_type}) → "{target_group_name}"')
                    )
                    stats['assigned'] += 1
                    
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Grupo "{target_group_name}" no encontrado')
                )
        
        # Resumen final
        self.stdout.write(f'\n📊 RESUMEN:')
        self.stdout.write(f'   👥 Usuarios procesados: {stats["processed"]}')
        self.stdout.write(f'   ✅ Nuevas asignaciones: {stats["assigned"]}')
        self.stdout.write(f'   ℹ️  Ya asignados correctamente: {stats["already_assigned"]}')
        self.stdout.write(f'   ⚠️  Tipos desconocidos: {stats["unknown_type"]}')
        
        if dry_run and stats['assigned'] > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n🚀 Para aplicar {stats["assigned"]} cambios, ejecuta sin --dry-run')
            )
        elif not dry_run and stats['assigned'] > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\n🎉 ¡{stats["assigned"]} usuarios asignados correctamente!')
            )
        
        # Mostrar distribución actual
        self.show_current_distribution()
    
    def show_current_distribution(self):
        """Muestra la distribución actual de usuarios por grupo"""
        self.stdout.write(f'\n📈 DISTRIBUCIÓN ACTUAL:')
        
        for group_name in ['Administradores', 'Supervisores', 'Empleados']:
            try:
                group = Group.objects.get(name=group_name)
                # CORRECCIÓN: Cambiar user_set por user_set.all()
                count = group.user_set.all().count()  # ← CAMBIO AQUÍ
                self.stdout.write(f'   {group_name}: {count} usuarios')
                
                # Mostrar usuarios si son pocos
                if count <= 5:
                    users = group.user_set.all()  # ← Y AQUÍ
                    for user in users:
                        self.stdout.write(f'     - {user.get_full_name()} ({user.username})')
                        
            except Group.DoesNotExist:
                self.stdout.write(f'   {group_name}: ❌ Grupo no existe')