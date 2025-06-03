from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator

class ReportTemplate(models.Model):
    """
    Plantillas de reportes
    """
    REPORT_TYPES = [
        ('payroll', 'Nómina'),
        ('attendance', 'Asistencia'),
        ('benefits', 'Beneficios'),
        ('deductions', 'Deducciones'),
        ('leaves', 'Licencias'),
        ('summary', 'Resumen'),
        ('custom', 'Personalizado'),
    ]
    
    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ]
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre del Reporte'
    )
    
    report_type = models.CharField(
        max_length=15,
        choices=REPORT_TYPES,
        verbose_name='Tipo de Reporte'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    query = models.TextField(
        verbose_name='Consulta SQL/QuerySet'
    )
    
    fields = models.JSONField(
        default=list,
        verbose_name='Campos a Incluir'
    )
    
    filters = models.JSONField(
        default=dict,
        verbose_name='Filtros Disponibles'
    )
    
    default_format = models.CharField(
        max_length=10,
        choices=FORMAT_CHOICES,
        default='pdf',
        verbose_name='Formato por Defecto'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Creado por'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Plantilla de Reporte'
        verbose_name_plural = 'Plantillas de Reportes'
        db_table = 'reports_template'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ReportGeneration(models.Model):
    """
    Historial de generación de reportes
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
    ]
    
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='generations',
        verbose_name='Plantilla'
    )
    
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Generado por'
    )
    
    parameters = models.JSONField(
        default=dict,
        verbose_name='Parámetros'
    )
    
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Estado'
    )
    
    file_path = models.FileField(
        upload_to='reports/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Archivo Generado'
    )
    
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='Tamaño del Archivo (bytes)'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='Mensaje de Error'
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Iniciado en'
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Completado en'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Generación de Reporte'
        verbose_name_plural = 'Generaciones de Reportes'
        db_table = 'reports_generation'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.template.name} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"
