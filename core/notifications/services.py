# core/notifications/services.py
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from django.apps import apps

from .models import Notification, NotificationType, NotificationPreference, EmailQueue
from core.employees.models import Employee
from core.leaves.models import LeaveRequest
from core.payroll.models import Payroll, AdelantoQuincena

import logging

logger = logging.getLogger(__name__)

# Obtener el modelo User correctamente
User = get_user_model()


class NotificationService:
    """Servicio central para manejo de notificaciones"""
    
    @staticmethod
    def setup_notification_types():
        """Crear tipos de notificación por defecto"""
        
        notification_types = [
            {
                'name': 'Solicitud de Licencia',
                'code': 'leave_request_created',
                'template_subject': 'Nueva solicitud de licencia de {employee_name}',
                'template_body': 'El empleado {employee_name} ha solicitado {days} días de {leave_type} desde {start_date} hasta {end_date}.',
                'icon': 'fa-calendar-alt',
                'color': 'info'
            },
            {
                'name': 'Licencia Aprobada',
                'code': 'leave_request_approved',
                'template_subject': 'Tu solicitud de licencia ha sido aprobada',
                'template_body': 'Tu solicitud de {leave_type} desde {start_date} hasta {end_date} ha sido aprobada por {approved_by}.',
                'icon': 'fa-check-circle',
                'color': 'success'
            },
            {
                'name': 'Licencia Rechazada',
                'code': 'leave_request_rejected',
                'template_subject': 'Tu solicitud de licencia ha sido rechazada',
                'template_body': 'Tu solicitud de {leave_type} desde {start_date} hasta {end_date} ha sido rechazada. Motivo: {rejection_reason}',
                'icon': 'fa-times-circle',
                'color': 'danger'
            },
            {
                'name': 'Nómina Disponible',
                'code': 'payroll_ready',
                'template_subject': 'Tu nómina de {period} está disponible',
                'template_body': 'Ya puedes consultar tu nómina del período {period}. Salario neto: ${net_pay}',
                'icon': 'fa-money-bill-wave',
                'color': 'success'
            },
            {
                'name': 'Nómina Pagada',
                'code': 'payroll_paid',
                'template_subject': 'Tu nómina de {period} ha sido pagada',
                'template_body': 'Tu nómina del período {period} ha sido pagada exitosamente. El pago se realizó por {payment_method} el {payment_date}.',
                'icon': 'fa-credit-card',
                'color': 'success'
            },
            {
                'name': 'Adelanto Aprobado',
                'code': 'adelanto_approved',
                'template_subject': 'Tu adelanto de ${amount} ha sido aprobado',
                'template_body': 'Tu solicitud de adelanto por ${amount} ha sido aprobada. El monto será descontado en tu próxima nómina.',
                'icon': 'fa-hand-holding-usd',
                'color': 'info'
            },
            {
                'name': 'Adelanto Procesado',
                'code': 'adelanto_processed',
                'template_subject': 'Adelanto de ${amount} descontado de tu nómina',
                'template_body': 'Se ha descontado ${amount} de tu nómina correspondiente al adelanto del {adelanto_date}.',
                'icon': 'fa-minus-circle',
                'color': 'warning'
            },
            {
                'name': 'Sistema General',
                'code': 'system_general',
                'template_subject': '{title}',
                'template_body': '{message}',
                'icon': 'fa-bell',
                'color': 'primary'
            }
        ]
        
        for notification_data in notification_types:
            NotificationType.objects.get_or_create(
                code=notification_data['code'],
                defaults=notification_data
            )
    
    @staticmethod
    def create_notification(recipient, notification_type_code, title=None, message=None, 
                          related_object=None, action_url=None, priority='normal', 
                          expires_in_days=None, metadata=None, **template_vars):
        """Crear una nueva notificación"""
        
        try:
            # Obtener tipo de notificación
            notification_type = NotificationType.objects.get(
                code=notification_type_code,
                is_active=True
            )
            
            # Verificar preferencias del usuario
            prefs = NotificationPreference.objects.filter(user=recipient).first()
            if prefs:
                # Verificar si el usuario quiere recibir este tipo de notificación
                preference_map = {
                    'leave_request_created': prefs.receive_leave_notifications,
                    'leave_request_approved': prefs.receive_leave_notifications,
                    'leave_request_rejected': prefs.receive_leave_notifications,
                    'payroll_ready': prefs.receive_payroll_notifications,
                    'payroll_paid': prefs.receive_payroll_notifications,
                    'adelanto_approved': prefs.receive_adelanto_notifications,
                    'adelanto_processed': prefs.receive_adelanto_notifications,
                }
                
                if not preference_map.get(notification_type_code, True):
                    logger.info(f"Usuario {recipient.username} tiene deshabilitadas las notificaciones de tipo {notification_type_code}")
                    return None
            
            # Generar título y mensaje usando plantillas
            if not title:
                title = notification_type.template_subject.format(**template_vars)
            if not message:
                message = notification_type.template_body.format(**template_vars)
            
            # Configurar expiración
            expires_at = None
            if expires_in_days:
                expires_at = timezone.now() + timedelta(days=expires_in_days)
            
            # Obtener content_type si hay objeto relacionado
            content_type = None
            object_id = None
            if related_object:
                content_type = ContentType.objects.get_for_model(related_object)
                object_id = related_object.pk
            
            # Crear notificación
            notification = Notification.objects.create(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message,
                priority=priority,
                content_type=content_type,
                object_id=object_id,
                action_url=action_url,
                expires_at=expires_at,
                metadata=metadata or {}
            )
            
            # Enviar email si está habilitado
            if notification_type.is_email and (not prefs or prefs.email_enabled):
                NotificationService.queue_email_notification(notification, template_vars)
            
            logger.info(f"Notificación creada: {title} para {recipient.username}")
            return notification
            
        except NotificationType.DoesNotExist:
            logger.error(f"Tipo de notificación {notification_type_code} no encontrado")
            return None
        except Exception as e:
            logger.error(f"Error creando notificación: {str(e)}")
            return None
    
    @staticmethod
    def queue_email_notification(notification, template_vars=None):
        """Encolar email para envío"""
        try:
            # Crear entrada en cola de email
            EmailQueue.objects.create(
                notification=notification,
                to_email=notification.recipient.email,
                subject=notification.title,
                body=notification.message,
                # Aquí podrías generar HTML más elaborado
                html_body=f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #333;">{notification.title}</h2>
                    <p>{notification.message}</p>
                    <hr>
                    <p style="color: #666; font-size: 12px;">
                        Este es un mensaje automático del Sistema de Nómina.
                        <br>Fecha: {notification.created_at.strftime('%d/%m/%Y %H:%M')}
                    </p>
                </div>
                """,
                scheduled_at=timezone.now()
            )
            
        except Exception as e:
            logger.error(f"Error encolando email: {str(e)}")
    
    # Métodos específicos para cada tipo de notificación
    
    @staticmethod
    def notify_leave_request_created(leave_request):
        """Notificar nueva solicitud de licencia a supervisores"""
        
        # Obtener supervisores que deben ser notificados
        supervisors = []
        
        # Supervisor directo
        if leave_request.employee.supervisor:
            supervisors.append(leave_request.employee.supervisor.user)
        
        # Jefe de departamento
        if leave_request.employee.department.manager:
            supervisors.append(leave_request.employee.department.manager)
        
        # Usuarios con permisos de aprobación - CORREGIDO
        try:
            # Usar el modelo User correcto
            permission_users = User.objects.filter(
                Q(user_permissions__codename='change_leaverequest') |
                Q(groups__permissions__codename='change_leaverequest')
            ).distinct()
            
            # Convertir a lista para evitar problemas con el QuerySet
            permission_users_list = list(permission_users)
            
        except Exception as e:
            logger.error(f"Error obteniendo usuarios con permisos: {e}")
            permission_users_list = []
        
        # Combinar todos los destinatarios
        all_recipients = set(supervisors)
        all_recipients.update(permission_users_list)
        
        # Remover al empleado solicitante de los destinatarios
        all_recipients.discard(leave_request.employee.user)
        
        template_vars = {
            'employee_name': leave_request.employee.user.get_full_name(),
            'days': leave_request.days_requested,
            'leave_type': leave_request.leave_type.name,
            'start_date': leave_request.start_date.strftime('%d/%m/%Y'),
            'end_date': leave_request.end_date.strftime('%d/%m/%Y'),
        }
        
        # Enviar notificación a cada destinatario
        for recipient in all_recipients:
            try:
                NotificationService.create_notification(
                    recipient=recipient,
                    notification_type_code='leave_request_created',
                    related_object=leave_request,
                    action_url=f'/leaves/requests/{leave_request.id}/',  # ✅ URL CORRECTA
                    priority='normal',
                    expires_in_days=30,
                    **template_vars
                )
                logger.info(f"Notificación enviada a {recipient.get_full_name()}")
            except Exception as e:
                logger.error(f"Error enviando notificación a {recipient.get_full_name()}: {e}")
    
    @staticmethod
    def notify_leave_request_approved(leave_request):
        """Notificar aprobación de licencia al empleado"""
        
        template_vars = {
            'leave_type': leave_request.leave_type.name,
            'start_date': leave_request.start_date.strftime('%d/%m/%Y'),
            'end_date': leave_request.end_date.strftime('%d/%m/%Y'),
            'approved_by': leave_request.approved_by.user.get_full_name() if leave_request.approved_by else 'Sistema',
        }
        
        NotificationService.create_notification(
            recipient=leave_request.employee.user,
            notification_type_code='leave_request_approved',
            related_object=leave_request,
            action_url=f'/leaves/requests/{leave_request.id}/',  # ✅ URL CORRECTA
            priority='normal',
            **template_vars
        )
    
    @staticmethod
    def notify_leave_request_rejected(leave_request):
        """Notificar rechazo de licencia al empleado"""
        
        template_vars = {
            'leave_type': leave_request.leave_type.name,
            'start_date': leave_request.start_date.strftime('%d/%m/%Y'),
            'end_date': leave_request.end_date.strftime('%d/%m/%Y'),
            'rejection_reason': getattr(leave_request, 'supervisor_notes', 'No se especificó motivo'),
        }
        
        NotificationService.create_notification(
            recipient=leave_request.employee.user,
            notification_type_code='leave_request_rejected',
            related_object=leave_request,
            action_url=f'/leaves/requests/{leave_request.id}/',  # ✅ URL CORRECTA
            priority='high',
            **template_vars
        )
    
    @staticmethod
    def notify_payroll_ready(payroll):
        """Notificar que la nómina está lista"""
        
        template_vars = {
            'period': payroll.period.name,
            'net_pay': f"{payroll.net_pay:,.2f}",
        }
        
        NotificationService.create_notification(
            recipient=payroll.employee.user,
            notification_type_code='payroll_ready',
            related_object=payroll,
            action_url=f'/payroll/admin/nominas/{payroll.id}/',  # ✅ URL CORRECTA
            priority='normal',
            **template_vars
        )
    
    @staticmethod
    def notify_payroll_paid(payroll):
        """Notificar que la nómina ha sido pagada"""
        
        template_vars = {
            'period': payroll.period.name,
            'payment_method': payroll.payment_method or 'Transferencia bancaria',
            'payment_date': payroll.payment_date.strftime('%d/%m/%Y') if payroll.payment_date else 'Hoy',
        }
        
        NotificationService.create_notification(
            recipient=payroll.employee.user,
            notification_type_code='payroll_paid',
            related_object=payroll,
            action_url=f'/payroll/admin/nominas/{payroll.id}/',  # ✅ URL CORRECTA
            priority='normal',
            **template_vars
        )
    
    @staticmethod
    def notify_adelanto_approved(adelanto):
        """Notificar aprobación de adelanto"""
        
        template_vars = {
            'amount': f"{adelanto.monto:,.2f}",
        }
        
        NotificationService.create_notification(
            recipient=adelanto.employee.user,
            notification_type_code='adelanto_approved',
            related_object=adelanto,
            action_url='/payroll/admin/adelantos/',  # ✅ URL CORRECTA
            priority='normal',
            **template_vars
        )
    
    @staticmethod
    def notify_adelanto_processed(payroll_rubro):
        """Notificar que un adelanto fue descontado"""
        
        template_vars = {
            'amount': f"{payroll_rubro.monto:,.2f}",
            'adelanto_date': payroll_rubro.fecha_adelanto.strftime('%d/%m/%Y') if payroll_rubro.fecha_adelanto else 'N/A',
        }
        
        NotificationService.create_notification(
            recipient=payroll_rubro.payroll.employee.user,
            notification_type_code='adelanto_processed',
            related_object=payroll_rubro.payroll,
            action_url=f'/payroll/admin/nominas/{payroll_rubro.payroll.id}/',  # ✅ URL CORRECTA
            priority='normal',
            **template_vars
        )
    
    @staticmethod
    def get_dashboard_notifications(user):
        """Obtener notificaciones para el dashboard - TODAS LAS URLS CORREGIDAS"""
        
        try:
            # Verificar si el usuario tiene perfil de empleado
            if not hasattr(user, 'employee_profile'):
                logger.warning(f"Usuario {user.username} no tiene perfil de empleado")
                return {
                    'success': True,
                    'notifications': [],
                    'pending_actions': 0,
                    'total_unread': 0
                }
            
            employee = user.employee_profile
            pending_actions = 0
            notifications_data = []
            
            # 1. Solicitudes de licencia pendientes (para supervisores)
            if user.has_perm('leaves.change_leaverequest'):
                try:
                    # Obtener empleados bajo supervisión
                    subordinates = Employee.objects.filter(
                        Q(supervisor=employee) |
                        Q(department=employee.department, user__user_type='employee')
                    ).filter(status='active')
                    
                    pending_leaves = LeaveRequest.objects.filter(
                        employee__in=subordinates,
                        status='pending'
                    ).count()
                    
                    if pending_leaves > 0:
                        pending_actions += pending_leaves
                        notifications_data.append({
                            'type': 'leave_requests',
                            'title': f'{pending_leaves} Solicitud(es) de Licencia Pendiente(s)',
                            'message': 'Hay solicitudes de licencia esperando tu aprobación',
                            'icon': 'fa-calendar-alt',
                            'color': 'warning',
                            'count': pending_leaves,
                            'url': '/leaves/requests/?status=pending',  # ✅ URL CORRECTA
                            'priority': 'normal',
                            'time_ago': 'Pendiente'
                        })
                except Exception as e:
                    logger.error(f"Error obteniendo solicitudes pendientes: {e}")
            
            # 2. Nóminas pendientes de pago (para administradores)
            if user.has_perm('payroll.change_payroll'):
                try:
                    unpaid_payrolls = Payroll.objects.filter(is_paid=False).count()
                    
                    if unpaid_payrolls > 0:
                        pending_actions += unpaid_payrolls
                        notifications_data.append({
                            'type': 'unpaid_payrolls',
                            'title': f'{unpaid_payrolls} Nómina(s) Pendiente(s) de Pago',
                            'message': 'Hay nóminas que requieren procesamiento de pago',
                            'icon': 'fa-money-bill-wave',
                            'color': 'danger',
                            'count': unpaid_payrolls,
                            'url': '/payroll/admin/nominas/?status=unpaid',  # ✅ URL CORRECTA
                            'priority': 'high',
                            'time_ago': 'Pendiente'
                        })
                except Exception as e:
                    logger.error(f"Error obteniendo nóminas pendientes: {e}")
            
            # 3. Adelantos pendientes de descuento
            try:
                adelantos_pendientes = AdelantoQuincena.objects.filter(
                    employee=employee,
                    is_descontado=False
                ).count()
                
                if adelantos_pendientes > 0:
                    notifications_data.append({
                        'type': 'pending_adelantos',
                        'title': f'{adelantos_pendientes} Adelanto(s) Pendiente(s)',
                        'message': 'Tienes adelantos que serán descontados en la próxima nómina',
                        'icon': 'fa-hand-holding-usd',
                        'color': 'info',
                        'count': adelantos_pendientes,
                        'url': '/payroll/admin/adelantos/',  # ✅ URL CORRECTA
                        'priority': 'normal',
                        'time_ago': 'Por descontar'
                    })
            except Exception as e:
                logger.error(f"Error obteniendo adelantos pendientes: {e}")
            
            # 4. Notificaciones del sistema recientes (máximo 5)
            try:
                recent_notifications = Notification.objects.for_user(user)\
                    .unread()\
                    .not_expired()\
                    .select_related('notification_type')\
                    .order_by('-created_at')[:5]
                
                for notification in recent_notifications:
                    notifications_data.append({
                        'type': 'system_notification',
                        'title': notification.title,
                        'message': notification.message[:100] + '...' if len(notification.message) > 100 else notification.message,
                        'icon': notification.get_icon(),
                        'color': notification.get_color(),
                        'url': notification.action_url or f'/notifications/{notification.id}/',
                        'priority': notification.priority,
                        'time_ago': notification.get_time_ago(),
                        'id': notification.id
                    })
            except Exception as e:
                logger.error(f"Error obteniendo notificaciones del sistema: {e}")
            
            total_unread = Notification.objects.for_user(user).unread().not_expired().count()
            
            return {
                'success': True,
                'notifications': notifications_data,
                'pending_actions': pending_actions,
                'total_unread': total_unread
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo notificaciones del dashboard: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'notifications': [],
                'pending_actions': 0,
                'total_unread': 0
            }
    
    @staticmethod
    def create_system_notification(recipient, title, message, priority='normal', 
                                 action_url=None, expires_in_days=None):
        """Crear notificación general del sistema"""
        
        return NotificationService.create_notification(
            recipient=recipient,
            notification_type_code='system_general',
            title=title,
            message=message,
            priority=priority,
            action_url=action_url,
            expires_in_days=expires_in_days
        )
    
    @staticmethod
    def broadcast_notification(users_queryset, title, message, priority='normal', 
                             action_url=None, expires_in_days=None):
        """Enviar notificación a múltiples usuarios"""
        
        notifications_created = []
        
        for user in users_queryset:
            notification = NotificationService.create_system_notification(
                recipient=user,
                title=title,
                message=message,
                priority=priority,
                action_url=action_url,
                expires_in_days=expires_in_days
            )
            
            if notification:
                notifications_created.append(notification)
        
        logger.info(f"Notificación broadcast enviada a {len(notifications_created)} usuarios: {title}")
        return notifications_created
    
    @staticmethod
    def cleanup_expired_notifications():
        """Limpiar notificaciones expiradas (para ejecutar en cron job)"""
        
        expired_count = Notification.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]
        
        logger.info(f"Se eliminaron {expired_count} notificaciones expiradas")
        return expired_count
    
    @staticmethod
    def get_user_unread_count(user):
        """Obtener contador de notificaciones no leídas para un usuario"""
        
        return Notification.objects.for_user(user).unread().not_expired().count()
    
    @staticmethod
    def mark_notification_as_read(notification_id, user):
        """Marcar una notificación específica como leída"""
        
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=user
            )
            notification.mark_as_read()
            return True
            
        except Notification.DoesNotExist:
            logger.warning(f"Notificación {notification_id} no encontrada para usuario {user.username}")
            return False
    
    @staticmethod
    def mark_all_as_read(user):
        """Marcar todas las notificaciones de un usuario como leídas"""
        
        updated_count = Notification.objects.for_user(user).unread().update(
            status='read',
            read_at=timezone.now()
        )
        
        logger.info(f"Se marcaron {updated_count} notificaciones como leídas para {user.username}")
        return updated_count