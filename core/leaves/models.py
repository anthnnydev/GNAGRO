# core/leaves/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, timedelta

class LeaveType(models.Model):
    """
    Tipos de licencias y permisos
    """
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre del Tipo de Licencia'
    )
    
    code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Código'
    )
    
    days_allowed = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name='Días Permitidos por Año'
    )
    
    requires_approval = models.BooleanField(
        default=True,
        verbose_name='Requiere Aprobación'
    )
    
    is_paid = models.BooleanField(
        default=True,
        verbose_name='Es Remunerada'
    )
    
    carry_forward = models.BooleanField(
        default=False,
        verbose_name='Transferible al Siguiente Año'
    )
    
    color = models.CharField(
        max_length=7,
        default='#007bff',
        verbose_name='Color (Hex)'
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
        verbose_name = 'Tipo de Licencia'
        verbose_name_plural = 'Tipos de Licencias'
        db_table = 'leaves_type'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class LeaveRequest(models.Model):
    """
    Solicitudes de licencias y permisos
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
        ('cancelled', 'Cancelada'),
    ]
    
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='leave_requests',
        verbose_name='Empleado'
    )
    
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        verbose_name='Tipo de Licencia'
    )
    
    start_date = models.DateField(
        verbose_name='Fecha de Inicio'
    )
    
    end_date = models.DateField(
        verbose_name='Fecha de Fin'
    )
    
    days_requested = models.IntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Días Solicitados'
    )
    
    reason = models.TextField(
        verbose_name='Motivo'
    )
    
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Estado'
    )
    
    approved_by = models.ForeignKey(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves',
        verbose_name='Aprobado por'
    )
    
    approved_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Aprobación'
    )
    
    rejection_reason = models.TextField(
        blank=True,
        verbose_name='Motivo de Rechazo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Solicitud de Licencia'
        verbose_name_plural = 'Solicitudes de Licencias'
        db_table = 'leaves_request'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type.name} ({self.start_date})"


class LeaveBalance(models.Model):
    """
    Balance de días de licencia por empleado
    """
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='leave_balances',
        verbose_name='Empleado'
    )
    
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        verbose_name='Tipo de Licencia'
    )
    
    year = models.IntegerField(
        verbose_name='Año'
    )
    
    allocated_days = models.IntegerField(
        default=0,
        verbose_name='Días Asignados'
    )
    
    used_days = models.IntegerField(
        default=0,
        verbose_name='Días Utilizados'
    )
    
    remaining_days = models.IntegerField(
        default=0,
        verbose_name='Días Restantes'
    )
    
    carried_forward = models.IntegerField(
        default=0,
        verbose_name='Días Transferidos'
    )
    
    class Meta:
        verbose_name = 'Balance de Licencias'
        verbose_name_plural = 'Balances de Licencias'
        db_table = 'leaves_balance'
        unique_together = ['employee', 'leave_type', 'year']
        ordering = ['-year', 'employee__first_name']
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.leave_type.name} ({self.year})"
