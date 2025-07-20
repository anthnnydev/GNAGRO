# core/notifications/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from .models import Notification, NotificationType, NotificationPreference
from .services import NotificationService
from core.leaves.models import LeaveRequest
from core.payroll.models import Payroll, AdelantoQuincena
from core.employees.models import Employee

import logging

logger = logging.getLogger(__name__)


@login_required
def notification_list(request):
    """Vista principal de notificaciones del usuario"""
    
    # Filtros
    status_filter = request.GET.get('status', 'all')
    type_filter = request.GET.get('type', 'all')
    page = request.GET.get('page', 1)
    
    # Query base
    notifications = Notification.objects.for_user(request.user).not_expired()
    
    # Aplicar filtros
    if status_filter == 'unread':
        notifications = notifications.unread()
    elif status_filter == 'read':
        notifications = notifications.read()
    
    if type_filter != 'all':
        notifications = notifications.by_type(type_filter)
    
    notifications = notifications.select_related('notification_type').order_by('-created_at')
    
    # Paginación
    paginator = Paginator(notifications, 20)
    page_obj = paginator.get_page(page)
    
    # Estadísticas
    stats = {
        'total': Notification.objects.for_user(request.user).not_expired().count(),
        'unread': Notification.objects.for_user(request.user).unread().not_expired().count(),
        'read': Notification.objects.for_user(request.user).read().not_expired().count(),
    }
    
    # Tipos de notificaciones para filtro
    notification_types = NotificationType.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'stats': stats,
        'notification_types': notification_types,
        'current_filters': {
            'status': status_filter,
            'type': type_filter,
        }
    }
    
    return render(request, 'pages/admin/notifications/list.html', context)


@login_required
def notification_detail(request, pk):
    """Ver detalle de una notificación"""
    notification = get_object_or_404(
        Notification.objects.for_user(request.user), 
        pk=pk
    )
    
    # Marcar como leída automáticamente
    if notification.status == 'unread':
        notification.mark_as_read()
    
    context = {
        'notification': notification,
        'related_object': notification.content_object,
    }
    
    return render(request, 'pages/admin/notifications/detail.html', context)


@login_required
@require_POST
def mark_as_read(request, pk):
    """Marcar notificación como leída (AJAX)"""
    try:
        notification = get_object_or_404(
            Notification.objects.for_user(request.user), 
            pk=pk
        )
        
        notification.mark_as_read()
        
        return JsonResponse({
            'success': True,
            'message': 'Notificación marcada como leída'
        })
        
    except Exception as e:
        logger.error(f"Error marcando notificación como leída: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def mark_all_as_read(request):
    """Marcar todas las notificaciones como leídas (AJAX)"""
    try:
        updated = Notification.objects.for_user(request.user).unread().update(
            status='read',
            read_at=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{updated} notificaciones marcadas como leídas',
            'count': updated
        })
        
    except Exception as e:
        logger.error(f"Error marcando todas las notificaciones como leídas: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def get_unread_count(request):
    """Obtener contador de notificaciones no leídas (AJAX)"""
    try:
        count = Notification.objects.for_user(request.user).unread().not_expired().count()
        
        return JsonResponse({
            'success': True,
            'unread_count': count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def get_recent_notifications(request):
    """Obtener notificaciones recientes para dropdown (AJAX)"""
    try:
        notifications = Notification.objects.for_user(request.user)\
            .not_expired()\
            .select_related('notification_type')\
            .order_by('-created_at')[:10]
        
        notifications_data = []
        for notification in notifications:
            notifications_data.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message[:100] + '...' if len(notification.message) > 100 else notification.message,
                'icon': notification.get_icon(),
                'color': notification.get_color(),
                'time_ago': notification.get_time_ago(),
                'is_read': notification.status == 'read',
                'action_url': notification.action_url or f'/notifications/{notification.id}/',
                'priority': notification.priority,
                'type': notification.notification_type.name,
            })
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'unread_count': Notification.objects.for_user(request.user).unread().count()
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo notificaciones recientes: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def notification_preferences(request):
    """Gestionar preferencias de notificaciones"""
    
    # Obtener o crear preferencias
    prefs, created = NotificationPreference.objects.get_or_create(
        user=request.user
    )
    
    if request.method == 'POST':
        # Actualizar preferencias
        prefs.receive_leave_notifications = request.POST.get('receive_leave_notifications') == 'on'
        prefs.receive_payroll_notifications = request.POST.get('receive_payroll_notifications') == 'on'
        prefs.receive_adelanto_notifications = request.POST.get('receive_adelanto_notifications') == 'on'
        prefs.email_enabled = request.POST.get('email_enabled') == 'on'
        prefs.system_enabled = request.POST.get('system_enabled') == 'on'
        
        # Horas silenciosas
        quiet_start = request.POST.get('quiet_hours_start')
        quiet_end = request.POST.get('quiet_hours_end')
        
        if quiet_start:
            prefs.quiet_hours_start = quiet_start
        if quiet_end:
            prefs.quiet_hours_end = quiet_end
            
        prefs.save()
        
        messages.success(request, 'Preferencias actualizadas correctamente.')
        return redirect('notifications:preferences')
    
    context = {
        'preferences': prefs,
    }
    
    return render(request, 'pages/admin/notifications/preferences.html', context)


@login_required
@require_POST
def delete_notification(request, pk):
    """Eliminar una notificación"""
    try:
        notification = get_object_or_404(
            Notification.objects.for_user(request.user), 
            pk=pk
        )
        
        notification.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Notificación eliminada correctamente'
        })
        
    except Exception as e:
        logger.error(f"Error eliminando notificación: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def dashboard_notifications(request):
    """Notificaciones para el dashboard"""
    try:
        # Solo para usuarios con perfiles de empleado
        if not hasattr(request.user, 'employee_profile'):
            return JsonResponse({
                'success': True,
                'notifications': [],
                'pending_actions': 0
            })
        
        employee = request.user.employee_profile
        pending_actions = 0
        notifications_data = []
        
        # 1. Solicitudes de licencia pendientes (para supervisores)
        if request.user.has_perm('leaves.change_leaverequest'):
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
                    'url': '/leaves/requests/?status=pending',
                    'priority': 'normal'
                })
        
        # 2. Nóminas pendientes de pago (para administradores)
        if request.user.has_perm('payroll.change_payroll'):
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
                    'url': '/payroll/admin/nominas/?status=unpaid',
                    'priority': 'high'
                })
        
        # 3. Adelantos pendientes de descuento
        adelantos_pendientes = AdelantoQuincena.objects.filter(
            employee=employee,
            is_descontado=False
        ).count()
        
        if adelantos_pendientes > 0:
            notifications_data.append({
                'type': 'pending_adelantos',
                'title': f'{adelantos_pendientes} Adelanto(s) Pendiente(s) de Descuento',
                'message': 'Tienes adelantos que serán descontados en la próxima nómina',
                'icon': 'fa-hand-holding-usd',
                'color': 'info',
                'count': adelantos_pendientes,
                'url': '/payroll/my-adelantos/',
                'priority': 'normal'
            })
        
        # 4. Notificaciones del sistema recientes
        recent_notifications = Notification.objects.for_user(request.user)\
            .unread()\
            .not_expired()\
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
                'time_ago': notification.get_time_ago()
            })
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'pending_actions': pending_actions,
            'total_unread': Notification.objects.for_user(request.user).unread().count()
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo notificaciones del dashboard: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)