# core/employees/views/attendance_ajax.py

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, time, timedelta
import json
import pytz  # AGREGAR ESTA IMPORTACIÓN

def get_client_ip(request):
    """Obtener IP del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_local_now():
    """Obtener fecha/hora actual en zona horaria de Ecuador"""
    ecuador_tz = pytz.timezone('America/Guayaquil')
    return timezone.now().astimezone(ecuador_tz)

def get_local_today():
    """Obtener fecha local de Ecuador"""
    return get_local_now().date()

@login_required
@require_http_methods(["POST"])
@csrf_exempt
def clock_in_api(request):
    """API para marcar entrada"""
    
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    employee = request.user.employee_profile
    today = get_local_today()  # Usar fecha local
    now_local = get_local_now()  # Usar hora local
    
    try:
        data = json.loads(request.body) if request.body else {}
        location_lat = data.get('latitude')
        location_lng = data.get('longitude')
    except json.JSONDecodeError:
        location_lat = location_lng = None
    
    try:
        from core.attendance.models import Attendance, EmployeeSchedule
        
        # Verificar si ya hay registro para hoy
        existing_record = Attendance.objects.filter(
            employee=employee,
            date=today
        ).first()
        
        if existing_record and existing_record.clock_in:
            return JsonResponse({
                'error': 'Ya has marcado entrada hoy',
                'clock_in_time': existing_record.clock_in.strftime('%H:%M:%S')
            }, status=400)
        
        # Obtener horario del empleado
        employee_schedule = EmployeeSchedule.objects.filter(
            employee=employee,
            is_active=True,
            start_date__lte=today,
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        ).select_related('schedule').first()
        
        schedule = employee_schedule.schedule if employee_schedule else None
        
        # Crear o actualizar registro - USAR SOLO LA HORA LOCAL
        local_time_only = now_local.time()
        
        if existing_record:
            existing_record.clock_in = local_time_only
            existing_record.schedule = schedule
            existing_record.clock_in_ip = get_client_ip(request)
            if location_lat and location_lng:
                existing_record.clock_in_location = f"{location_lat},{location_lng}"
            existing_record.save()
            attendance_record = existing_record
        else:
            attendance_record = Attendance.objects.create(
                employee=employee,
                date=today,
                clock_in=local_time_only,
                schedule=schedule,
                clock_in_ip=get_client_ip(request),
                clock_in_location=f"{location_lat},{location_lng}" if location_lat and location_lng else "",
                created_by=request.user
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Entrada registrada exitosamente',
            'clock_in_time': attendance_record.clock_in.strftime('%H:%M:%S'),
            'record_id': attendance_record.id,
            'schedule_name': schedule.name if schedule else 'Sin horario asignado',
            'local_time': now_local.strftime('%H:%M:%S')  # Para debug
        })
        
    except ImportError:
        return JsonResponse({
            'error': 'Sistema de asistencia no disponible'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def clock_out_api(request):
    """API para marcar salida"""
    
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    employee = request.user.employee_profile
    today = get_local_today()  # Usar fecha local
    now_local = get_local_now()  # Usar hora local
    
    try:
        data = json.loads(request.body) if request.body else {}
        location_lat = data.get('latitude')
        location_lng = data.get('longitude')
    except json.JSONDecodeError:
        location_lat = location_lng = None
    
    try:
        from core.attendance.models import Attendance
        
        # Buscar registro del día
        attendance_record = Attendance.objects.filter(
            employee=employee,
            date=today
        ).first()
        
        if not attendance_record or not attendance_record.clock_in:
            return JsonResponse({
                'error': 'No hay entrada registrada para marcar salida'
            }, status=400)
        
        if attendance_record.clock_out:
            return JsonResponse({
                'error': 'Ya has marcado salida hoy',
                'clock_out_time': attendance_record.clock_out.strftime('%H:%M:%S')
            }, status=400)
        
        # Marcar salida - USAR SOLO LA HORA LOCAL
        local_time_only = now_local.time()
        
        attendance_record.clock_out = local_time_only
        attendance_record.clock_out_ip = get_client_ip(request)
        if location_lat and location_lng:
            attendance_record.clock_out_location = f"{location_lat},{location_lng}"
        
        # Finalizar descanso si está activo
        if attendance_record.break_start and not attendance_record.break_end:
            attendance_record.break_end = local_time_only
        
        attendance_record.save()  # Esto triggerea los cálculos automáticos
        
        return JsonResponse({
            'success': True,
            'message': 'Salida registrada exitosamente',
            'clock_out_time': attendance_record.clock_out.strftime('%H:%M:%S'),
            'total_hours': float(attendance_record.total_hours),
            'overtime_hours': float(attendance_record.overtime_hours),
            'status': attendance_record.get_status_display(),
            'local_time': now_local.strftime('%H:%M:%S')  # Para debug
        })
        
    except ImportError:
        return JsonResponse({
            'error': 'Sistema de asistencia no disponible'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def break_start_api(request):
    """API para iniciar descanso"""
    
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    employee = request.user.employee_profile
    today = get_local_today()  # Usar fecha local
    now_local = get_local_now()  # Usar hora local
    
    try:
        data = json.loads(request.body) if request.body else {}
        break_type = data.get('break_type', 'regular')
    except json.JSONDecodeError:
        break_type = 'regular'
    
    try:
        from core.attendance.models import Attendance
        
        # Buscar registro del día
        attendance_record = Attendance.objects.filter(
            employee=employee,
            date=today
        ).first()
        
        if not attendance_record or not attendance_record.clock_in:
            return JsonResponse({
                'error': 'No hay sesión activa'
            }, status=400)
        
        if attendance_record.clock_out:
            return JsonResponse({
                'error': 'Ya has marcado salida hoy'
            }, status=400)
        
        if attendance_record.break_start and not attendance_record.break_end:
            return JsonResponse({
                'error': 'Ya tienes un descanso activo',
                'break_start_time': attendance_record.break_start.strftime('%H:%M:%S')
            }, status=400)
        
        # Iniciar nuevo descanso - USAR SOLO LA HORA LOCAL
        local_time_only = now_local.time()
        
        attendance_record.break_start = local_time_only
        attendance_record.break_end = None  # Limpiar fin de descanso anterior
        attendance_record.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Descanso iniciado',
            'break_start_time': attendance_record.break_start.strftime('%H:%M:%S'),
            'break_type': break_type,
            'local_time': now_local.strftime('%H:%M:%S')  # Para debug
        })
        
    except ImportError:
        return JsonResponse({
            'error': 'Sistema de asistencia no disponible'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def break_end_api(request):
    """API para finalizar descanso"""
    
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    employee = request.user.employee_profile
    today = get_local_today()  # Usar fecha local
    now_local = get_local_now()  # Usar hora local
    
    try:
        from core.attendance.models import Attendance
        
        # Buscar registro del día
        attendance_record = Attendance.objects.filter(
            employee=employee,
            date=today
        ).first()
        
        if not attendance_record or not attendance_record.clock_in:
            return JsonResponse({
                'error': 'No hay sesión activa'
            }, status=400)
        
        if not attendance_record.break_start or attendance_record.break_end:
            return JsonResponse({
                'error': 'No hay descanso activo para finalizar'
            }, status=400)
        
        # Finalizar descanso - USAR SOLO LA HORA LOCAL
        local_time_only = now_local.time()
        
        attendance_record.break_end = local_time_only
        attendance_record.save()
        
        # Calcular duración del descanso
        break_start_dt = datetime.combine(today, attendance_record.break_start)
        break_end_dt = datetime.combine(today, attendance_record.break_end)
        break_duration = break_end_dt - break_start_dt
        
        return JsonResponse({
            'success': True,
            'message': 'Descanso finalizado',
            'break_end_time': attendance_record.break_end.strftime('%H:%M:%S'),
            'break_duration': str(break_duration),
            'local_time': now_local.strftime('%H:%M:%S')  # Para debug
        })
        
    except ImportError:
        return JsonResponse({
            'error': 'Sistema de asistencia no disponible'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)


@login_required
def attendance_status_api(request):
    """API para obtener el estado actual de asistencia"""
    
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'No autorizado'}, status=403)
    
    employee = request.user.employee_profile
    today = get_local_today()  # Usar fecha local
    
    try:
        from core.attendance.models import Attendance, EmployeeSchedule
        
        # Buscar registro del día
        today_record = Attendance.objects.filter(
            employee=employee,
            date=today
        ).first()
        
        # Obtener horario
        employee_schedule = EmployeeSchedule.objects.filter(
            employee=employee,
            is_active=True,
            start_date__lte=today,
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        ).select_related('schedule').first()
        
        schedule = employee_schedule.schedule if employee_schedule else None
        
        status_data = {
            'has_record': today_record is not None,
            'is_working': False,
            'is_on_break': False,
            'clock_in': None,
            'clock_out': None,
            'break_start': None,
            'break_end': None,
            'total_hours': 0.0,
            'schedule': None,
            'current_local_time': get_local_now().strftime('%H:%M:%S')  # Para debug
        }
        
        if today_record:
            status_data.update({
                'is_working': today_record.clock_in and not today_record.clock_out,
                'is_on_break': today_record.break_start and not today_record.break_end,
                'clock_in': today_record.clock_in.strftime('%H:%M:%S') if today_record.clock_in else None,
                'clock_out': today_record.clock_out.strftime('%H:%M:%S') if today_record.clock_out else None,
                'break_start': today_record.break_start.strftime('%H:%M:%S') if today_record.break_start else None,
                'break_end': today_record.break_end.strftime('%H:%M:%S') if today_record.break_end else None,
                'total_hours': float(today_record.total_hours),
                'status': today_record.get_status_display()
            })
        
        if schedule:
            status_data['schedule'] = {
                'name': schedule.name,
                'start_time': schedule.start_time.strftime('%H:%M'),
                'end_time': schedule.end_time.strftime('%H:%M'),
                'daily_hours': schedule.daily_hours
            }
        
        return JsonResponse({
            'success': True,
            'data': status_data
        })
        
    except ImportError:
        return JsonResponse({
            'error': 'Sistema de asistencia no disponible'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)