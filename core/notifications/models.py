# core/notifications/models.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import datetime, timedelta


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
    
    # Nuevos campos para personalización
    icon = models.CharField(
        max_length=50,
        default='fa-bell',
        verbose_name='Icono FontAwesome'
    )
    
    color = models.CharField(
        max_length=20,
        default='primary',
        verbose_name='Color Bootstrap'
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


# Manager personalizado para notificaciones
class NotificationQuerySet(models.QuerySet):
    def unread(self):
        return self.filter(status='unread')
    
    def read(self):
        return self.filter(status='read')
    
    def for_user(self, user):
        return self.filter(recipient=user)
    
    def by_type(self, notification_type):
        return self.filter(notification_type__code=notification_type)
    
    def not_expired(self):
        return self.filter(
            models.Q(expires_at__isnull=True) | 
            models.Q(expires_at__gt=timezone.now())
        )
    
    def recent(self, days=7):
        since = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=since)


class NotificationManager(models.Manager):
    def get_queryset(self):
        return NotificationQuerySet(self.model, using=self._db)
    
    def unread(self):
        return self.get_queryset().unread()
    
    def read(self):
        return self.get_queryset().read()
    
    def for_user(self, user):
        return self.get_queryset().for_user(user)
    
    def by_type(self, notification_type):
        return self.get_queryset().by_type(notification_type)
    
    def not_expired(self):
        return self.get_queryset().not_expired()
    
    def recent(self, days=7):
        return self.get_queryset().recent(days)


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
    
    ACTION_CHOICES = [
        ('view', 'Ver'),
        ('approve', 'Aprobar'),
        ('reject', 'Rechazar'),
        ('edit', 'Editar'),
        ('download', 'Descargar'),
        ('none', 'Sin Acción'),
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
    
    # Nuevos campos para acciones dinámicas
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        default='view',
        verbose_name='Tipo de Acción'
    )
    
    action_url = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='URL de Acción'
    )
    
    # Metadatos adicionales en JSON
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Metadatos Adicionales'
    )
    
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
    
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Expira en'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Aplicar el manager personalizado
    objects = NotificationManager()
    
    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        db_table = 'notifications_notification'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        """Marcar notificación como leída"""
        if self.status == 'unread':
            self.status = 'read'
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])
    
    def is_expired(self):
        """Verificar si la notificación ha expirado"""
        return self.expires_at and timezone.now() > self.expires_at
    
    def get_icon(self):
        """Obtener icono basado en el tipo de notificación"""
        return self.notification_type.icon
    
    def get_color(self):
        """Obtener color basado en la prioridad"""
        color_map = {
            'low': 'secondary',
            'normal': self.notification_type.color,
            'high': 'warning',
            'urgent': 'danger'
        }
        return color_map.get(self.priority, 'primary')
    
    def get_time_ago(self):
        """Obtener tiempo transcurrido desde la creación"""
        now = timezone.now()
        diff = now - self.created_at
        
        if diff.days > 0:
            return f"Hace {diff.days} día{'s' if diff.days > 1 else ''}"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"Hace {hours} hora{'s' if hours > 1 else ''}"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"Hace {minutes} minuto{'s' if minutes > 1 else ''}"
        else:
            return "Hace un momento"


class NotificationPreference(models.Model):
    """
    Preferencias de notificación por usuario
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Tipos de notificaciones
    receive_leave_notifications = models.BooleanField(
        default=True,
        verbose_name='Notificaciones de Licencias'
    )
    
    receive_payroll_notifications = models.BooleanField(
        default=True,
        verbose_name='Notificaciones de Nómina'
    )
    
    receive_adelanto_notifications = models.BooleanField(
        default=True,
        verbose_name='Notificaciones de Adelantos'
    )
    
    # Canales de notificación
    email_enabled = models.BooleanField(
        default=True,
        verbose_name='Notificaciones por Email'
    )
    
    system_enabled = models.BooleanField(
        default=True,
        verbose_name='Notificaciones del Sistema'
    )
    
    # Horarios
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Inicio de Horas Silenciosas'
    )
    
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Fin de Horas Silenciosas'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Preferencia de Notificación'
        verbose_name_plural = 'Preferencias de Notificaciones'
        db_table = 'notifications_preferences'
    
    def __str__(self):
        return f"Preferencias de {self.user.username}"


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
    
    # Relacionar con notificación
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='email_queue'
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