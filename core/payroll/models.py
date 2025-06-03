# core/payroll/models.py
from django.db import models
from django.conf import settings
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator

class PayrollPeriod(models.Model):
    """
    Períodos de nómina (mensual, quincenal, etc.)
    """
    PERIOD_TYPES = [
        ('monthly', 'Mensual'),
        ('biweekly', 'Quincenal'),  
        ('weekly', 'Semanal'),
        ('daily', 'Diaria'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('processing', 'Procesando'),
        ('completed', 'Completada'),
        ('paid', 'Pagada'),
        ('cancelled', 'Cancelada'),
    ]
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre del Período'
    )
    
    period_type = models.CharField(
        max_length=15,
        choices=PERIOD_TYPES,
        verbose_name='Tipo de Período'
    )
    
    start_date = models.DateField(
        verbose_name='Fecha de Inicio'
    )
    
    end_date = models.DateField(
        verbose_name='Fecha de Fin'
    )
    
    pay_date = models.DateField(
        verbose_name='Fecha de Pago'
    )
    
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Estado'
    )
    
    is_closed = models.BooleanField(
        default=False,
        verbose_name='Cerrado'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Notas'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_payrolls',
        verbose_name='Creado por'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Período de Nómina'
        verbose_name_plural = 'Períodos de Nómina'
        db_table = 'payroll_period'
        ordering = ['-start_date']
        unique_together = ['start_date', 'end_date', 'period_type']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
    
    @property
    def total_employees(self):
        return self.payroll_entries.count()
    
    @property
    def total_gross_pay(self):
        return sum(entry.gross_pay for entry in self.payroll_entries.all())
    
    @property
    def total_net_pay(self):
        return sum(entry.net_pay for entry in self.payroll_entries.all())


class Payroll(models.Model):
    """
    Registro de nómina individual por empleado
    """
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='payrolls',
        verbose_name='Empleado'
    )
    
    period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.CASCADE,
        related_name='payroll_entries',
        verbose_name='Período'
    )
    
    # Salarios y pagos
    base_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Salario Base'
    )
    
    overtime_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Horas Extras'
    )
    
    overtime_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.50'),
        verbose_name='Factor Horas Extras'
    )
    
    overtime_pay = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Pago Horas Extras'
    )
    
    bonus = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Bonificaciones'
    )
    
    commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Comisiones'
    )
    
    allowances = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Subsidios'
    )
    
    gross_pay = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Pago Bruto'
    )
    
    # Deducciones
    income_tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Impuesto a la Renta'
    )
    
    social_security = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Seguridad Social'
    )
    
    health_insurance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Seguro de Salud'
    )
    
    other_deductions = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Otras Deducciones'
    )
    
    total_deductions = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Total Deducciones'
    )
    
    net_pay = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Pago Neto'
    )
    
    # Control
    is_paid = models.BooleanField(
        default=False,
        verbose_name='Pagado'
    )
    
    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Pago'
    )
    
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Método de Pago'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Notas'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Nómina'
        verbose_name_plural = 'Nóminas'
        db_table = 'payroll_payroll'
        ordering = ['-period__start_date', 'employee__employee_number']
        unique_together = ['employee', 'period']
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.period.name}"
    
    def save(self, *args, **kwargs):
        # Calcular automáticamente los totales
        self.overtime_pay = self.overtime_hours * (self.base_salary / 160) * self.overtime_rate
        self.gross_pay = self.base_salary + self.overtime_pay + self.bonus + self.commission + self.allowances
        self.total_deductions = self.income_tax + self.social_security + self.health_insurance + self.other_deductions
        self.net_pay = self.gross_pay - self.total_deductions
        super().save(*args, **kwargs)


class PayrollDeduction(models.Model):
    """
    Deducciones específicas de nómina
    """
    DEDUCTION_TYPES = [
        ('tax', 'Impuesto'),
        ('insurance', 'Seguro'),
        ('loan', 'Préstamo'),
        ('union', 'Sindicato'),
        ('other', 'Otro'),
    ]
    
    payroll = models.ForeignKey(
        Payroll,
        on_delete=models.CASCADE,
        related_name='deductions',
        verbose_name='Nómina'
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre de la Deducción'
    )
    
    deduction_type = models.CharField(
        max_length=20,
        choices=DEDUCTION_TYPES,
        verbose_name='Tipo'
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto'
    )
    
    is_percentage = models.BooleanField(
        default=False,
        verbose_name='Es Porcentaje'
    )
    
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Porcentaje'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Deducción de Nómina'
        verbose_name_plural = 'Deducciones de Nómina'
        db_table = 'payroll_deduction'
    
    def __str__(self):
        return f"{self.name} - {self.payroll.employee.full_name}"


class PayslipTemplate(models.Model):
    """
    Plantillas para recibos de pago
    """
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre de la Plantilla'
    )
    
    template_html = models.TextField(
        verbose_name='HTML de la Plantilla'
    )
    
    is_default = models.BooleanField(
        default=False,
        verbose_name='Plantilla por Defecto'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activa'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Plantilla de Recibo'
        verbose_name_plural = 'Plantillas de Recibo'
        db_table = 'payroll_template'
    
    def __str__(self):
        return self.name