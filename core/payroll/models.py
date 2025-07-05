# core/payroll/models.py
from django.db import models
from django.conf import settings
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from core.employees.models import Employee


class TipoRubro(models.Model):
    """
    Define si un rubro es ingreso o egreso
    """
    TIPO_CHOICES = [
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso/Deducción'),
    ]
    
    nombre = models.CharField(
        max_length=50,
        verbose_name='Nombre del Tipo'
    )
    
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        verbose_name='Tipo'
    )
    
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Tipo de Rubro'
        verbose_name_plural = 'Tipos de Rubros'
        db_table = 'payroll_tipo_rubro'
        ordering = ['tipo', 'nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class Rubro(models.Model):
    """
    Rubros específicos de ingresos y egresos
    """
    CALCULO_CHOICES = [
        ('fijo', 'Monto Fijo'),
        ('porcentaje', 'Porcentaje del Salario Base'),
        ('porcentaje_bruto', 'Porcentaje del Salario Bruto'),
        ('horas', 'Por Horas'),
    ]
    
    tipo_rubro = models.ForeignKey(
        TipoRubro,
        on_delete=models.CASCADE,
        related_name='rubros',
        verbose_name='Tipo de Rubro'
    )
    
    codigo = models.CharField(
        max_length=10,
        unique=True,
        verbose_name='Código'
    )
    
    nombre = models.CharField(
        max_length=100,
        verbose_name='Nombre del Rubro'
    )
    
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    tipo_calculo = models.CharField(
        max_length=20,
        choices=CALCULO_CHOICES,
        default='fijo',
        verbose_name='Tipo de Cálculo'
    )
    
    # Para cálculos automáticos
    porcentaje_default = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Porcentaje por Defecto'
    )
    
    monto_default = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Monto por Defecto'
    )
    
    # Control de aplicación
    es_obligatorio = models.BooleanField(
        default=False,
        verbose_name='Es Obligatorio'
    )
    
    aplicar_automaticamente = models.BooleanField(
        default=False,
        verbose_name='Aplicar Automáticamente'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Rubro'
        verbose_name_plural = 'Rubros'
        db_table = 'payroll_rubro'
        ordering = ['tipo_rubro__tipo', 'nombre']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    @property
    def is_ingreso(self):
        return self.tipo_rubro.tipo == 'ingreso'
    
    @property
    def is_egreso(self):
        return self.tipo_rubro.tipo == 'egreso'


class PayrollPeriod(models.Model):
    """
    Períodos de nómina (mensual, quincenal, etc.)
    """
    PERIOD_TYPES = [
        ('monthly', 'Mensual'),
        ('biweekly', 'Quincenal'),  
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
        related_name='created_periods',
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
    """Modelo de nómina individual simplificado usando rubros"""
    
    employee = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        verbose_name="Empleado",
        related_name="payrolls"
    )
    period = models.ForeignKey(
        PayrollPeriod, 
        on_delete=models.CASCADE, 
        verbose_name="Período",
        related_name="payroll_entries"
    )
    
    quincena_numero = models.IntegerField(
        null=True,
        blank=True,
        choices=[(1, 'Primera Quincena'), (2, 'Segunda Quincena')],
        verbose_name='Número de Quincena',
        help_text='Solo aplica para períodos quincenales'
    )
    
    # Salario base (se toma del empleado automáticamente)
    base_salary = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Salario Base",
        help_text="Se toma automáticamente del perfil del empleado"
    )
    
    # Horas extra (mantenemos estos campos básicos)
    overtime_hours = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Horas Extra"
    )
    overtime_rate = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=1.50,
        validators=[MinValueValidator(Decimal('1.00'))],
        verbose_name="Factor Horas Extra"
    )
    
    # Campos de estado y control
    is_paid = models.BooleanField(default=False, verbose_name="Pagada")
    payment_date = models.DateField(null=True, blank=True, verbose_name="Fecha de Pago")
    payment_method = models.CharField(
        max_length=100, 
        blank=True, 
        default="Transferencia bancaria",
        verbose_name="Método de Pago"
    )
    
    # Metadatos
    notes = models.TextField(blank=True, verbose_name="Notas")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Creado por"
    )

    class Meta:
        unique_together = ['employee', 'period']
        ordering = ['-created_at']
        verbose_name = "Nómina"
        verbose_name_plural = "Nóminas"

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.period.name}"

    def save(self, *args, **kwargs):
        # Auto-asignar salario del empleado si no está definido
        if not self.base_salary and hasattr(self.employee, 'salary') and self.employee.salary:
            self.base_salary = self.employee.salary
        
        super().save(*args, **kwargs)

    @property
    def overtime_pay(self):
        """Calcular pago por horas extra"""
        if self.overtime_hours and self.base_salary:
            # Calcular pago por hora (asumiendo 160 horas mensuales)
            hourly_rate = self.base_salary / 160
            return hourly_rate * self.overtime_hours * self.overtime_rate
        return Decimal('0.00')

    @property
    def total_ingresos_rubros(self):
        """Total de ingresos adicionales por rubros"""
        return sum(
            rubro.monto for rubro in self.rubros_aplicados.filter(
                rubro__tipo_rubro__tipo='ingreso'
            )
        ) or Decimal('0.00')

    @property 
    def total_egresos_rubros(self):
        """Total de egresos por rubros"""
        return sum(
            rubro.monto for rubro in self.rubros_aplicados.filter(
                rubro__tipo_rubro__tipo='egreso'
            )
        ) or Decimal('0.00')

    @property
    def gross_pay(self):
        """Pago bruto total"""
        return (
            self.base_salary + 
            self.overtime_pay + 
            self.total_ingresos_rubros
        )

    @property
    def total_deductions(self):
        """Total de deducciones (solo rubros de egreso)"""
        return self.total_egresos_rubros
    
    @property
    def salary_divisor(self):
        """Divisor para salario según tipo de período"""
        if self.period.period_type == 'biweekly':
            return 2  # Dividir entre 2 para quincenas
        return 1  # Sin división para mensual
    
    @property
    def adjusted_base_salary(self):
        """Salario base ajustado según el tipo de período"""
        return self.base_salary / self.salary_divisor
    
    @property
    def overtime_pay(self):
        """Calcular pago por horas extra ajustado"""
        if self.overtime_hours and self.base_salary:
            # Calcular pago por hora (asumiendo 160 horas mensuales, 80 por quincena)
            hours_per_period = 160 / self.salary_divisor
            hourly_rate = self.base_salary / 160  # Siempre sobre base mensual
            return hourly_rate * self.overtime_hours * self.overtime_rate
        return Decimal('0.00')
    
    @property
    def gross_pay(self):
        """Pago bruto total ajustado por período"""
        return (
            self.adjusted_base_salary + 
            self.overtime_pay + 
            self.total_ingresos_rubros
        )

    @property
    def net_pay(self):
        """Pago neto"""
        return self.gross_pay - self.total_deductions

    def aplicar_rubros_automaticos(self):
        """Aplicar rubros automáticos según configuración"""
        from .models import Rubro, PayrollRubro
        
        # Obtener rubros automáticos activos
        rubros_automaticos = Rubro.objects.filter(
            aplicar_automaticamente=True,
            is_active=True
        ).select_related('tipo_rubro')
        
        for rubro in rubros_automaticos:
            # Verificar si ya está aplicado
            if not self.rubros_aplicados.filter(rubro=rubro).exists():
                monto_calculado = self._calcular_monto_rubro(rubro)
                
                if monto_calculado > 0:
                    PayrollRubro.objects.create(
                        payroll=self,
                        rubro=rubro,
                        monto=monto_calculado,
                        observaciones=f"Aplicado automáticamente - {rubro.descripcion or ''}"
                    )

    def _calcular_monto_rubro(self, rubro):
        """Calcular monto de un rubro según su configuración y tipo de período"""
        base_amount = Decimal('0.00')
        
        if rubro.tipo_calculo == 'fijo':
            base_amount = rubro.monto_default or Decimal('0.00')
        
        elif rubro.tipo_calculo == 'porcentaje':
            if rubro.porcentaje_default:
                base_amount = (self.base_salary * rubro.porcentaje_default) / 100
        
        elif rubro.tipo_calculo == 'porcentaje_bruto':
            if rubro.porcentaje_default:
                # Calcular sobre el bruto sin incluir otros rubros
                base_bruto = self.base_salary + self.overtime_pay
                base_amount = (base_bruto * rubro.porcentaje_default) / 100
        
        elif rubro.tipo_calculo == 'horas':
            if hasattr(self.employee, 'hourly_rate') and self.employee.hourly_rate:
                base_amount = self.employee.hourly_rate * (rubro.horas_default or Decimal('0.00'))
        
        # Aplicar divisor para períodos quincenales
        return base_amount / self.salary_divisor

    def get_adelantos_pendientes(self):
        from .models import AdelantoQuincena
        
        return AdelantoQuincena.objects.filter(
            employee=self.employee,
            is_descontado=False  # Solo adelantos que no han sido descontados
        )

    def get_rubros_by_type(self, tipo):
        """Obtener rubros aplicados por tipo (ingreso/egreso)"""
        return self.rubros_aplicados.filter(
            rubro__tipo_rubro__tipo=tipo
        ).select_related('rubro', 'rubro__tipo_rubro')

    @property
    def ingresos_adicionales(self):
        """Rubros de ingreso aplicados"""
        return self.get_rubros_by_type('ingreso')

    @property 
    def egresos_adicionales(self):
        """Rubros de egreso aplicados"""
        return self.get_rubros_by_type('egreso')

    def calcular_impuesto_renta(self):
        """Calcular impuesto a la renta según tabla vigente"""
        # Implementar lógica de cálculo de impuesto según legislación local
        # Por ahora retorna 0, pero aquí iría la lógica real
        return Decimal('0.00')

    def calcular_aporte_iess(self):
        """Calcular aporte IESS (ejemplo para Ecuador)"""
        if self.gross_pay:
            # 9.45% aporte personal IESS (ejemplo)
            return (self.gross_pay * Decimal('9.45')) / 100
        return Decimal('0.00')
    
    

    def aplicar_deducciones_legales(self):
        """Aplicar deducciones legales automáticamente"""
        from .models import Rubro, PayrollRubro, TipoRubro
        
        # Buscar o crear rubros de deducciones legales
        tipo_deduccion, _ = TipoRubro.objects.get_or_create(
            nombre="Deducciones Legales",
            tipo="egreso",
            defaults={
                'descripcion': 'Deducciones obligatorias por ley',
                'is_active': True
            }
        )
        
        # IESS
        rubro_iess, _ = Rubro.objects.get_or_create(
            codigo="IESS_PERSONAL",
            defaults={
                'nombre': 'Aporte Personal IESS',
                'tipo_rubro': tipo_deduccion,
                'tipo_calculo': 'porcentaje_bruto',
                'porcentaje_default': Decimal('9.45'),
                'is_active': True,
                'aplicar_automaticamente': True
            }
        )
        
        # Aplicar si no existe ya
        if not self.rubros_aplicados.filter(rubro=rubro_iess).exists():
            monto_iess = self.calcular_aporte_iess()
            if monto_iess > 0:
                PayrollRubro.objects.create(
                    payroll=self,
                    rubro=rubro_iess,
                    monto=monto_iess,
                    observaciones="Aporte personal IESS 9.45%"
                )


class PayrollRubro(models.Model):
    """
    Aplicación de rubros específicos a una nómina
    """
    payroll = models.ForeignKey(
        Payroll,
        on_delete=models.CASCADE,
        related_name='rubros_aplicados',
        verbose_name='Nómina'
    )
    
    rubro = models.ForeignKey(
        Rubro,
        on_delete=models.CASCADE,
        related_name='aplicaciones',
        verbose_name='Rubro'
    )
    
    # Valores específicos para esta aplicación
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Monto'
    )
    
    porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Porcentaje Aplicado'
    )
    
    horas = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Horas'
    )
    
    # Para el caso de adelantos de quincena
    es_adelanto = models.BooleanField(
        default=False,
        verbose_name='Es Adelanto'
    )
    
    fecha_adelanto = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha del Adelanto'
    )
    
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Rubro Aplicado'
        verbose_name_plural = 'Rubros Aplicados'
        db_table = 'payroll_rubro_aplicado'
        unique_together = ['payroll', 'rubro']
    
    def __str__(self):
        return f"{self.payroll.employee.user.get_full_name()} - {self.rubro.nombre}: ${self.monto}"
    
    def save(self, *args, **kwargs):
        # Calcular monto según tipo de cálculo
        if self.rubro.tipo_calculo == 'porcentaje' and self.porcentaje:
            self.monto = (self.payroll.base_salary * self.porcentaje) / 100
        elif self.rubro.tipo_calculo == 'porcentaje_bruto' and self.porcentaje:
            # Para porcentaje bruto, calcular sobre salario base + horas extra + otros ingresos
            bruto_base = (
                self.payroll.base_salary + 
                self.payroll.overtime_pay + 
                self.payroll.total_ingresos_rubros  # Usar el property que sí existe
            )
            self.monto = (bruto_base * self.porcentaje) / 100
        elif self.rubro.tipo_calculo == 'horas' and self.horas:
            # Calcular por horas (ejemplo: hora extra, hora normal, etc.)
            rate_per_hour = self.payroll.base_salary / 160  # Asumiendo 160 horas/mes
            self.monto = self.horas * rate_per_hour
        elif self.rubro.tipo_calculo == 'fijo':
            # Si es monto fijo y no se especificó, usar el default del rubro
            if self.monto == 0 and self.rubro.monto_default:
                self.monto = self.rubro.monto_default
        
        super().save(*args, **kwargs)
        
        # Marcar adelanto como descontado si es un adelanto
        if self.es_adelanto and self.fecha_adelanto:
            from .models import AdelantoQuincena  # Import local para evitar circular
            AdelantoQuincena.objects.filter(
                employee=self.payroll.employee,
                fecha_adelanto=self.fecha_adelanto,
                monto=self.monto,
                is_descontado=False
            ).update(
                is_descontado=True,
                payroll_descuento=self.payroll
            )


class AdelantoQuincena(models.Model):
    """
    Registro de adelantos de quincena para posterior descuento
    """
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='adelantos_quincena',
        verbose_name='Empleado'
    )
    
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto del Adelanto'
    )
    
    fecha_adelanto = models.DateField(
        verbose_name='Fecha del Adelanto'
    )
    
    motivo = models.TextField(
        blank=True,
        verbose_name='Motivo'
    )
    
    is_descontado = models.BooleanField(
        default=False,
        verbose_name='Ya Descontado'
    )
    
    payroll_descuento = models.ForeignKey(
        Payroll,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='adelantos_descontados',
        verbose_name='Nómina donde se descontó'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Autorizado por'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Adelanto de Quincena'
        verbose_name_plural = 'Adelantos de Quincena'
        db_table = 'payroll_adelanto_quincena'
        ordering = ['-fecha_adelanto']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - ${self.monto} ({self.fecha_adelanto})"


# Mantener PayrollDeduction para compatibilidad (deprecated)
class PayrollDeduction(models.Model):
    """
    Deducciones específicas de nómina (DEPRECATED - usar PayrollRubro)
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
        return f"{self.name} - {self.payroll.employee.user.get_full_name()}"


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