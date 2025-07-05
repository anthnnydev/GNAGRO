from django.db import models
from django.conf import settings
from decimal import Decimal
from django.core.validators import RegexValidator
from django.utils import timezone

class ExternalWorker(models.Model):
    """
    Modelo para trabajadores externos/eventuales
    No son empleados de la empresa, prestan servicios ocasionales
    """
    IDENTIFICATION_TYPES = [
        ('cedula', 'Cédula'),
        ('ruc', 'RUC'),
        ('pasaporte', 'Pasaporte'),
        ('rise', 'RISE'),
    ]
    
    # Información personal básica
    full_name = models.CharField(
        max_length=150,
        verbose_name='Nombre Completo'
    )
    
    identification_type = models.CharField(
        max_length=10,
        choices=IDENTIFICATION_TYPES,
        default='cedula',
        verbose_name='Tipo de Identificación'
    )
    
    identification_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Número de Identificación'
    )
    
    phone = models.CharField(
        max_length=15,
        blank=True,
        verbose_name='Teléfono'
    )
    
    email = models.EmailField(
        blank=True,
        verbose_name='Email'
    )
    
    address = models.TextField(
        blank=True,
        verbose_name='Dirección'
    )
    
    # Información tributaria
    has_ruc = models.BooleanField(
        default=False,
        verbose_name='Tiene RUC'
    )
    
    ruc_number = models.CharField(
        max_length=13,
        blank=True,
        verbose_name='Número de RUC'
    )
    
    has_rise = models.BooleanField(
        default=False,
        verbose_name='Tiene RISE'
    )
    
    business_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Razón Social'
    )
    
    # Metadatos
    notes = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Registrado por'
    )
    
    class Meta:
        verbose_name = 'Trabajador Externo'
        verbose_name_plural = 'Trabajadores Externos'
        db_table = 'external_workers'
        ordering = ['full_name']
    
    def __str__(self):
        return f"{self.full_name} ({self.identification_number})"
    
    @property
    def can_issue_invoice(self):
        """Determina si puede emitir factura"""
        return self.has_ruc or self.has_rise
    
    @property
    def total_payments_this_year(self):
        """Total de pagos en el año actual"""
        current_year = timezone.now().year
        return self.external_payments.filter(
            payment_date__year=current_year
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')


class ServiceType(models.Model):
    """
    Tipos de servicios que pueden prestar trabajadores externos
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre del Servicio'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    # Configuración de pago
    default_unit = models.CharField(
        max_length=50,
        default='día',
        verbose_name='Unidad por Defecto',
        help_text='ej: día, hectárea, metro, quintal, etc.'
    )
    
    default_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Tarifa por Defecto'
    )
    
    requires_invoice = models.BooleanField(
        default=False,
        verbose_name='Requiere Factura',
        help_text='Si es obligatorio que emitan factura'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Tipo de Servicio'
        verbose_name_plural = 'Tipos de Servicios'
        db_table = 'external_service_types'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ExternalPayment(models.Model):
    """
    Registro de pagos a trabajadores externos por servicios prestados
    """
    PAYMENT_STATUS = [
        ('pending', 'Pendiente'),
        ('paid', 'Pagado'),
        ('cancelled', 'Cancelado'),
    ]
    
    PAYMENT_METHODS = [
        ('cash', 'Efectivo'),
        ('transfer', 'Transferencia Bancaria'),
        ('check', 'Cheque'),
        ('other', 'Otro'),
    ]
    
    # Referencias principales
    external_worker = models.ForeignKey(
        ExternalWorker,
        on_delete=models.CASCADE,
        related_name='external_payments',
        verbose_name='Trabajador Externo'
    )
    
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name='Tipo de Servicio'
    )
    
    # Información del trabajo
    work_description = models.TextField(
        verbose_name='Descripción del Trabajo',
        help_text='Detalle específico del trabajo realizado'
    )
    
    start_date = models.DateField(
        verbose_name='Fecha de Inicio'
    )
    
    end_date = models.DateField(
        verbose_name='Fecha de Fin'
    )
    
    # Cálculo del pago
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
        verbose_name='Cantidad'
    )
    
    unit = models.CharField(
        max_length=50,
        verbose_name='Unidad'
    )
    
    unit_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Tarifa por Unidad'
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto Total'
    )
    
    # Información de pago
    payment_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Pago'
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='cash',
        verbose_name='Método de Pago'
    )
    
    status = models.CharField(
        max_length=15,
        choices=PAYMENT_STATUS,
        default='pending',
        verbose_name='Estado'
    )
    
    # Información fiscal
    has_invoice = models.BooleanField(
        default=False,
        verbose_name='Emitió Factura'
    )
    
    invoice_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Número de Factura'
    )
    
    invoice_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Factura'
    )
    
    tax_withheld = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Retención de Impuestos'
    )
    
    # Documentación de respaldo
    contract_file = models.FileField(
        upload_to='external_payments/contracts/',
        blank=True,
        null=True,
        verbose_name='Contrato/Acuerdo'
    )
    
    invoice_file = models.FileField(
        upload_to='external_payments/invoices/',
        blank=True,
        null=True,
        verbose_name='Archivo de Factura'
    )
    
    # Observaciones y control
    notes = models.TextField(
        blank=True,
        verbose_name='Observaciones'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Registrado por'
    )
    
    class Meta:
        verbose_name = 'Pago por Servicio Externo'
        verbose_name_plural = 'Pagos por Servicios Externos'
        db_table = 'external_payments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.external_worker.full_name} - {self.service_type.name} (${self.amount})"
    
    def save(self, *args, **kwargs):
        # Calcular monto automáticamente si no está definido
        if not self.amount:
            self.amount = self.quantity * self.unit_rate
        
        # Asignar unidad por defecto del tipo de servicio
        if not self.unit and self.service_type:
            self.unit = self.service_type.default_unit
        
        super().save(*args, **kwargs)
    
    @property
    def work_duration_days(self):
        """Duración del trabajo en días"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 1
    
    @property
    def net_payment(self):
        """Pago neto después de retenciones"""
        return self.amount - self.tax_withheld
    
    @property
    def requires_tax_withholding(self):
        """Determina si requiere retención según el monto"""
        # Ejemplo: retención si supera $300 en Ecuador
        return self.amount > Decimal('300.00')
    
    def calculate_tax_withholding(self):
        """Calcula retención automática si aplica"""
        if self.requires_tax_withholding and not self.external_worker.has_ruc:
            # 2% de retención para personas naturales sin RUC
            return (self.amount * Decimal('2.00')) / 100
        return Decimal('0.00')
    
    def mark_as_paid(self, payment_date=None, payment_method='cash'):
        """Marcar como pagado"""
        self.status = 'paid'
        self.payment_date = payment_date or timezone.now().date()
        self.payment_method = payment_method
        self.save()


class ExternalPaymentDocument(models.Model):
    """
    Documentos adicionales relacionados con pagos externos
    """
    DOCUMENT_TYPES = [
        ('contract', 'Contrato'),
        ('invoice', 'Factura'),
        ('receipt', 'Recibo'),
        ('work_photo', 'Foto del Trabajo'),
        ('id_copy', 'Copia de Cédula'),
        ('other', 'Otro'),
    ]
    
    external_payment = models.ForeignKey(
        ExternalPayment,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Pago Externo'
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
        upload_to='external_payments/documents/',
        verbose_name='Archivo'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    upload_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Documento de Pago Externo'
        verbose_name_plural = 'Documentos de Pagos Externos'
        db_table = 'external_payment_documents'
        ordering = ['-upload_date']
    
    def __str__(self):
        return f"{self.name} - {self.external_payment}"