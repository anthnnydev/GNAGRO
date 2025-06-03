# core/employees/models.py
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from decimal import Decimal

class Department(models.Model):
    """
    Modelo para departamentos de la empresa
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre del Departamento'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments',
        verbose_name='Jefe de Departamento'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        db_table = 'employees_department'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Position(models.Model):
    """
    Modelo para cargos/posiciones en la empresa
    """
    title = models.CharField(
        max_length=100,
        verbose_name='Título del Cargo'
    )
    
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='positions',
        verbose_name='Departamento'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción del Cargo'
    )
    
    base_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Salario Base'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Cargo'
        verbose_name_plural = 'Cargos'
        db_table = 'employees_position'
        ordering = ['department', 'title']
        unique_together = ['title', 'department']
    
    def __str__(self):
        return f"{self.title} - {self.department.name}"


class Employee(models.Model):
    """
    Modelo principal para empleados con información laboral
    """
    GENDER_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
    ]
    
    MARITAL_STATUS_CHOICES = [
        ('single', 'Soltero'),
        ('married', 'Casado'),
        ('divorced', 'Divorciado'),
        ('widowed', 'Viudo'),
    ]
    
    CONTRACT_TYPE_CHOICES = [
        ('permanent', 'Permanente'),
        ('temporary', 'Temporal'),
        ('contract', 'Por Contrato'),
        ('internship', 'Pasantía'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Activo'),
        ('inactive', 'Inactivo'),
        ('suspended', 'Suspendido'),
        ('terminated', 'Terminado'),
    ]
    
    # Relación con User
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee_profile'
    )
    
    # Información personal
    national_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Cédula/DNI'
    )
    
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        verbose_name='Género'
    )
    
    birth_date = models.DateField(
        verbose_name='Fecha de Nacimiento'
    )
    
    marital_status = models.CharField(
        max_length=10,
        choices=MARITAL_STATUS_CHOICES,
        default='single',
        verbose_name='Estado Civil'
    )
    
    address = models.TextField(
        verbose_name='Dirección'
    )
    
    # Información laboral
    employee_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Número de Empleado'
    )
    
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='employees',
        verbose_name='Departamento'
    )
    
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        related_name='employees',
        verbose_name='Cargo'
    )
    
    supervisor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates',
        verbose_name='Supervisor'
    )
    
    hire_date = models.DateField(
        verbose_name='Fecha de Contratación'
    )
    
    contract_type = models.CharField(
        max_length=15,
        choices=CONTRACT_TYPE_CHOICES,
        default='permanent',
        verbose_name='Tipo de Contrato'
    )
    
    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Salario Actual'
    )
    
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='Estado'
    )
    
    termination_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Terminación'
    )
    
    # Información de contacto de emergencia
    emergency_contact_name = models.CharField(
        max_length=100,
        verbose_name='Contacto de Emergencia'
    )
    
    emergency_contact_phone = models.CharField(
        max_length=17,
        verbose_name='Teléfono de Emergencia'
    )
    
    emergency_contact_relationship = models.CharField(
        max_length=50,
        verbose_name='Parentesco'
    )
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'
        db_table = 'employees_employee'
        ordering = ['employee_number']
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_number})"
    
    @property
    def full_name(self):
        return self.user.get_full_name()
    
    @property
    def is_active(self):
        return self.status == 'active'
    
    @property
    def years_of_service(self):
        from datetime import date
        if self.termination_date:
            end_date = self.termination_date
        else:
            end_date = date.today()
        
        years = end_date.year - self.hire_date.year
        if end_date.month < self.hire_date.month or (
            end_date.month == self.hire_date.month and 
            end_date.day < self.hire_date.day
        ):
            years -= 1
        return years


class EmployeeDocument(models.Model):
    """
    Modelo para documentos de empleados
    """
    DOCUMENT_TYPES = [
        ('contract', 'Contrato'),
        ('id_copy', 'Copia de Cédula'),
        ('resume', 'Currículum'),
        ('certificate', 'Certificado'),
        ('photo', 'Fotografía'),
        ('other', 'Otro'),
    ]
    
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Empleado'
    )
    
    document_type = models.CharField(
        max_length=15,
        choices=DOCUMENT_TYPES,
        verbose_name='Tipo de Documento'
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre del Documento'
    )
    
    file = models.FileField(
        upload_to='employee_documents/',
        verbose_name='Archivo'
    )
    
    upload_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Subida'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Notas'
    )
    
    class Meta:
        verbose_name = 'Documento de Empleado'
        verbose_name_plural = 'Documentos de Empleados'
        db_table = 'employees_document'
        ordering = ['-upload_date']
    
    def __str__(self):
        return f"{self.name} - {self.employee.full_name}"