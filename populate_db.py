#!/usr/bin/env python
"""
Script para poblar la base de datos con datos de ejemplo
Ejecutar desde la raíz del proyecto Django: python populate_db.py
"""

import os
import django
from django.conf import settings
from decimal import Decimal
from datetime import datetime, date, time, timedelta
import random

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.users.models import Company, UserProfile
from core.employees.models import Department, Position, Employee, EmployeeDocument
from core.attendance.models import WorkSchedule, EmployeeSchedule, Holiday, AttendanceRule, Attendance
from core.leaves.models import LeaveType, LeaveRequest, LeaveBalance
from core.payroll.models import TipoRubro, Rubro, PayrollPeriod, Payroll, PayrollRubro, AdelantoQuincena
from core.tasks.models import TaskCategory, Task, TaskAssignment
from core.notifications.models import NotificationType, Notification, NotificationPreference

User = get_user_model()

def clear_data():
    """Limpiar datos existentes (opcional)"""
    print("Limpiando datos existentes...")
    
    # Orden importante para evitar errores de foreign key
    NotificationPreference.objects.all().delete()
    Notification.objects.all().delete()
    NotificationType.objects.all().delete()
    
    TaskAssignment.objects.all().delete()
    Task.objects.all().delete()
    TaskCategory.objects.all().delete()
    
    PayrollRubro.objects.all().delete()
    AdelantoQuincena.objects.all().delete()
    Payroll.objects.all().delete()
    PayrollPeriod.objects.all().delete()
    Rubro.objects.all().delete()
    TipoRubro.objects.all().delete()
    
    LeaveBalance.objects.all().delete()
    LeaveRequest.objects.all().delete()
    LeaveType.objects.all().delete()
    
    Attendance.objects.all().delete()
    EmployeeSchedule.objects.all().delete()
    Holiday.objects.all().delete()
    AttendanceRule.objects.all().delete()
    WorkSchedule.objects.all().delete()
    
    EmployeeDocument.objects.all().delete()
    Employee.objects.all().delete()
    Position.objects.all().delete()
    Department.objects.all().delete()
    
    UserProfile.objects.all().delete()
    User.objects.filter(is_superuser=False).delete()
    Company.objects.all().delete()
    
    print("✓ Datos limpiados")

def create_company():
    """Crear empresa principal"""
    print("Creando empresa...")
    
    company = Company.objects.create(
        name="AgroTech Solutions S.A.",
        ruc="1234567890001",
        address="Av. Principal 123, Sector Industrial",
        city="Milagro",
        province="Guayas",
        phone="042123456",
        email="info@agrotech.com.ec",
        website="https://www.agrotech.com.ec",
        is_active=True
    )
    
    print(f"✓ Empresa creada: {company.name}")
    return company

def create_users_and_employees():
    """Crear usuarios y empleados"""
    print("Creando usuarios y empleados...")
    
    # Datos de empleados de ejemplo
    employees_data = [
        {
            'username': 'admin',
            'password': 'admin123',
            'first_name': 'Carlos',
            'last_name': 'Administrador',
            'email': 'admin@agrotech.com',
            'user_type': 'admin',
            'employee_id': 'EMP001',
            'phone_number': '0998765432',
            'national_id': '0123456789',
            'gender': 'M',
            'birth_date': date(1985, 3, 15),
            'address': 'Av. Central 456, Milagro',
            'salary': Decimal('2500.00'),
            'hire_date': date(2020, 1, 15),
            'emergency_contact_name': 'María Administrador',
            'emergency_contact_phone': '0987654321',
            'emergency_contact_relationship': 'Esposa'
        },
        {
            'username': 'supervisor1',
            'password': 'super123',
            'first_name': 'Ana',
            'last_name': 'Supervisora',
            'email': 'ana.supervisora@agrotech.com',
            'user_type': 'supervisor',
            'employee_id': 'EMP002',
            'phone_number': '0987654321',
            'national_id': '0987654321',
            'gender': 'F',
            'birth_date': date(1988, 7, 22),
            'address': 'Calle Los Rosales 789, Milagro',
            'salary': Decimal('1800.00'),
            'hire_date': date(2021, 3, 10),
            'emergency_contact_name': 'Pedro Supervisora',
            'emergency_contact_phone': '0912345678',
            'emergency_contact_relationship': 'Esposo'
        },
        {
            'username': 'jperez',
            'password': 'juan123',
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'email': 'juan.perez@agrotech.com',
            'user_type': 'employee',
            'employee_id': 'EMP003',
            'phone_number': '0912345678',
            'national_id': '1234567890',
            'gender': 'M',
            'birth_date': date(1992, 11, 5),
            'address': 'Barrio La Esperanza, Mz. 5 Solar 10',
            'salary': Decimal('450.00'),
            'hire_date': date(2022, 6, 1),
            'emergency_contact_name': 'Carmen Pérez',
            'emergency_contact_phone': '0923456789',
            'emergency_contact_relationship': 'Madre'
        },
        {
            'username': 'mrodriguez',
            'password': 'maria123',
            'first_name': 'María',
            'last_name': 'Rodríguez',
            'email': 'maria.rodriguez@agrotech.com',
            'user_type': 'employee',
            'employee_id': 'EMP004',
            'phone_number': '0923456789',
            'national_id': '2345678901',
            'gender': 'F',
            'birth_date': date(1990, 4, 18),
            'address': 'Cdla. Los Jardines, Casa 25',
            'salary': Decimal('480.00'),
            'hire_date': date(2022, 8, 15),
            'emergency_contact_name': 'Luis Rodríguez',
            'emergency_contact_phone': '0934567890',
            'emergency_contact_relationship': 'Hermano'
        },
        {
            'username': 'cgonzalez',
            'password': 'carlos123',
            'first_name': 'Carlos',
            'last_name': 'González',
            'email': 'carlos.gonzalez@agrotech.com',
            'user_type': 'employee',
            'employee_id': 'EMP005',
            'phone_number': '0934567890',
            'national_id': '3456789012',
            'gender': 'M',
            'birth_date': date(1987, 9, 12),
            'address': 'Sector Rural, Km 8 Vía a Yaguachi',
            'salary': Decimal('520.00'),
            'hire_date': date(2021, 11, 20),
            'emergency_contact_name': 'Elena González',
            'emergency_contact_phone': '0945678901',
            'emergency_contact_relationship': 'Esposa'
        },
        {
            'username': 'llopez',
            'password': 'lucia123',
            'first_name': 'Lucía',
            'last_name': 'López',
            'email': 'lucia.lopez@agrotech.com',
            'user_type': 'employee',
            'employee_id': 'EMP006',
            'phone_number': '0945678901',
            'national_id': '4567890123',
            'gender': 'F',
            'birth_date': date(1995, 1, 30),
            'address': 'Cooperativa 15 de Mayo, Mz. 12',
            'salary': Decimal('465.00'),
            'hire_date': date(2023, 2, 5),
            'emergency_contact_name': 'Roberto López',
            'emergency_contact_phone': '0956789012',
            'emergency_contact_relationship': 'Padre'
        }
    ]
    
    # Crear departamentos primero
    departments = {}
    dept_data = [
        ('Administración', 'Departamento administrativo y de recursos humanos'),
        ('Producción', 'Departamento de producción agrícola'),
        ('Mantenimiento', 'Mantenimiento de equipos e infraestructura'),
        ('Supervisión', 'Supervisión de campo y control de calidad')
    ]
    
    for name, desc in dept_data:
        dept, created = Department.objects.get_or_create(
            name=name,
            defaults={
                'description': desc,
                'is_active': True
            }
        )
        departments[name] = dept
        if created:
            print(f"  ✓ Departamento creado: {name}")
        else:
            print(f"  • Departamento existe: {name}")
    
    # Crear posiciones
    positions = {}
    pos_data = [
        ('Administrador General', 'Administración', 'Responsable de la administración general', Decimal('2500.00')),
        ('Supervisor de Campo', 'Supervisión', 'Supervisión de actividades de campo', Decimal('1800.00')),
        ('Trabajador Agrícola', 'Producción', 'Labores de campo y producción', Decimal('450.00')),
        ('Técnico de Mantenimiento', 'Mantenimiento', 'Mantenimiento de equipos y sistemas', Decimal('600.00'))
    ]
    
    for title, dept_name, desc, salary in pos_data:
        pos, created = Position.objects.get_or_create(
            title=title,
            department=departments[dept_name],
            defaults={
                'description': desc,
                'base_salary': salary,
                'is_active': True
            }
        )
        positions[title] = pos
        if created:
            print(f"  ✓ Posición creada: {title}")
        else:
            print(f"  • Posición existe: {title}")
    
    created_users = []
    
    for emp_data in employees_data:
        # Verificar si el usuario ya existe
        user, user_created = User.objects.get_or_create(
            username=emp_data['username'],
            defaults={
                'first_name': emp_data['first_name'],
                'last_name': emp_data['last_name'],
                'email': emp_data['email'],
                'user_type': emp_data['user_type'],
                'employee_id': emp_data['employee_id'],
                'phone_number': emp_data['phone_number'],
                'is_active_employee': True
            }
        )
        
        if user_created:
            user.set_password(emp_data['password'])
            user.save()
            print(f"  ✓ Usuario creado: {emp_data['username']}")
        else:
            print(f"  • Usuario existe: {emp_data['username']}")
        
        # Crear o actualizar perfil de usuario
        profile, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'birth_date': emp_data['birth_date'],
                'address': emp_data['address'],
                'emergency_contact_name': emp_data['emergency_contact_name'],
                'emergency_contact_phone': emp_data['emergency_contact_phone']
            }
        )
        
        if profile_created:
            print(f"    ✓ Perfil creado para: {emp_data['username']}")
        else:
            print(f"    • Perfil existe para: {emp_data['username']}")
        
        # Asignar departamento y posición según el tipo de usuario
        if emp_data['user_type'] == 'admin':
            dept = departments['Administración']
            pos = positions['Administrador General']
        elif emp_data['user_type'] == 'supervisor':
            dept = departments['Supervisión']
            pos = positions['Supervisor de Campo']
        else:
            dept = departments['Producción']
            pos = positions['Trabajador Agrícola']
        
        # Crear o actualizar empleado
        employee, emp_created = Employee.objects.get_or_create(
            user=user,
            defaults={
                'national_id': emp_data['national_id'],
                'gender': emp_data['gender'],
                'birth_date': emp_data['birth_date'],
                'address': emp_data['address'],
                'employee_number': emp_data['employee_id'],
                'department': dept,
                'position': pos,
                'hire_date': emp_data['hire_date'],
                'salary': emp_data['salary'],
                'status': 'active',
                'emergency_contact_name': emp_data['emergency_contact_name'],
                'emergency_contact_phone': emp_data['emergency_contact_phone'],
                'emergency_contact_relationship': emp_data['emergency_contact_relationship']
            }
        )
        
        if emp_created:
            print(f"    ✓ Empleado creado: {emp_data['employee_id']}")
        else:
            print(f"    • Empleado existe: {emp_data['employee_id']}")
        
        created_users.append({
            'username': emp_data['username'],
            'password': emp_data['password'],
            'name': f"{emp_data['first_name']} {emp_data['last_name']}",
            'type': emp_data['user_type'],
            'employee': employee
        })
    
    return created_users, departments, positions

def create_work_schedules():
    """Crear horarios de trabajo"""
    print("Creando horarios de trabajo...")
    
    schedules = []
    
    # Horario administrativo
    admin_schedule = WorkSchedule.objects.create(
        name='Horario Administrativo',
        schedule_type='fixed',
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_duration=timedelta(hours=1),
        weekly_hours=Decimal('40.00'),
        late_tolerance=15,
        monday=True,
        tuesday=True,
        wednesday=True,
        thursday=True,
        friday=True,
        saturday=False,
        sunday=False,
        is_active=True
    )
    schedules.append(admin_schedule)
    
    # Horario de campo
    field_schedule = WorkSchedule.objects.create(
        name='Horario de Campo',
        schedule_type='fixed',
        start_time=time(6, 0),
        end_time=time(14, 0),
        break_duration=timedelta(minutes=30),
        weekly_hours=Decimal('40.00'),
        late_tolerance=10,
        monday=True,
        tuesday=True,
        wednesday=True,
        thursday=True,
        friday=True,
        saturday=True,
        sunday=False,
        is_active=True
    )
    schedules.append(field_schedule)
    
    print(f"✓ {len(schedules)} horarios creados")
    return schedules

def create_holidays():
    """Crear días feriados"""
    print("Creando días feriados...")
    
    current_year = datetime.now().year
    holidays = []
    
    holidays_data = [
        ('Año Nuevo', 1, 1, True),
        ('Día del Trabajo', 5, 1, True),
        ('Independencia de Ecuador', 8, 10, True),
        ('Independencia de Guayaquil', 10, 9, True),
        ('Día de los Difuntos', 11, 2, True),
        ('Independencia de Cuenca', 11, 3, True),
        ('Navidad', 12, 25, True),
    ]
    
    for name, month, day, is_recurring in holidays_data:
        holiday = Holiday.objects.create(
            name=name,
            date=date(current_year, month, day),
            is_recurring=is_recurring,
            is_paid=True,
            description=f'Feriado nacional: {name}',
            is_active=True
        )
        holidays.append(holiday)
    
    print(f"✓ {len(holidays)} feriados creados")
    return holidays

def create_leave_types():
    """Crear tipos de licencias"""
    print("Creando tipos de licencias...")
    
    leave_types = []
    
    leave_data = [
        ('Vacaciones Anuales', 'VAC', 15, True, True, True, '#007bff'),
        ('Licencia por Enfermedad', 'ENF', 5, True, True, False, '#dc3545'),
        ('Licencia de Maternidad', 'MAT', 84, True, True, False, '#e83e8c'),
        ('Licencia de Paternidad', 'PAT', 10, True, True, False, '#6f42c1'),
        ('Permiso Personal', 'PER', 3, True, False, False, '#fd7e14'),
        ('Calamidad Doméstica', 'CAL', 3, True, True, False, '#6c757d'),
    ]
    
    for name, code, days, approval, paid, carry, color in leave_data:
        leave_type = LeaveType.objects.create(
            name=name,
            code=code,
            days_allowed=days,
            requires_approval=approval,
            is_paid=paid,
            carry_forward=carry,
            color=color,
            description=f'Licencia de tipo {name}',
            is_active=True
        )
        leave_types.append(leave_type)
    
    print(f"✓ {len(leave_types)} tipos de licencias creados")
    return leave_types

def create_payroll_rubros():
    """Crear tipos de rubros y rubros para nómina"""
    print("Creando rubros de nómina...")
    
    # Crear tipos de rubros
    tipo_ingreso = TipoRubro.objects.create(
        nombre='Ingresos',
        tipo='ingreso',
        descripcion='Rubros que incrementan el salario',
        is_active=True
    )
    
    tipo_egreso = TipoRubro.objects.create(
        nombre='Deducciones',
        tipo='egreso',
        descripcion='Rubros que se descuentan del salario',
        is_active=True
    )
    
    # Rubros de ingreso
    ingresos_data = [
        ('HOE', 'Horas Extras', 'horas', None, Decimal('2.50'), True, True),
        ('BON', 'Bonificación', 'fijo', None, Decimal('50.00'), False, False),
        ('COM', 'Comisiones', 'fijo', None, None, False, False),
        ('MOV', 'Movilización', 'fijo', None, Decimal('30.00'), False, False),
    ]
    
    rubros_ingreso = []
    for codigo, nombre, tipo_calc, porcentaje, monto, obligatorio, automatico in ingresos_data:
        rubro = Rubro.objects.create(
            tipo_rubro=tipo_ingreso,
            codigo=codigo,
            nombre=nombre,
            tipo_calculo=tipo_calc,
            porcentaje_default=porcentaje,
            monto_default=monto,
            es_obligatorio=obligatorio,
            aplicar_automaticamente=automatico,
            is_active=True
        )
        rubros_ingreso.append(rubro)
    
    # Rubros de egreso
    egresos_data = [
        ('IESS', 'Aporte IESS Personal', 'porcentaje', Decimal('9.45'), None, True, True),
        ('IMP', 'Impuesto a la Renta', 'porcentaje', Decimal('5.00'), None, False, False),
        ('PRE', 'Préstamo', 'fijo', None, None, False, False),
        ('MUL', 'Multas', 'fijo', None, None, False, False),
        ('ADQ', 'Adelanto Quincenal', 'fijo', None, None, False, False),
    ]
    
    rubros_egreso = []
    for codigo, nombre, tipo_calc, porcentaje, monto, obligatorio, automatico in egresos_data:
        rubro = Rubro.objects.create(
            tipo_rubro=tipo_egreso,
            codigo=codigo,
            nombre=nombre,
            tipo_calculo=tipo_calc,
            porcentaje_default=porcentaje,
            monto_default=monto,
            es_obligatorio=obligatorio,
            aplicar_automaticamente=automatico,
            is_active=True
        )
        rubros_egreso.append(rubro)
    
    print(f"✓ {len(rubros_ingreso + rubros_egreso)} rubros creados")
    return rubros_ingreso, rubros_egreso

def create_task_categories():
    """Crear categorías de tareas"""
    print("Creando categorías de tareas...")
    
    categories_data = [
        ('Siembra', 'Actividades relacionadas con la siembra', 'fas fa-seedling', '#10B981'),
        ('Riego', 'Sistema de riego y mantenimiento', 'fas fa-tint', '#3B82F6'),
        ('Fertilización', 'Aplicación de fertilizantes', 'fas fa-flask', '#F59E0B'),
        ('Control de Plagas', 'Control fitosanitario', 'fas fa-bug', '#EF4444'),
        ('Cosecha', 'Actividades de recolección', 'fas fa-apple-alt', '#8B5CF6'),
        ('Mantenimiento', 'Mantenimiento general', 'fas fa-tools', '#6B7280'),
        ('Limpieza', 'Limpieza de áreas', 'fas fa-broom', '#06B6D4'),
    ]
    
    categories = []
    for name, desc, icon, color in categories_data:
        category = TaskCategory.objects.create(
            name=name,
            description=desc,
            icon=icon,
            color=color,
            is_active=True
        )
        categories.append(category)
    
    print(f"✓ {len(categories)} categorías de tareas creadas")
    return categories

def create_notification_types():
    """Crear tipos de notificaciones"""
    print("Creando tipos de notificaciones...")
    
    notification_types = []
    
    types_data = [
        ('Nueva Tarea Asignada', 'TASK_ASSIGNED', 'Nueva tarea: {task_title}', 
         'Se te ha asignado una nueva tarea: {task_title}', True, True, True, 'fa-tasks', 'info'),
        ('Solicitud de Licencia', 'LEAVE_REQUEST', 'Solicitud de licencia pendiente', 
         'Tienes una solicitud de licencia pendiente de aprobación', True, True, True, 'fa-calendar-times', 'warning'),
        ('Nómina Generada', 'PAYROLL_GENERATED', 'Tu nómina está lista', 
         'Tu recibo de pago del período {period} está disponible', True, True, True, 'fa-money-bill', 'success'),
        ('Adelanto Aprobado', 'ADVANCE_APPROVED', 'Adelanto aprobado', 
         'Tu solicitud de adelanto por ${amount} ha sido aprobada', True, True, True, 'fa-hand-holding-usd', 'success'),
        ('Recordatorio de Asistencia', 'ATTENDANCE_REMINDER', 'Recordatorio de marcación', 
         'No olvides marcar tu asistencia', True, True, True, 'fa-clock', 'info'),
    ]
    
    for name, code, subject, body, email, system, auto, icon, color in types_data:
        nt = NotificationType.objects.create(
            name=name,
            code=code,
            template_subject=subject,
            template_body=body,
            is_email=email,
            is_system=system,
            auto_send=auto,
            icon=icon,
            color=color,
            is_active=True
        )
        notification_types.append(nt)
    
    print(f"✓ {len(notification_types)} tipos de notificaciones creados")
    return notification_types

def create_sample_data(users, schedules, leave_types, categories):
    """Crear datos de ejemplo (asistencia, tareas, etc.)"""
    print("Creando datos de ejemplo...")
    
    # Asignar horarios a empleados
    admin_user = next(u for u in users if u['type'] == 'admin')
    supervisor_user = next(u for u in users if u['type'] == 'supervisor')
    employee_users = [u for u in users if u['type'] == 'employee']
    
    admin_schedule = schedules[0]  # Horario administrativo
    field_schedule = schedules[1]   # Horario de campo
    
    # Asignar horario administrativo al admin y supervisor
    for user_data in [admin_user, supervisor_user]:
        EmployeeSchedule.objects.create(
            employee=user_data['employee'],
            schedule=admin_schedule,
            start_date=date(2024, 1, 1),
            is_active=True,
            notes='Horario asignado automáticamente'
        )
    
    # Asignar horario de campo a empleados
    for user_data in employee_users:
        EmployeeSchedule.objects.create(
            employee=user_data['employee'],
            schedule=field_schedule,
            start_date=date(2024, 1, 1),
            is_active=True,
            notes='Horario de campo'
        )
    
    # Crear algunas tareas de ejemplo
    today = datetime.now()
    
    for i, category in enumerate(categories[:3]):  # Solo 3 categorías para el ejemplo
        task = Task.objects.create(
            title=f'Tarea de {category.name} - Semana {i+1}',
            description=f'Realizar actividades de {category.name.lower()} en el sector asignado.',
            category=category,
            supervisor=supervisor_user['employee'],
            start_date=today + timedelta(days=i),
            end_date=today + timedelta(days=i+2),
            estimated_hours=Decimal('16.00'),
            location=f'Sector {i+1}',
            payment_type='hourly',
            hourly_rate=Decimal('3.50'),
            priority='medium',
            status='assigned' if i == 0 else 'draft',
            special_instructions=f'Usar equipo de protección para {category.name.lower()}'
        )
        
        # Asignar empleados a la primera tarea
        if i == 0:
            for user_data in employee_users[:2]:
                TaskAssignment.objects.create(
                    task=task,
                    employee=user_data['employee'],
                    status='accepted'
                )
    
    # Crear balances de licencias para todos los empleados
    current_year = datetime.now().year
    for user_data in users:
        if user_data['type'] == 'employee':
            for leave_type in leave_types:
                LeaveBalance.objects.create(
                    employee=user_data['employee'],
                    leave_type=leave_type,
                    year=current_year,
                    allocated_days=leave_type.days_allowed,
                    used_days=0,
                    remaining_days=leave_type.days_allowed,
                    carried_forward=0
                )
    
    # Crear preferencias de notificación para todos los usuarios
    for user_data in users:
        NotificationPreference.objects.create(
            user=user_data['employee'].user,
            receive_leave_notifications=True,
            receive_payroll_notifications=True,
            receive_adelanto_notifications=True,
            email_enabled=True,
            system_enabled=True
        )
    
    print("✓ Datos de ejemplo creados")

def print_user_credentials(users):
    """Imprimir credenciales de acceso"""
    print("\n" + "="*60)
    print("CREDENCIALES DE ACCESO")
    print("="*60)
    print(f"{'Usuario':<15} {'Contraseña':<12} {'Nombre':<20} {'Tipo':<12}")
    print("-"*60)
    
    for user in users:
        print(f"{user['username']:<15} {user['password']:<12} {user['name']:<20} {user['type']:<12}")
    
    print("-"*60)
    print("NOTAS:")
    print("- admin: Acceso completo al sistema")
    print("- supervisor1: Puede supervisar tareas y aprobar solicitudes")
    print("- Empleados: Pueden marcar asistencia y ver sus datos")
    print("="*60)

def main():
    """Función principal"""
    print("Iniciando población de base de datos...")
    print("="*50)
    
    # Limpiar datos existentes 
    print("¿Deseas limpiar datos existentes? (y/N): ", end="")
    try:
        response = input().strip().lower()
        if response in ['y', 'yes', 's', 'si']:
            clear_data()
    except:
        print("No - manteniendo datos existentes")
    
    try:
        # Crear empresa
        company, created = Company.objects.get_or_create(
            ruc="1234567890001",
            defaults={
                'name': "AgroTech Solutions S.A.",
                'address': "Av. Principal 123, Sector Industrial",
                'city': "Milagro",
                'province': "Guayas",
                'phone': "042123456",
                'email': "info@agrotech.com.ec",
                'website': "https://www.agrotech.com.ec",
                'is_active': True
            }
        )
        if created:
            print(f"✓ Empresa creada: {company.name}")
        else:
            print(f"• Empresa existe: {company.name}")
        
        # Crear usuarios y empleados
        users, departments, positions = create_users_and_employees()
        
        # Crear horarios de trabajo
        schedules = create_work_schedules()
        
        # Crear feriados
        holidays = create_holidays()
        
        # Crear tipos de licencias
        leave_types = create_leave_types()
        
        # Crear rubros de nómina
        rubros_ingreso, rubros_egreso = create_payroll_rubros()
        
        # Crear categorías de tareas
        categories = create_task_categories()
        
        # Crear tipos de notificaciones
        notification_types = create_notification_types()
        
        # Crear datos de ejemplo
        create_sample_data(users, schedules, leave_types, categories)
        
        print("\n✓ Base de datos poblada exitosamente!")
        
        # Mostrar credenciales
        print_user_credentials(users)
        
    except Exception as e:
        print(f"\n❌ Error al poblar la base de datos: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()