# core/tasks/views/employee.py - CORREGIDO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.urls import reverse_lazy
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from core.employees.models import Employee
from ..models import Task, TaskAssignment, TaskProgress, TaskComment
from core.tasks.forms.TaskForm import TaskProgressForm, TaskCommentForm


class EmployeeTaskRequiredMixin:
    """Mixin que verifica que el usuario sea empleado"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        
        if not hasattr(request.user, 'employee_profile'):
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('users:login')
        
        return super().dispatch(request, *args, **kwargs)


class EmployeeTaskDashboardView(EmployeeTaskRequiredMixin, LoginRequiredMixin, ListView):
    """Dashboard de tareas para empleados"""
    template_name = 'pages/employee/tasks/dashboard.html'
    context_object_name = 'assignments'
    paginate_by = 10
    
    def get_queryset(self):
        employee = self.request.user.employee_profile
        return TaskAssignment.objects.filter(
            employee=employee
        ).select_related('task__category', 'task__supervisor__user').order_by('-assigned_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        # Estadísticas del empleado
        assignments_stats = TaskAssignment.objects.filter(employee=employee).aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            in_progress=Count('id', filter=Q(status='in_progress')),
            completed=Count('id', filter=Q(status='completed')),
            total_hours=Sum('hours_worked') or 0,
            total_units=Sum('units_completed') or 0
        )
        
        # Tareas urgentes asignadas
        urgent_assignments = TaskAssignment.objects.filter(
            employee=employee,
            status__in=['pending', 'accepted', 'in_progress'],
            task__priority='urgent'
        ).select_related('task').order_by('task__end_date')[:3]
        
        # Actividad reciente del empleado
        recent_progress = TaskProgress.objects.filter(
            assignment__employee=employee
        ).select_related('assignment__task').order_by('-timestamp')[:5]
        
        # Tareas próximas a vencer (próximas 24 horas)
        upcoming_deadline = TaskAssignment.objects.filter(
            employee=employee,
            status__in=['pending', 'accepted', 'in_progress'],
            task__end_date__range=[
                timezone.now(),
                timezone.now() + timedelta(hours=24)
            ]
        ).select_related('task').order_by('task__end_date')
        
        # Earnings del mes (calculado basado en tareas completadas)
        current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_earnings = 0
        completed_assignments_this_month = TaskAssignment.objects.filter(
            employee=employee,
            status='completed',
            completed_at__gte=current_month_start
        )
        
        for assignment in completed_assignments_this_month:
            monthly_earnings += assignment.calculated_payment
        
        context.update({
            'employee': employee,
            'assignments_stats': assignments_stats,
            'urgent_assignments': urgent_assignments,
            'recent_progress': recent_progress,
            'upcoming_deadline': upcoming_deadline,
            'monthly_earnings': monthly_earnings,
        })
        
        return context


class EmployeeTaskListView(EmployeeTaskRequiredMixin, LoginRequiredMixin, ListView):
    """Lista de todas las tareas asignadas al empleado"""
    model = TaskAssignment
    template_name = 'pages/employee/tasks/task_list.html'
    context_object_name = 'assignments'
    paginate_by = 20
    
    def get_queryset(self):
        employee = self.request.user.employee_profile
        queryset = TaskAssignment.objects.filter(
            employee=employee
        ).select_related('task__category', 'task__supervisor__user').order_by('-assigned_at')
        
        # Filtros
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(task__priority=priority)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(task__title__icontains=search) |
                Q(task__description__icontains=search) |
                Q(task__location__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = TaskAssignment.ASSIGNMENT_STATUS_CHOICES
        context['priority_choices'] = Task.PRIORITY_CHOICES
        context['current_filters'] = {
            'status': self.request.GET.get('status', ''),
            'priority': self.request.GET.get('priority', ''),
            'search': self.request.GET.get('search', ''),
        }
        return context


class EmployeeTaskDetailView(EmployeeTaskRequiredMixin, LoginRequiredMixin, DetailView):
    """Vista detallada de una tarea asignada"""
    model = TaskAssignment
    template_name = 'pages/employee/tasks/task_detail.html'
    context_object_name = 'assignment'
    
    def get_queryset(self):
        return TaskAssignment.objects.filter(
            employee=self.request.user.employee_profile
        ).select_related(
            'task__category',
            'task__supervisor__user',
            'employee__user'
        ).prefetch_related('progress_reports')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Reportes de progreso
        progress_reports = self.object.progress_reports.order_by('-timestamp')
        
        # Otros empleados asignados a la misma tarea
        other_assignments = TaskAssignment.objects.filter(
            task=self.object.task
        ).exclude(
            employee=self.request.user.employee_profile
        ).select_related('employee__user')
        
        # Comentarios de la tarea
        comments = TaskComment.objects.filter(
            task=self.object.task
        ).filter(
            Q(is_private=False) | Q(author=self.request.user.employee_profile)
        ).select_related('author__user').order_by('-timestamp')
        
        # Formularios
        progress_form = TaskProgressForm(assignment=self.object)
        comment_form = TaskCommentForm(author=self.request.user.employee_profile)
        
        # Calcular pago estimado
        estimated_payment = self.object.calculated_payment
        
        # Verificar si puede iniciar trabajo (GPS/ubicación)
        can_start_work = True  # Implementar lógica de geolocalización si es necesario
        
        context.update({
            'progress_reports': progress_reports,
            'other_assignments': other_assignments,
            'comments': comments,
            'progress_form': progress_form,
            'comment_form': comment_form,
            'estimated_payment': estimated_payment,
            'can_start_work': can_start_work,
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Manejar las acciones POST del empleado - CORREGIDO"""
        self.object = self.get_object()
        assignment = self.object
        
        # DEBUG: Imprimir información del POST
        print("=" * 50)
        print("🔍 DEBUG EmployeeTaskDetailView POST")
        print("=" * 50)
        print(f"POST data: {request.POST}")
        print(f"Assignment: {assignment.task.title} - {assignment.employee.user.get_full_name()}")
        print(f"Current status: {assignment.status}")
        print(f"User: {request.user.username}")
        
        try:
            # Aceptar tarea
            if 'accept_task' in request.POST:
                print("✅ PROCESANDO ACEPTACIÓN DE TAREA")
                if assignment.status == 'pending':
                    with transaction.atomic():
                        assignment.status = 'accepted'
                        assignment.accepted_at = timezone.now()
                        assignment.save()
                        print(f"✅ Tarea aceptada: {assignment.task.title}")
                    
                    messages.success(request, '✅ Tarea aceptada exitosamente.')
                else:
                    messages.warning(request, 'Esta tarea ya ha sido aceptada.')
                
                return redirect('tasks:employee_task_detail', pk=assignment.pk)
            
            # Rechazar tarea
            elif 'reject_task' in request.POST:
                print("❌ PROCESANDO RECHAZO DE TAREA")
                if assignment.status == 'pending':
                    reason = request.POST.get('reject_reason', '').strip()
                    with transaction.atomic():
                        assignment.status = 'rejected'
                        if reason:
                            assignment.employee_notes = f"Razón del rechazo: {reason}"
                        assignment.save()
                        print(f"❌ Tarea rechazada: {assignment.task.title} - Motivo: {reason}")
                    
                    messages.info(request, '❌ Tarea rechazada.')
                    return redirect('tasks:employee_task_list')
                else:
                    messages.warning(request, 'No se puede rechazar esta tarea.')
            
            # Iniciar trabajo
            elif 'start_work' in request.POST:
                print("▶️ PROCESANDO INICIO DE TRABAJO")
                if assignment.status == 'accepted':
                    with transaction.atomic():
                        assignment.status = 'in_progress'
                        assignment.started_at = timezone.now()
                        assignment.save()
                        
                        # Actualizar estado de la tarea principal
                        if assignment.task.status == 'assigned':
                            assignment.task.status = 'in_progress'
                            assignment.task.save()
                            print(f"📝 Estado de tarea principal cambiado a: {assignment.task.status}")
                        
                        print(f"▶️ Trabajo iniciado: {assignment.task.title}")
                    
                    messages.success(request, '🚀 Trabajo iniciado. ¡Mucho éxito!')
                else:
                    messages.warning(request, 'Solo puedes iniciar tareas que hayas aceptado.')
                
                return redirect('tasks:employee_task_detail', pk=assignment.pk)
            
            # Pausar trabajo
            elif 'pause_work' in request.POST:
                print("⏸️ PROCESANDO PAUSA DE TRABAJO")
                if assignment.status == 'in_progress':
                    with transaction.atomic():
                        assignment.status = 'accepted'  # Volver a aceptado para poder reanudar
                        assignment.save()
                        print(f"⏸️ Trabajo pausado: {assignment.task.title}")
                    
                    messages.info(request, '⏸️ Trabajo pausado. Puedes reanudarlo cuando quieras.')
                else:
                    messages.warning(request, 'Solo puedes pausar tareas en progreso.')
                
                return redirect('tasks:employee_task_detail', pk=assignment.pk)
            
            # Reportar progreso
            elif 'report_progress' in request.POST:
                print("📊 PROCESANDO REPORTE DE PROGRESO")
                if assignment.status != 'in_progress':
                    messages.error(request, 'Solo puedes reportar progreso en tareas en progreso.')
                    return redirect('tasks:employee_task_detail', pk=assignment.pk)
                
                progress_form = TaskProgressForm(
                    request.POST,
                    request.FILES,
                    assignment=assignment
                )
                
                if progress_form.is_valid():
                    with transaction.atomic():
                        progress = progress_form.save(commit=False)
                        progress.assignment = assignment
                        
                        # Capturar ubicación si está disponible
                        lat = request.POST.get('latitude')
                        lng = request.POST.get('longitude')
                        if lat and lng:
                            try:
                                progress.location_lat = Decimal(str(lat))
                                progress.location_lng = Decimal(str(lng))
                                print(f"📍 Ubicación capturada: {lat}, {lng}")
                            except (ValueError, TypeError) as e:
                                print(f"⚠️ Error capturando ubicación: {e}")
                        
                        progress.save()
                        print(f"📊 Progreso guardado: ID {progress.id}")
                        
                        # CORREGIDO: Actualizar totales del assignment correctamente
                        hours_to_add = progress.hours_worked_session or Decimal('0.00')
                        units_to_add = progress.units_completed_session or 0
                        
                        assignment.hours_worked = (assignment.hours_worked or Decimal('0.00')) + hours_to_add
                        assignment.units_completed = (assignment.units_completed or 0) + units_to_add
                        assignment.save()
                        
                        print(f"📊 Totales actualizados: {assignment.hours_worked}h, {assignment.units_completed} unidades")
                    
                    messages.success(request, '📊 Progreso reportado exitosamente.')
                    return redirect('tasks:employee_task_detail', pk=assignment.pk)
                else:
                    print(f"❌ Error en formulario de progreso: {progress_form.errors}")
                    for field, errors in progress_form.errors.items():
                        for error in errors:
                            messages.error(request, f'{field}: {error}')
            
            # Marcar como completado
            elif 'complete_task' in request.POST:
                print("✅ PROCESANDO FINALIZACIÓN DE TAREA")
                if assignment.status != 'in_progress':
                    messages.warning(request, 'Solo puedes completar tareas que estén en progreso.')
                    return redirect('tasks:employee_task_detail', pk=assignment.pk)
                
                # CORREGIDO: Verificar si hay progreso reportado
                if not assignment.progress_reports.exists():
                    messages.warning(request, 'Debes reportar progreso antes de completar la tarea.')
                    return redirect('tasks:employee_task_detail', pk=assignment.pk)
                
                with transaction.atomic():
                    assignment.status = 'completed'
                    assignment.completed_at = timezone.now()
                    assignment.save()
                    print(f"✅ Asignación completada: {assignment.task.title}")
                    
                    # CORREGIDO: Verificar si todas las asignaciones están completadas
                    task = assignment.task
                    total_assignments = task.assignments.count()
                    completed_assignments = task.assignments.filter(status='completed').count()
                    
                    # Actualizar porcentaje de progreso de la tarea
                    if total_assignments > 0:
                        progress_percentage = int((completed_assignments / total_assignments) * 100)
                        task.progress_percentage = progress_percentage
                        
                        # Si todas las asignaciones están completadas, marcar la tarea como completada
                        if completed_assignments == total_assignments:
                            task.status = 'completed'
                            task.completed_at = timezone.now()
                            task.progress_percentage = 100
                            print(f"🎉 Tarea principal completada: {task.title}")
                        
                        task.save()
                        print(f"📝 Progreso de tarea actualizado: {progress_percentage}%")
                
                messages.success(request, '🎉 ¡Felicitaciones! Tarea completada exitosamente.')
                return redirect('tasks:employee_task_detail', pk=assignment.pk)
            
            # Agregar comentario
            elif 'add_comment' in request.POST:
                print("💬 PROCESANDO AGREGAR COMENTARIO")
                comment_form = TaskCommentForm(
                    request.POST,
                    request.FILES,
                    author=request.user.employee_profile
                )
                
                if comment_form.is_valid():
                    with transaction.atomic():
                        comment = comment_form.save(commit=False)
                        comment.task = assignment.task
                        comment.author = request.user.employee_profile
                        comment.save()
                        print(f"💬 Comentario agregado por {request.user.employee_profile.user.get_full_name()}")
                    
                    messages.success(request, '💬 Comentario agregado exitosamente.')
                    return redirect('tasks:employee_task_detail', pk=assignment.pk)
                else:
                    print(f"❌ Error en formulario de comentario: {comment_form.errors}")
                    for field, errors in comment_form.errors.items():
                        for error in errors:
                            messages.error(request, f'{field}: {error}')
            
            else:
                messages.warning(request, 'Acción no reconocida.')
                print("⚠️ Acción POST no reconocida")
        
        except Exception as e:
            print(f"❌ Error en EmployeeTaskDetailView POST: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error al procesar la acción: {str(e)}')
        
        print("=" * 50)
        return redirect('tasks:employee_task_detail', pk=assignment.pk)


class EmployeeTaskProgressView(EmployeeTaskRequiredMixin, LoginRequiredMixin, ListView):
    """Vista del historial de progreso del empleado"""
    model = TaskProgress
    template_name = 'pages/employee/tasks/progress_history.html'
    context_object_name = 'progress_reports'
    paginate_by = 20
    
    def get_queryset(self):
        employee = self.request.user.employee_profile
        return TaskProgress.objects.filter(
            assignment__employee=employee
        ).select_related('assignment__task').order_by('-timestamp')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        # Estadísticas de progreso
        progress_stats = TaskProgress.objects.filter(
            assignment__employee=employee
        ).aggregate(
            total_sessions=Count('id'),
            total_hours=Sum('hours_worked_session') or 0,
            total_units=Sum('units_completed_session') or 0
        )
        
        context['progress_stats'] = progress_stats
        return context


# APIs y funciones auxiliares
@login_required
def employee_task_stats_api(request):
    """API para estadísticas de tareas del empleado"""
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    employee = request.user.employee_profile
    
    # Estadísticas por estado
    status_stats = TaskAssignment.objects.filter(employee=employee).values('status').annotate(
        count=Count('id')
    )
    
    # Productividad semanal (últimas 4 semanas)
    weeks_data = []
    for i in range(4):
        week_start = timezone.now() - timedelta(weeks=i+1)
        week_end = timezone.now() - timedelta(weeks=i)
        
        completed = TaskAssignment.objects.filter(
            employee=employee,
            status='completed',
            completed_at__range=[week_start, week_end]
        ).count()
        
        hours_worked = TaskProgress.objects.filter(
            assignment__employee=employee,
            timestamp__range=[week_start, week_end]
        ).aggregate(Sum('hours_worked_session'))['hours_worked_session__sum'] or 0
        
        weeks_data.append({
            'week': f'Semana {4-i}',
            'completed': completed,
            'hours': float(hours_worked)
        })
    
    # Distribución por categoría
    category_stats = TaskAssignment.objects.filter(employee=employee).values(
        'task__category__name', 'task__category__color'
    ).annotate(count=Count('id'))
    
    # Earnings por mes (últimos 6 meses)
    earnings_data = []
    for i in range(6):
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30*i)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_end = month_end - timedelta(days=month_end.day)
        
        completed_assignments = TaskAssignment.objects.filter(
            employee=employee,
            status='completed',
            completed_at__range=[month_start, month_end]
        )
        
        month_earnings = sum(assignment.calculated_payment for assignment in completed_assignments)
        
        earnings_data.append({
            'month': month_start.strftime('%B %Y'),
            'earnings': float(month_earnings)
        })
    
    return JsonResponse({
        'status_stats': list(status_stats),
        'productivity': weeks_data,
        'category_stats': list(category_stats),
        'earnings': list(reversed(earnings_data))
    })


@login_required
def task_location_api(request, assignment_id):
    """API para obtener ubicación de una tarea (para mapas)"""
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        assignment = TaskAssignment.objects.get(
            id=assignment_id,
            employee=request.user.employee_profile
        )
        
        # Obtener progreso con ubicación
        progress_with_location = TaskProgress.objects.filter(
            assignment=assignment,
            location_lat__isnull=False,
            location_lng__isnull=False
        ).values('location_lat', 'location_lng', 'timestamp', 'progress_description')
        
        return JsonResponse({
            'task_location': assignment.task.location,
            'progress_locations': list(progress_with_location)
        })
        
    except TaskAssignment.DoesNotExist:
        return JsonResponse({'error': 'Assignment not found'}, status=404)


@login_required
def start_work_session(request):
    """API para iniciar una sesión de trabajo con geolocalización"""
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        assignment_id = request.POST.get('assignment_id')
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        try:
            assignment = TaskAssignment.objects.get(
                id=assignment_id,
                employee=request.user.employee_profile
            )
            
            if assignment.status != 'in_progress':
                return JsonResponse({'error': 'Task must be in progress'}, status=400)
            
            # Crear registro de inicio de sesión
            session_data = {
                'assignment_id': assignment_id,
                'start_time': timezone.now().isoformat(),
                'start_location': {
                    'lat': latitude,
                    'lng': longitude
                } if latitude and longitude else None
            }
            
            # En una implementación real, podrías almacenar esto en Redis o base de datos
            request.session[f'work_session_{assignment_id}'] = session_data
            
            return JsonResponse({
                'success': True,
                'message': 'Sesión de trabajo iniciada',
                'session_id': f'work_session_{assignment_id}'
            })
            
        except TaskAssignment.DoesNotExist:
            return JsonResponse({'error': 'Assignment not found'}, status=404)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def end_work_session(request):
    """API para finalizar una sesión de trabajo"""
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        assignment_id = request.POST.get('assignment_id')
        
        try:
            session_key = f'work_session_{assignment_id}'
            session_data = request.session.get(session_key)
            
            if not session_data:
                return JsonResponse({'error': 'No active session found'}, status=400)
            
            # Calcular duración de la sesión
            start_time = timezone.datetime.fromisoformat(session_data['start_time'])
            end_time = timezone.now()
            duration = end_time - start_time
            hours_worked = duration.total_seconds() / 3600
            
            # Limpiar la sesión
            del request.session[session_key]
            
            return JsonResponse({
                'success': True,
                'duration_hours': round(hours_worked, 2),
                'message': f'Sesión finalizada. Trabajaste {round(hours_worked, 2)} horas.'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def employee_task_calendar_api(request):
    """API para el calendario de tareas del empleado"""
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    employee = request.user.employee_profile
    
    # Obtener tareas del mes actual
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    start_date = timezone.datetime(year, month, 1)
    if month == 12:
        end_date = timezone.datetime(year + 1, 1, 1)
    else:
        end_date = timezone.datetime(year, month + 1, 1)
    
    assignments = TaskAssignment.objects.filter(
        employee=employee,
        task__start_date__range=[start_date, end_date]
    ).select_related('task__category')
    
    events = []
    for assignment in assignments:
        task = assignment.task
        events.append({
            'id': assignment.id,
            'title': task.title,
            'start': task.start_date.isoformat(),
            'end': task.end_date.isoformat(),
            'color': task.category.color if task.category else '#6B7280',
            'status': assignment.status,
            'priority': task.priority,
            'location': task.location,
            'payment': float(assignment.calculated_payment)
        })
    
    return JsonResponse({'events': events})