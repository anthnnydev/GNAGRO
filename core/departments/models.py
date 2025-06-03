# core/departments/models.py
from django.db import models
from django.conf import settings
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
    
    code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Código del Departamento'
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
    
    parent_department = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_departments',
        verbose_name='Departamento Padre'
    )
    
    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Presupuesto'
    )
    
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Ubicación'
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
        db_table = 'departments_department'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def employee_count(self):
        """Número de empleados en este departamento"""
        return self.employees.filter(status='active').count()
    
    @property
    def total_budget(self):
        """Presupuesto total incluyendo subdepartamentos"""
        total = self.budget
        for sub_dept in self.sub_departments.filter(is_active=True):
            total += sub_dept.total_budget
        return total


class DepartmentCostCenter(models.Model):
    """
    Centros de costo por departamento
    """
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='cost_centers',
        verbose_name='Departamento'
    )
    
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código Centro de Costo'
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Presupuesto'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Centro de Costo'
        verbose_name_plural = 'Centros de Costo'
        db_table = 'departments_costcenter'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"