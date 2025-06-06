# Generated by Django 5.2.1 on 2025-05-31 04:52

import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Nombre del Departamento')),
                ('description', models.TextField(blank=True, verbose_name='Descripción')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('manager', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='managed_departments', to=settings.AUTH_USER_MODEL, verbose_name='Jefe de Departamento')),
            ],
            options={
                'verbose_name': 'Departamento',
                'verbose_name_plural': 'Departamentos',
                'db_table': 'employees_department',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Employee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('national_id', models.CharField(max_length=20, unique=True, verbose_name='Cédula/DNI')),
                ('gender', models.CharField(choices=[('M', 'Masculino'), ('F', 'Femenino'), ('O', 'Otro')], max_length=1, verbose_name='Género')),
                ('birth_date', models.DateField(verbose_name='Fecha de Nacimiento')),
                ('marital_status', models.CharField(choices=[('single', 'Soltero'), ('married', 'Casado'), ('divorced', 'Divorciado'), ('widowed', 'Viudo')], default='single', max_length=10, verbose_name='Estado Civil')),
                ('address', models.TextField(verbose_name='Dirección')),
                ('employee_number', models.CharField(max_length=20, unique=True, verbose_name='Número de Empleado')),
                ('hire_date', models.DateField(verbose_name='Fecha de Contratación')),
                ('contract_type', models.CharField(choices=[('permanent', 'Permanente'), ('temporary', 'Temporal'), ('contract', 'Por Contrato'), ('internship', 'Pasantía')], default='permanent', max_length=15, verbose_name='Tipo de Contrato')),
                ('salary', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Salario Actual')),
                ('status', models.CharField(choices=[('active', 'Activo'), ('inactive', 'Inactivo'), ('suspended', 'Suspendido'), ('terminated', 'Terminado')], default='active', max_length=15, verbose_name='Estado')),
                ('termination_date', models.DateField(blank=True, null=True, verbose_name='Fecha de Terminación')),
                ('emergency_contact_name', models.CharField(max_length=100, verbose_name='Contacto de Emergencia')),
                ('emergency_contact_phone', models.CharField(max_length=17, verbose_name='Teléfono de Emergencia')),
                ('emergency_contact_relationship', models.CharField(max_length=50, verbose_name='Parentesco')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='employees', to='employees.department', verbose_name='Departamento')),
                ('supervisor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subordinates', to='employees.employee', verbose_name='Supervisor')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='employee_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Empleado',
                'verbose_name_plural': 'Empleados',
                'db_table': 'employees_employee',
                'ordering': ['employee_number'],
            },
        ),
        migrations.CreateModel(
            name='EmployeeDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(choices=[('contract', 'Contrato'), ('id_copy', 'Copia de Cédula'), ('resume', 'Currículum'), ('certificate', 'Certificado'), ('photo', 'Fotografía'), ('other', 'Otro')], max_length=15, verbose_name='Tipo de Documento')),
                ('name', models.CharField(max_length=100, verbose_name='Nombre del Documento')),
                ('file', models.FileField(upload_to='employee_documents/', verbose_name='Archivo')),
                ('upload_date', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Subida')),
                ('notes', models.TextField(blank=True, verbose_name='Notas')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='employees.employee', verbose_name='Empleado')),
            ],
            options={
                'verbose_name': 'Documento de Empleado',
                'verbose_name_plural': 'Documentos de Empleados',
                'db_table': 'employees_document',
                'ordering': ['-upload_date'],
            },
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100, verbose_name='Título del Cargo')),
                ('description', models.TextField(blank=True, verbose_name='Descripción del Cargo')),
                ('base_salary', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='Salario Base')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='positions', to='employees.department', verbose_name='Departamento')),
            ],
            options={
                'verbose_name': 'Cargo',
                'verbose_name_plural': 'Cargos',
                'db_table': 'employees_position',
                'ordering': ['department', 'title'],
                'unique_together': {('title', 'department')},
            },
        ),
        migrations.AddField(
            model_name='employee',
            name='position',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='employees', to='employees.position', verbose_name='Cargo'),
        ),
    ]
