# core/notifications/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in

from core.leaves.models import LeaveRequest
from core.payroll.models import Payroll, AdelantoQuincena, PayrollRubro
from .models import NotificationPreference
from .services import NotificationService

import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=LeaveRequest)
def handle_leave_request_notification(sender, instance, created, **kwargs):
    """Manejar notificaciones de solicitudes de licencia"""
    
    if created:
        # Nueva solicitud creada
        NotificationService.notify_leave_request_created(instance)
        logger.info(f"Notificación enviada: Nueva solicitud de licencia de {instance.employee.user.get_full_name()}")
    
    else:
        # Solicitud actualizada - verificar cambio de estado
        if hasattr(instance, '_state_changed'):
            old_status = instance._state_changed.get('status')
            new_status = instance.status
            
            if old_status == 'pending' and new_status == 'approved':
                NotificationService.notify_leave_request_approved(instance)
                logger.info(f"Notificación enviada: Licencia aprobada para {instance.employee.user.get_full_name()}")
            
            elif old_status == 'pending' and new_status == 'rejected':
                NotificationService.notify_leave_request_rejected(instance)
                logger.info(f"Notificación enviada: Licencia rechazada para {instance.employee.user.get_full_name()}")


@receiver(pre_save, sender=LeaveRequest)
def track_leave_request_status_change(sender, instance, **kwargs):
    """Rastrear cambios de estado en solicitudes de licencia"""
    
    if instance.pk:
        try:
            old_instance = LeaveRequest.objects.get(pk=instance.pk)
            instance._state_changed = {
                'status': old_instance.status
            }
        except LeaveRequest.DoesNotExist:
            pass


@receiver(post_save, sender=Payroll)
def handle_payroll_notification(sender, instance, created, **kwargs):
    """Manejar notificaciones de nómina"""
    
    if created:
        # Nueva nómina creada
        NotificationService.notify_payroll_ready(instance)
        logger.info(f"Notificación enviada: Nómina lista para {instance.employee.user.get_full_name()}")
    
    else:
        # Nómina actualizada - verificar si fue marcada como pagada
        if hasattr(instance, '_payment_changed'):
            old_is_paid = instance._payment_changed.get('is_paid', False)
            new_is_paid = instance.is_paid
            
            if not old_is_paid and new_is_paid:
                NotificationService.notify_payroll_paid(instance)
                logger.info(f"Notificación enviada: Nómina pagada para {instance.employee.user.get_full_name()}")


@receiver(pre_save, sender=Payroll)
def track_payroll_payment_change(sender, instance, **kwargs):
    """Rastrear cambios de pago en nóminas"""
    
    if instance.pk:
        try:
            old_instance = Payroll.objects.get(pk=instance.pk)
            instance._payment_changed = {
                'is_paid': old_instance.is_paid
            }
        except Payroll.DoesNotExist:
            pass


@receiver(post_save, sender=AdelantoQuincena)
def handle_adelanto_notification(sender, instance, created, **kwargs):
    """Manejar notificaciones de adelantos"""
    
    if created:
        # Nuevo adelanto creado
        NotificationService.notify_adelanto_approved(instance)
        logger.info(f"Notificación enviada: Adelanto aprobado para {instance.employee.user.get_full_name()}")


@receiver(post_save, sender=PayrollRubro)
def handle_payroll_rubro_notification(sender, instance, created, **kwargs):
    """Manejar notificaciones de rubros de nómina"""
    
    if created and instance.es_adelanto:
        # Rubro de adelanto aplicado (descontado)
        NotificationService.notify_adelanto_processed(instance)
        logger.info(f"Notificación enviada: Adelanto descontado para {instance.payroll.employee.user.get_full_name()}")


@receiver(user_logged_in)
def create_notification_preferences(sender, request, user, **kwargs):
    """Crear preferencias de notificación por defecto al hacer login"""
    
    NotificationPreference.objects.get_or_create(
        user=user,
        defaults={
            'receive_leave_notifications': True,
            'receive_payroll_notifications': True,
            'receive_adelanto_notifications': True,
            'email_enabled': True,
            'system_enabled': True,
        }
    )