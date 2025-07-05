# core/tasks/views/supervisor.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.urls import reverse_lazy
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
import csv

from core.employees.models import Employee
from ..models import Task, TaskCategory, TaskAssignment, TaskProgress, TaskComment
from core.tasks.forms.TaskForm import TaskForm, TaskAssignmentForm, TaskCommentForm, TaskSearchForm, TaskCategoryForm


class SupervisorRequiredMixin:
    """Mixin que verifica que el usuario sea supervisor o admin"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        
        if not hasattr(request.user, 'employee_profile'):
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('employees:employee_dashboard')
        
        user_type = getattr(request.user, 'user_type', 'employee')
        if user_type not in ['supervisor', 'admin', 'hr']:
            messages.error(request, 'Solo supervisores y administradores pueden acceder a esta sección.')
            return redirect('employees:employee_dashboard')
        
        return super().dispatch(request, *args, **kwargs)


class SupervisorDashboardView(SupervisorRequiredMixin, LoginRequiredMixin, ListView):
    """Dashboard principal del supervisor"""
    template_name = 'pages/supervisor/dashboard/dashboard.html'
    context_object_name = 'tasks'
    paginate_by = 10
    
    def get_queryset(self):
        supervisor = self.request.user.employee_profile
        return Task.objects.filter(
            supervisor=supervisor
        ).select_related('category').prefetch_related('assigned_employees').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supervisor = self.request.user.employee_profile
        
        # Estadísticas del supervisor
        tasks_stats = Task.objects.filter(supervisor=supervisor).aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(status__in=['assigned', 'in_progress'])),
            completed=Count('id', filter=Q(status='completed')),
            overdue=Count('id', filter=Q(
                status__in=['assigned', 'in_progress'],
                end_date__lt=timezone.now()
            ))
        )
        
        # Empleados bajo supervisión
        subordinates = Employee.objects.filter(
            Q(supervisor=supervisor) |
            Q(department=supervisor.department, user__user_type='employee')
        ).filter(status='active').count()
        
        # Tareas urgentes
        urgent_tasks = Task.objects.filter(
            supervisor=supervisor,
            priority='urgent',
            status__in=['assigned', 'in_progress']
        ).order_by('end_date')[:5]
        
        # Actividad reciente
        recent_activity = TaskProgress.objects.filter(
            assignment__task__supervisor=supervisor
        ).select_related(
            'assignment__employee__user',
            'assignment__task'
        ).order_by('-timestamp')[:10]
        
        context.update({
            'supervisor': supervisor,
            'tasks_stats': tasks_stats,
            'subordinates_count': subordinates,
            'urgent_tasks': urgent_tasks,
            'recent_activity': recent_activity,
        })
        
        return context


class TaskListView(SupervisorRequiredMixin, LoginRequiredMixin, ListView):
    """Lista de todas las tareas del supervisor"""
    model = Task
    template_name = 'pages/supervisor/tasks/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 20
    
    def get_queryset(self):
        supervisor = self.request.user.employee_profile
        queryset = Task.objects.filter(
            supervisor=supervisor
        ).select_related('category').prefetch_related('assigned_employees').order_by('-created_at')
        
        # Aplicar filtros de búsqueda
        form = TaskSearchForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search) |
                    Q(location__icontains=search)
                )
            
            category = form.cleaned_data.get('category')
            if category:
                queryset = queryset.filter(category=category)
            
            status = form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            priority = form.cleaned_data.get('priority')
            if priority:
                queryset = queryset.filter(priority=priority)
            
            date_from = form.cleaned_data.get('date_from')
            if date_from:
                queryset = queryset.filter(start_date__date__gte=date_from)
            
            date_to = form.cleaned_data.get('date_to')
            if date_to:
                queryset = queryset.filter(end_date__date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = TaskSearchForm(self.request.GET)
        return context


class TaskCreateView(SupervisorRequiredMixin, LoginRequiredMixin, CreateView):
    """Vista para crear nuevas tareas"""
    model = Task
    form_class = TaskForm
    template_name = 'pages/supervisor/tasks/task_form.html'
    
    def get_success_url(self):
        return reverse_lazy('tasks:task_assign', kwargs={'pk': self.object.pk})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['supervisor'] = self.request.user.employee_profile
        return kwargs
    
    def form_valid(self, form):
        task = form.save(commit=False)
        task.supervisor = self.request.user.employee_profile
        task.save()
        
        messages.success(
            self.request,
            f'Tarea "{task.title}" creada exitosamente. Ahora asigna empleados.'
        )
        return super().form_valid(form)


class TaskUpdateView(SupervisorRequiredMixin, LoginRequiredMixin, UpdateView):
    """Vista para editar tareas"""
    model = Task
    form_class = TaskForm
    template_name = 'pages/supervisor/tasks/task_form.html'
    
    def get_queryset(self):
        # Solo permitir editar tareas propias
        return Task.objects.filter(supervisor=self.request.user.employee_profile)
    
    def get_success_url(self):
        return reverse_lazy('tasks:task_detail', kwargs={'pk': self.object.pk})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['supervisor'] = self.request.user.employee_profile
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, f'Tarea "{self.object.title}" actualizada exitosamente.')
        return super().form_valid(form)


class TaskDetailView(SupervisorRequiredMixin, LoginRequiredMixin, DetailView):
    """Vista detallada de una tarea"""
    model = Task
    template_name = 'pages/supervisor/tasks/task_detail.html'
    context_object_name = 'task'
    
    def get_queryset(self):
        return Task.objects.filter(
            supervisor=self.request.user.employee_profile
        ).select_related('category', 'supervisor__user').prefetch_related(
            'assignments__employee__user',
            'comments__author__user',
            'assignments__progress_reports'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Asignaciones de la tarea
        assignments = self.object.assignments.select_related(
            'employee__user', 'employee__position'
        ).order_by('-assigned_at')
        
        # Comentarios
        comments = self.object.comments.select_related(
            'author__user'
        ).order_by('-timestamp')
        
        # Progreso general
        total_hours = assignments.aggregate(Sum('hours_worked'))['hours_worked__sum'] or 0
        total_units = assignments.aggregate(Sum('units_completed'))['units_completed__sum'] or 0
        
        # Formulario para nuevos comentarios
        comment_form = TaskCommentForm(author=self.request.user.employee_profile)
        
        context.update({
            'assignments': assignments,
            'comments': comments,
            'total_hours': total_hours,
            'total_units': total_units,
            'comment_form': comment_form,
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Manejar comentarios POST"""
        self.object = self.get_object()
        
        if 'add_comment' in request.POST:
            comment_form = TaskCommentForm(
                request.POST, 
                request.FILES,
                author=request.user.employee_profile
            )
            
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.task = self.object
                comment.author = request.user.employee_profile
                comment.save()
                
                messages.success(request, 'Comentario agregado exitosamente.')
                return redirect('tasks:task_detail', pk=self.object.pk)
        
        return self.get(request, *args, **kwargs)


class TaskAssignView(SupervisorRequiredMixin, LoginRequiredMixin, DetailView):
    """Vista para asignar empleados a una tarea"""
    model = Task
    template_name = 'pages/supervisor/tasks/task_assign.html'
    context_object_name = 'task'
    
    def get_queryset(self):
        return Task.objects.filter(supervisor=self.request.user.employee_profile)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supervisor = self.request.user.employee_profile
        
        # CORREGIDO: Obtener asignaciones en lugar de solo empleados
        task_assignments = TaskAssignment.objects.filter(
            task=self.object
        ).select_related(
            'employee__user', 
            'employee__position', 
            'employee__department'
        ).order_by('-assigned_at')
        
        # Empleados ya asignados (para compatibilidad)
        assigned_employees = Employee.objects.filter(
            id__in=task_assignments.values_list('employee_id', flat=True)
        ).select_related('user', 'position', 'department')
        
        # Empleados disponibles (no asignados ya a esta tarea)
        available_employees = Employee.objects.filter(
            Q(supervisor=supervisor) |
            Q(department=supervisor.department, user__user_type='employee')
        ).filter(status='active').exclude(
            id__in=assigned_employees.values_list('id', flat=True)
        ).select_related('user', 'position', 'department')
        
        # Formulario de asignación
        assignment_form = TaskAssignmentForm(
            task=self.object,
            supervisor=self.request.user.employee_profile
        )
        
        context.update({
            'task_assignments': task_assignments,  # NUEVO: Asignaciones completas
            'assigned_employees': assigned_employees,  # Mantener para compatibilidad
            'assignment_form': assignment_form,
            'available_employees': available_employees,
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # DEBUG: Imprimir toda la información del POST
        print("=" * 50)
        print("🔍 DEBUG TaskAssignView POST")
        print("=" * 50)
        print(f"POST data: {request.POST}")
        print(f"Task: {self.object.title} (ID: {self.object.id})")
        print(f"Task status: {self.object.status}")
        print(f"User: {request.user.username}")
        print(f"Employee profile: {request.user.employee_profile}")
        
        if 'assign_employees' in request.POST:
            print("\n📋 PROCESANDO ASIGNACIÓN DE EMPLEADOS")
            
            # Obtener IDs de empleados seleccionados
            employee_ids = request.POST.getlist('employees')
            print(f"IDs recibidos: {employee_ids}")
            
            if not employee_ids:
                print("❌ ERROR: No se recibieron IDs de empleados")
                messages.error(request, 'No se seleccionaron empleados. Por favor selecciona al menos un empleado.')
                return redirect('tasks:task_assign', pk=self.object.pk)
            
            # Validar que los IDs sean números
            try:
                employee_ids = [int(id_str) for id_str in employee_ids if id_str.isdigit()]
                print(f"IDs convertidos a int: {employee_ids}")
            except ValueError as e:
                print(f"❌ ERROR convirtiendo IDs: {e}")
                messages.error(request, 'Error en los datos de empleados seleccionados.')
                return redirect('tasks:task_assign', pk=self.object.pk)
            
            if not employee_ids:
                print("❌ ERROR: No hay IDs válidos después de la conversión")
                messages.error(request, 'No se seleccionaron empleados válidos.')
                return redirect('tasks:task_assign', pk=self.object.pk)
            
            supervisor = request.user.employee_profile
            print(f"Supervisor: {supervisor}")
            
            # Obtener empleados válidos
            valid_employees = Employee.objects.filter(
                id__in=employee_ids,
                status='active'
            ).filter(
                Q(supervisor=supervisor) |
                Q(department=supervisor.department, user__user_type='employee')
            )
            
            print(f"Empleados válidos encontrados: {valid_employees.count()}")
            for emp in valid_employees:
                print(f"  - {emp.user.get_full_name()} (ID: {emp.id})")
            
            if not valid_employees.exists():
                print("❌ ERROR: No se encontraron empleados válidos")
                messages.error(request, 'No se encontraron empleados válidos para asignar.')
                return redirect('tasks:task_assign', pk=self.object.pk)
            
            # Verificar empleados ya asignados
            already_assigned = []
            new_assignments = []
            
            try:
                with transaction.atomic():
                    for employee in valid_employees:
                        assignment, created = TaskAssignment.objects.get_or_create(
                            task=self.object,
                            employee=employee,
                            defaults={
                                'status': 'pending',
                                'assigned_at': timezone.now()
                            }
                        )
                        
                        if created:
                            new_assignments.append(employee)
                            print(f"✅ NUEVO: Asignado {employee.user.get_full_name()}")
                        else:
                            already_assigned.append(employee)
                            print(f"⚠️ YA EXISTÍA: {employee.user.get_full_name()}")
                    
                    # Actualizar estado de la tarea si es la primera asignación
                    if self.object.status == 'draft' and new_assignments:
                        old_status = self.object.status
                        self.object.status = 'assigned'
                        self.object.save()
                        print(f"📝 Estado de tarea cambiado: {old_status} → {self.object.status}")
                
                # Mensajes de resultado
                if new_assignments:
                    assigned_names = [emp.user.get_full_name() for emp in new_assignments]
                    messages.success(
                        request,
                        f'✅ {len(new_assignments)} empleado(s) asignado(s) exitosamente: {", ".join(assigned_names)}'
                    )
                    print(f"✅ ÉXITO: {len(new_assignments)} nuevas asignaciones")
                
                if already_assigned:
                    already_names = [emp.user.get_full_name() for emp in already_assigned]
                    messages.info(
                        request,
                        f'ℹ️ {len(already_assigned)} empleado(s) ya estaban asignados: {", ".join(already_names)}'
                    )
                    print(f"ℹ️ INFO: {len(already_assigned)} ya asignados")
                
                if not new_assignments and not already_assigned:
                    messages.warning(request, 'No se procesaron asignaciones.')
                    print("⚠️ WARNING: No se procesaron asignaciones")
                
            except Exception as e:
                print(f"❌ EXCEPCIÓN durante la asignación: {e}")
                messages.error(request, f'Error al asignar empleados: {str(e)}')
                return redirect('tasks:task_assign', pk=self.object.pk)
            
            print(f"🔄 Redirigiendo a task_assign con pk={self.object.pk}")
            return redirect('tasks:task_assign', pk=self.object.pk)
        
        elif 'remove_assignment' in request.POST:
            print("\n🗑️ PROCESANDO REMOCIÓN DE ASIGNACIÓN")
            assignment_id = request.POST.get('assignment_id')
            employee_id = request.POST.get('employee_id')  # Fallback
            
            print(f"Assignment ID: {assignment_id}")
            print(f"Employee ID: {employee_id}")
            
            try:
                assignment = None
                
                # Intentar primero con assignment_id
                if assignment_id:
                    try:
                        assignment = TaskAssignment.objects.get(
                            id=assignment_id,
                            task=self.object
                        )
                        print(f"✅ Asignación encontrada por ID: {assignment_id}")
                    except TaskAssignment.DoesNotExist:
                        print(f"❌ No se encontró asignación con ID: {assignment_id}")
                
                # Si no se encontró, intentar con employee_id
                if not assignment and employee_id:
                    try:
                        assignment = TaskAssignment.objects.get(
                            employee_id=employee_id,
                            task=self.object
                        )
                        print(f"✅ Asignación encontrada por Employee ID: {employee_id}")
                    except TaskAssignment.DoesNotExist:
                        print(f"❌ No se encontró asignación para Employee ID: {employee_id}")
                
                if assignment:
                    employee_name = assignment.employee.user.get_full_name()
                    assignment_id_used = assignment.id
                    assignment.delete()
                    
                    messages.success(
                        request,
                        f'Asignación de {employee_name} removida exitosamente.'
                    )
                    print(f"✅ Asignación removida: {employee_name} (Assignment ID: {assignment_id_used})")
                else:
                    print("❌ ERROR: No se pudo encontrar la asignación")
                    messages.error(request, 'No se pudo encontrar la asignación a remover.')
                    
            except Exception as e:
                print(f"❌ ERROR removiendo asignación: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'Error al remover asignación: {str(e)}')
            
            return redirect('tasks:task_assign', pk=self.object.pk)
        
        print("=" * 50)
        return self.get(request, *args, **kwargs)

class TaskDeleteView(SupervisorRequiredMixin, LoginRequiredMixin, DeleteView):
    """Vista para eliminar tareas"""
    model = Task
    template_name = 'pages/supervisor/tasks/task_confirm_delete.html'
    success_url = reverse_lazy('tasks:task_list')
    
    def get_queryset(self):
        return Task.objects.filter(supervisor=self.request.user.employee_profile)
    
    def delete(self, request, *args, **kwargs):
        task = self.get_object()
        
        # Solo permitir eliminar tareas en borrador o que no hayan iniciado
        if task.status not in ['draft', 'assigned']:
            messages.error(
                request,
                'No se pueden eliminar tareas que ya están en progreso o completadas.'
            )
            return redirect('tasks:task_detail', pk=task.pk)
        
        task_title = task.title
        response = super().delete(request, *args, **kwargs)
        
        messages.success(request, f'Tarea "{task_title}" eliminada exitosamente.')
        return response


# Vista para gestionar categorías de tareas
class TaskCategoryListView(SupervisorRequiredMixin, LoginRequiredMixin, ListView):
    """Lista de categorías de tareas"""
    model = TaskCategory
    template_name = 'pages/supervisor/categories/category_list.html'
    context_object_name = 'categories'
    paginate_by = 20
    
    def get_queryset(self):
        return TaskCategory.objects.annotate(
            task_count=Count('tasks')
        ).order_by('name')


class TaskCategoryCreateView(SupervisorRequiredMixin, LoginRequiredMixin, CreateView):
    """Vista para crear categorías de tareas"""
    model = TaskCategory
    form_class = TaskCategoryForm
    template_name = 'pages/supervisor/categories/category_form.html'
    success_url = reverse_lazy('tasks:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Categoría "{form.instance.name}" creada exitosamente.')
        return super().form_valid(form)


class TaskCategoryUpdateView(SupervisorRequiredMixin, LoginRequiredMixin, UpdateView):
    """Vista para editar categorías de tareas"""
    model = TaskCategory
    form_class = TaskCategoryForm
    template_name = 'pages/supervisor/categories/category_form.html'
    success_url = reverse_lazy('tasks:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Categoría "{form.instance.name}" actualizada exitosamente.')
        return super().form_valid(form)


class TaskCategoryDeleteView(SupervisorRequiredMixin, LoginRequiredMixin, DeleteView):
    """Vista para eliminar categorías de tareas"""
    model = TaskCategory
    template_name = 'pages/supervisor/categories/category_confirm_delete.html'
    success_url = reverse_lazy('tasks:category_list')
    
    def delete(self, request, *args, **kwargs):
        category = self.get_object()
        
        # Verificar si hay tareas usando esta categoría
        if category.tasks.exists():
            messages.error(
                request,
                f'No se puede eliminar la categoría "{category.name}" porque tiene tareas asociadas.'
            )
            return redirect('tasks:category_list')
        
        category_name = category.name
        response = super().delete(request, *args, **kwargs)
        
        messages.success(request, f'Categoría "{category_name}" eliminada exitosamente.')
        return response


# APIs y funciones auxiliares
@login_required
def task_stats_api(request):
    """API para estadísticas de tareas del supervisor"""
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    supervisor = request.user.employee_profile
    
    # Estadísticas por estado
    status_stats = Task.objects.filter(supervisor=supervisor).values('status').annotate(
        count=Count('id')
    )
    
    # Estadísticas por categoría
    category_stats = Task.objects.filter(supervisor=supervisor).values(
        'category__name', 'category__color'
    ).annotate(count=Count('id'))
    
    # Productividad semanal (últimas 4 semanas)
    weeks_data = []
    for i in range(4):
        week_start = timezone.now() - timedelta(weeks=i+1)
        week_end = timezone.now() - timedelta(weeks=i)
        
        completed = Task.objects.filter(
            supervisor=supervisor,
            status='completed',
            completed_at__range=[week_start, week_end]
        ).count()
        
        weeks_data.append({
            'week': f'Semana {4-i}',
            'completed': completed
        })
    
    return JsonResponse({
        'status_stats': list(status_stats),
        'category_stats': list(category_stats),
        'productivity': weeks_data
    })


@login_required
def task_assignment_status_update(request, assignment_id):
    """API para actualizar estado de asignación"""
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Verificar permisos de supervisor
    user_type = getattr(request.user, 'user_type', 'employee')
    if user_type not in ['supervisor', 'admin', 'hr']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        assignment = TaskAssignment.objects.get(
            id=assignment_id,
            task__supervisor=request.user.employee_profile
        )
        
        new_status = request.POST.get('status')
        rating = request.POST.get('rating')
        supervisor_notes = request.POST.get('supervisor_notes')
        
        if new_status in [choice[0] for choice in TaskAssignment.ASSIGNMENT_STATUS_CHOICES]:
            assignment.status = new_status
            
            if rating:
                assignment.quality_rating = int(rating)
            
            if supervisor_notes:
                assignment.supervisor_notes = supervisor_notes
            
            assignment.save()
            
            return JsonResponse({'success': True, 'message': 'Estado actualizado exitosamente'})
        else:
            return JsonResponse({'error': 'Estado inválido'}, status=400)
            
    except TaskAssignment.DoesNotExist:
        return JsonResponse({'error': 'Asignación no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def bulk_task_actions(request):
    """Vista para acciones masivas en tareas"""
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Verificar permisos de supervisor
    user_type = getattr(request.user, 'user_type', 'employee')
    if user_type not in ['supervisor', 'admin', 'hr']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        task_ids = request.POST.getlist('task_ids')
        
        supervisor = request.user.employee_profile
        tasks = Task.objects.filter(
            id__in=task_ids,
            supervisor=supervisor
        )
        
        if action == 'delete':
            # Solo eliminar tareas en borrador
            draft_tasks = tasks.filter(status='draft')
            count = draft_tasks.count()
            draft_tasks.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'{count} tarea(s) eliminada(s) exitosamente'
            })
        
        elif action == 'cancel':
            # Cancelar tareas asignadas o en progreso
            cancellable_tasks = tasks.filter(status__in=['assigned', 'in_progress'])
            count = cancellable_tasks.update(status='cancelled')
            
            return JsonResponse({
                'success': True,
                'message': f'{count} tarea(s) cancelada(s) exitosamente'
            })
        
        elif action == 'change_priority':
            new_priority = request.POST.get('priority')
            if new_priority in [choice[0] for choice in Task.PRIORITY_CHOICES]:
                count = tasks.update(priority=new_priority)
                return JsonResponse({
                    'success': True,
                    'message': f'Prioridad cambiada en {count} tarea(s)'
                })
        
        return JsonResponse({'error': 'Acción inválida'}, status=400)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def export_tasks_csv(request):
    """Exportar tareas a CSV"""
    if not hasattr(request.user, 'employee_profile'):
        messages.error(request, 'No tienes permisos para acceder a esta función.')
        return redirect('employees:employee_dashboard')
    
    # Verificar permisos de supervisor
    user_type = getattr(request.user, 'user_type', 'employee')
    if user_type not in ['supervisor', 'admin', 'hr']:
        messages.error(request, 'Solo supervisores pueden exportar tareas.')
        return redirect('employees:employee_dashboard')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tareas_supervisor.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Título', 'Categoría', 'Estado', 'Prioridad', 'Fecha Inicio', 
        'Fecha Fin', 'Ubicación', 'Empleados Asignados', 'Horas Estimadas',
        'Tipo de Pago', 'Progreso %'
    ])
    
    supervisor = request.user.employee_profile
    tasks = Task.objects.filter(supervisor=supervisor).select_related('category').prefetch_related('assigned_employees')
    
    for task in tasks:
        assigned_employees = ', '.join([emp.user.get_full_name() for emp in task.assigned_employees.all()])
        
        writer.writerow([
            task.title,
            task.category.name,
            task.get_status_display(),
            task.get_priority_display(),
            task.start_date.strftime('%d/%m/%Y %H:%M'),
            task.end_date.strftime('%d/%m/%Y %H:%M'),
            task.location or '-',
            assigned_employees or '-',
            task.estimated_hours,
            task.get_payment_display_info(),
            f'{task.progress_percentage}%'
        ])
    
    return response