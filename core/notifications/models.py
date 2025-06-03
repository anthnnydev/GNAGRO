from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class NotificationType(models.Model):
    """
    Tipos de notificaciones
    """
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre del Tipo'
    )
    
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Código'
    )
    
    template_subject = models.CharField(
        max_length=200,
        verbose_name='Plantilla del Asunto'
    )
    
    template_body = models.TextField(
        verbose_name='Plantilla del Cuerpo'
    )
    
    is_email = models.BooleanField(
        default=True,
        verbose_name='Enviar por Email'
    )
    
    is_system = models.BooleanField(
        default=True,
        verbose_name='Notificación del Sistema'
    )
    
    auto_send = models.BooleanField(
        default=True,
        verbose_name='Envío Automático'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Tipo de Notificación'
        verbose_name_plural = 'Tipos de Notificaciones'
        db_table = 'notifications_type'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Notification(models.Model):
    """
    Notificaciones del sistema
    """
    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('normal', 'Normal'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ]
    
    STATUS_CHOICES = [
        ('unread', 'No Leída'),
        ('read', 'Leída'),
        ('archived', 'Archivada'),
    ]
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Destinatario'
    )
    
    notification_type = models.ForeignKey(
        NotificationType,
        on_delete=models.CASCADE,
        verbose_name='Tipo de Notificación'
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name='Título'
    )
    
    message = models.TextField(
        verbose_name='Mensaje'
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name='Prioridad'
    )
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='unread',
        verbose_name='Estado'
    )
    
    # Para relacionar con cualquier modelo
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Leída en'
    )
    
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Enviada en'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        db_table = 'notifications_notification'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"


class EmailQueue(models.Model):
    """
    Cola de emails para envío
    """
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('sent', 'Enviado'),
        ('failed', 'Fallido'),
        ('retry', 'Reintentando'),
    ]
    
    to_email = models.EmailField(
        verbose_name='Email Destinatario'
    )
    
    cc_emails = models.TextField(
        blank=True,
        verbose_name='Emails CC (separados por coma)'
    )
    
    bcc_emails = models.TextField(
        blank=True,
        verbose_name='Emails BCC (separados por coma)'
    )
    
    subject = models.CharField(
        max_length=200,
        verbose_name='Asunto'
    )
    
    body = models.TextField(
        verbose_name='Cuerpo del Mensaje'
    )
    
    html_body = models.TextField(
        blank=True,
        verbose_name='Cuerpo HTML'
    )
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Estado'
    )
    
    retry_count = models.IntegerField(
        default=0,
        verbose_name='Intentos de Reenvío'
    )
    
    max_retries = models.IntegerField(
        default=3,
        verbose_name='Máximo de Reintentos'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='Mensaje de Error'
    )
    
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Programado para'
    )
    
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Enviado en'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Email en Cola'
        verbose_name_plural = 'Emails en Cola'
        db_table = 'notifications_email_queue'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_at']),
        ]
    
    def __str__(self):
        return f"{self.subject} - {self.to_email}"