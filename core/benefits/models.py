from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class BenefitCategory(models.Model):
    """
    Categorías de beneficios
    """
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre de la Categoría'
    )
    
    code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Código'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Categoría de Beneficio'
        verbose_name_plural = 'Categorías de Beneficios'
        db_table = 'benefits_category'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Benefit(models.Model):
    """
    Beneficios y prestaciones
    """
    CALCULATION_TYPES = [
        ('fixed', 'Monto Fijo'),
        ('percentage', 'Porcentaje del Salario'),
        ('formula', 'Fórmula Personalizada'),
    ]
    
    FREQUENCY_CHOICES = [
        ('monthly', 'Mensual'),
        ('biweekly', 'Quincenal'),
        ('weekly', 'Semanal'),
        ('annual', 'Anual'),
        ('one_time', 'Una Sola Vez'),
    ]
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre del Beneficio'
    )
    
    code = models.CharField(
        max_length=15,
        unique=True,
        verbose_name='Código'
    )
    
    category = models.ForeignKey(
        BenefitCategory,
        on_delete=models.CASCADE,
        related_name='benefits',
        verbose_name='Categoría'
    )
    
    calculation_type = models.CharField(
        max_length=15,
        choices=CALCULATION_TYPES,
        default='fixed',
        verbose_name='Tipo de Cálculo'
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Monto/Porcentaje'
    )
    
    frequency = models.CharField(
        max_length=15,
        choices=FREQUENCY_CHOICES,
        default='monthly',
        verbose_name='Frecuencia'
    )
    
    is_taxable = models.BooleanField(
        default=True,
        verbose_name='Gravable'
    )
    
    max_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Monto Máximo'
    )
    
    min_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Monto Mínimo'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Beneficio'
        verbose_name_plural = 'Beneficios'
        db_table = 'benefits_benefit'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Deduction(models.Model):
    """
    Deducciones
    """
    CALCULATION_TYPES = [
        ('fixed', 'Monto Fijo'),
        ('percentage', 'Porcentaje del Salario'),
        ('progressive', 'Escala Progresiva'),
    ]
    
    FREQUENCY_CHOICES = [
        ('monthly', 'Mensual'),
        ('biweekly', 'Quincenal'),
        ('weekly', 'Semanal'),
        ('annual', 'Anual'),
        ('one_time', 'Una Sola Vez'),
    ]
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre de la Deducción'
    )
    
    code = models.CharField(
        max_length=15,
        unique=True,
        verbose_name='Código'
    )
    
    calculation_type = models.CharField(
        max_length=15,
        choices=CALCULATION_TYPES,
        default='fixed',
        verbose_name='Tipo de Cálculo'
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Monto/Porcentaje'
    )
    
    frequency = models.CharField(
        max_length=15,
        choices=FREQUENCY_CHOICES,
        default='monthly',
        verbose_name='Frecuencia'
    )
    
    is_mandatory = models.BooleanField(
        default=False,
        verbose_name='Obligatoria'
    )
    
    max_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Monto Máximo'
    )
    
    min_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Monto Mínimo'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Deducción'
        verbose_name_plural = 'Deducciones'
        db_table = 'benefits_deduction'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class EmployeeBenefit(models.Model):
    """
    Beneficios asignados a empleados
    """
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='employee_benefits',
        verbose_name='Empleado'
    )
    
    benefit = models.ForeignKey(
        Benefit,
        on_delete=models.CASCADE,
        verbose_name='Beneficio'
    )
    
    custom_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Monto Personalizado'
    )
    
    start_date = models.DateField(
        verbose_name='Fecha de Inicio'
    )
    
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Fin'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Notas'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Beneficio de Empleado'
        verbose_name_plural = 'Beneficios de Empleados'
        db_table = 'benefits_employee_benefit'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.benefit.name}"


class EmployeeDeduction(models.Model):
    """
    Deducciones asignadas a empleados
    """
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='employee_deductions',
        verbose_name='Empleado'
    )
    
    deduction = models.ForeignKey(
        Deduction,
        on_delete=models.CASCADE,
        verbose_name='Deducción'
    )
    
    custom_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Monto Personalizado'
    )
    
    start_date = models.DateField(
        verbose_name='Fecha de Inicio'
    )
    
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Fin'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Notas'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Deducción de Empleado'
        verbose_name_plural = 'Deducciones de Empleados'
        db_table = 'benefits_employee_deduction'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.deduction.name}"
