# core/tasks/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db import models
from django.forms import Textarea
from django.utils import timezone
from datetime import timedelta

from .models import TaskCategory, Task, TaskAssignment, TaskProgress, TaskComment


@admin.register(TaskCategory)
class TaskCategoryAdmin(admin.ModelAdmin):
    """Administración de categorías de tareas"""
    
    list_display = ['name', 'color_preview', 'icon_preview', 'task_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    ordering = ['name']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Apariencia', {
            'fields': ('icon', 'color'),
            'description': 'Configuración visual para la categoría'
        }),
    )
    
    def color_preview(self, obj):
        """Muestra una vista previa del color"""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 50%; display: inline-block;"></div>',
            obj.color
        )
    color_preview.short_description = 'Color'
    
    def icon_preview(self, obj):
        """Muestra una vista previa del icono"""
        return format_html('<i class="{}" style="font-size: 18px;"></i>', obj.icon)
    icon_preview.short_description = 'Icono'
    
    def task_count(self, obj):
        """Muestra el número de tareas en esta categoría"""
        count = obj.tasks.count()
        return format_html(
            '<span style="background: #e3f2fd; padding: 2px 6px; border-radius: 3px;">{}</span>',
            count
        )
    task_count.short_description = 'Tareas'


class TaskAssignmentInline(admin.TabularInline):
    """Inline para asignaciones de tareas"""
    model = TaskAssignment
    extra = 0
    fields = ['employee', 'status', 'assigned_at', 'hours_worked', 'units_completed', 'quality_rating']
    readonly_fields = ['assigned_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('employee__user')


class TaskCommentInline(admin.TabularInline):
    """Inline para comentarios de tareas"""
    model = TaskComment
    extra = 0
    fields = ['author', 'content', 'is_private', 'timestamp']
    readonly_fields = ['timestamp']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author__user')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Administración de tareas"""
    
    list_display = [
        'title', 'category_display', 'supervisor_display', 'status', 'status_display', 
        'priority', 'priority_display', 'payment_info', 'progress_bar', 'assigned_count', 
        'start_date', 'end_date', 'is_overdue_display'
    ]
    
    list_filter = [
        'status', 'priority', 'category', 'payment_type', 
        ('start_date', admin.DateFieldListFilter),
        ('supervisor__department', admin.RelatedFieldListFilter),
        'created_at'
    ]
    
    search_fields = [
        'title', 'description', 'location', 
        'supervisor__user__first_name', 'supervisor__user__last_name',
        'category__name'
    ]
    
    list_editable = ['status', 'priority']
    ordering = ['-created_at']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('title', 'description', 'category', 'supervisor', 'priority', 'status')
        }),
        ('Fechas y Tiempo', {
            'fields': ('start_date', 'end_date', 'estimated_hours'),
            'classes': ('collapse',)
        }),
        ('Ubicación y Pago', {
            'fields': ('location', 'payment_type', 'hourly_rate', 'fixed_amount', 'unit_rate', 'unit_description'),
            'classes': ('collapse',)
        }),
        ('Instrucciones y Referencias', {
            'fields': ('special_instructions', 'reference_image'),
            'classes': ('collapse',)
        }),
        ('Seguimiento', {
            'fields': ('progress_percentage', 'completed_at'),
            'classes': ('collapse',),
            'description': 'Información de seguimiento y finalización'
        })
    )
    
    readonly_fields = ['completed_at']
    
    inlines = [TaskAssignmentInline, TaskCommentInline]
    
    # Filtros personalizados
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category', 'supervisor__user', 'supervisor__department'
        ).prefetch_related('assignments__employee__user')
    
    def category_display(self, obj):
        """Muestra la categoría con color"""
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{}</span>',
            obj.category.color, obj.category.name
        )
    category_display.short_description = 'Categoría'
    
    def supervisor_display(self, obj):
        """Muestra el supervisor"""
        return obj.supervisor.user.get_full_name()
    supervisor_display.short_description = 'Supervisor'
    
    def status_display(self, obj):
        """Muestra el estado con colores"""
        colors = {
            'draft': '#9e9e9e',
            'assigned': '#2196f3',
            'in_progress': '#ff9800',
            'paused': '#795548',
            'completed': '#4caf50',
            'cancelled': '#f44336'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#9e9e9e'), obj.get_status_display()
        )
    status_display.short_description = 'Estado'
    
    def priority_display(self, obj):
        """Muestra la prioridad con colores"""
        colors = {
            'low': '#4caf50',
            'medium': '#ff9800', 
            'high': '#ff5722',
            'urgent': '#f44336'
        }
        icons = {
            'low': '▼',
            'medium': '●',
            'high': '▲',
            'urgent': '🔥'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            colors.get(obj.priority, '#9e9e9e'), 
            icons.get(obj.priority, '●'),
            obj.get_priority_display()
        )
    priority_display.short_description = 'Prioridad'
    
    def payment_info(self, obj):
        """Muestra información de pago"""
        return obj.get_payment_display_info()
    payment_info.short_description = 'Pago'
    
    def progress_bar(self, obj):
        """Muestra barra de progreso"""
        if obj.progress_percentage == 0:
            color = '#e0e0e0'
        elif obj.progress_percentage < 50:
            color = '#ff9800'
        elif obj.progress_percentage < 100:
            color = '#2196f3'
        else:
            color = '#4caf50'
            
        return format_html(
            '<div style="width: 100px; background: #f0f0f0; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; background: {}; height: 20px; display: flex; align-items: center; justify-content: center; color: white; font-size: 11px; font-weight: bold;">'
            '{}%'
            '</div></div>',
            obj.progress_percentage, color, obj.progress_percentage
        )
    progress_bar.short_description = 'Progreso'
    
    def assigned_count(self, obj):
        """Muestra el número de empleados asignados"""
        count = obj.assignments.count()
        if count == 0:
            return format_html('<span style="color: #f44336;">Sin asignar</span>')
        return format_html(
            '<span style="background: #e8f5e8; color: #2e7d32; padding: 2px 6px; border-radius: 3px;">{} empleado{}</span>',
            count, 's' if count != 1 else ''
        )
    assigned_count.short_description = 'Asignados'
    
    def is_overdue_display(self, obj):
        """Muestra si la tarea está vencida"""
        if obj.is_overdue and obj.status not in ['completed', 'cancelled']:
            return format_html(
                '<span style="color: #f44336; font-weight: bold;">⚠️ Vencida</span>'
            )
        # CORREGIDO: Usar timezone.now() en lugar de datetime.now()
        elif obj.end_date <= timezone.now() + timedelta(hours=24) and obj.status not in ['completed', 'cancelled']:
            return format_html(
                '<span style="color: #ff9800; font-weight: bold;">⏰ Próxima</span>'
            )
        return '✅ OK'
    is_overdue_display.short_description = 'Estado Tiempo'
    
    # Acciones personalizadas
    actions = ['mark_as_completed', 'mark_as_cancelled', 'mark_as_in_progress']
    
    def mark_as_completed(self, request, queryset):
        """Marca tareas como completadas"""
        updated = queryset.update(status='completed', completed_at=timezone.now(), progress_percentage=100)
        self.message_user(request, f'{updated} tarea(s) marcada(s) como completada(s).')
    mark_as_completed.short_description = "Marcar como completadas"
    
    def mark_as_cancelled(self, request, queryset):
        """Marca tareas como canceladas"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} tarea(s) cancelada(s).')
    mark_as_cancelled.short_description = "Cancelar tareas seleccionadas"
    
    def mark_as_in_progress(self, request, queryset):
        """Marca tareas como en progreso"""
        updated = queryset.update(status='in_progress')
        self.message_user(request, f'{updated} tarea(s) marcada(s) como en progreso.')
    mark_as_in_progress.short_description = "Marcar como en progreso"
    
    # Configuración de formularios
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 3, 'cols': 80})},
    }


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    """Administración de asignaciones de tareas"""
    
    list_display = [
        'task_link', 'employee_display', 'status', 'status_display', 'hours_worked', 
        'units_completed', 'calculated_payment_display', 'quality_rating', 'quality_rating_display', 
        'assigned_at', 'completion_time'
    ]
    
    list_filter = [
        'status', 'assigned_at', 'completed_at',
        ('task__category', admin.RelatedFieldListFilter),
        ('employee__department', admin.RelatedFieldListFilter),
        'quality_rating'
    ]
    
    search_fields = [
        'task__title', 'employee__user__first_name', 'employee__user__last_name',
        'employee__employee_number'
    ]
    
    list_editable = ['status', 'quality_rating']
    ordering = ['-assigned_at']
    date_hierarchy = 'assigned_at'
    
    readonly_fields = ['assigned_at', 'calculated_payment_display']
    
    fieldsets = (
        ('Asignación', {
            'fields': ('task', 'employee', 'status')
        }),
        ('Fechas', {
            'fields': ('assigned_at', 'accepted_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('Progreso', {
            'fields': ('hours_worked', 'units_completed', 'quality_rating')
        }),
        ('Notas', {
            'fields': ('employee_notes', 'supervisor_notes'),
            'classes': ('collapse',)
        }),
        ('Pago', {
            'fields': ('calculated_payment_display',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'task', 'employee__user', 'task__category'
        )
    
    def task_link(self, obj):
        """Link a la tarea"""
        url = reverse('admin:tasks_task_change', args=[obj.task.pk])
        task_title = str(obj.task.title)  # Convertir a string seguro
        return format_html('<a href="{}">{}</a>', url, task_title)
    task_link.short_description = 'Tarea'
    
    def employee_display(self, obj):
        """Muestra el empleado"""
        full_name = str(obj.employee.user.get_full_name())
        employee_number = str(obj.employee.employee_number)
        return "{} ({})".format(full_name, employee_number)
    employee_display.short_description = 'Empleado'
    
    def status_display(self, obj):
        """Muestra el estado con colores"""
        colors = {
            'pending': '#ff9800',
            'accepted': '#2196f3',
            'in_progress': '#9c27b0',
            'completed': '#4caf50',
            'rejected': '#f44336'
        }
        status_text = str(obj.get_status_display())
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#9e9e9e'), status_text
        )
    status_display.short_description = 'Estado'
    
    def calculated_payment_display(self, obj):
        """Muestra el pago calculado"""
        try:
            payment = obj.calculated_payment
            payment_float = float(payment)
            payment_formatted = "{:.2f}".format(payment_float)
            return format_html(
                '<span style="color: #2e7d32; font-weight: bold;">${}</span>',
                payment_formatted
            )
        except (ValueError, TypeError, AttributeError):
            return format_html('<span style="color: #f44336;">Error</span>')
    calculated_payment_display.short_description = 'Pago Calculado'
    
    def quality_rating_display(self, obj):
        """Muestra la calificación con estrellas"""
        if obj.quality_rating:
            stars = '⭐' * obj.quality_rating + '☆' * (5 - obj.quality_rating)
            return format_html(
                '<span title="Calificación: {}/5">{}</span>',
                obj.quality_rating, stars
            )
        return '-'
    quality_rating_display.short_description = 'Calidad'
    
    def completion_time(self, obj):
        """Tiempo hasta completar"""
        if obj.completed_at and obj.assigned_at:
            delta = obj.completed_at - obj.assigned_at
            days = delta.days
            hours = delta.seconds // 3600
            if days > 0:
                return "{}d {}h".format(days, hours)
            return "{}h".format(hours)
        return '-'
    completion_time.short_description = 'Tiempo Completion'


class TaskProgressInline(admin.TabularInline):
    """Inline para progreso de asignaciones"""
    model = TaskProgress
    extra = 0
    fields = ['timestamp', 'progress_description', 'hours_worked_session', 'units_completed_session']
    readonly_fields = ['timestamp']


@admin.register(TaskProgress)
class TaskProgressAdmin(admin.ModelAdmin):
    """Administración de reportes de progreso"""
    
    list_display = [
        'assignment_display', 'timestamp', 'hours_worked_session', 
        'units_completed_session', 'has_image', 'has_location'
    ]
    
    list_filter = [
        'timestamp', 
        ('assignment__task__category', admin.RelatedFieldListFilter),
        ('assignment__employee__department', admin.RelatedFieldListFilter)
    ]
    
    search_fields = [
        'assignment__task__title', 'assignment__employee__user__first_name',
        'assignment__employee__user__last_name', 'progress_description'
    ]
    
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    readonly_fields = ['timestamp']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('assignment', 'timestamp', 'progress_description')
        }),
        ('Progreso', {
            'fields': ('hours_worked_session', 'units_completed_session')
        }),
        ('Adjuntos', {
            'fields': ('progress_image',),
            'classes': ('collapse',)
        }),
        ('Ubicación', {
            'fields': ('location_lat', 'location_lng'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'assignment__task', 'assignment__employee__user'
        )
    
    def assignment_display(self, obj):
        """Muestra la asignación"""
        task_title = str(obj.assignment.task.title)
        employee_name = str(obj.assignment.employee.user.get_full_name())
        return "{} - {}".format(task_title, employee_name)
    assignment_display.short_description = 'Asignación'
    
    def has_image(self, obj):
        """Indica si tiene imagen"""
        return '📷' if obj.progress_image else '-'
    has_image.short_description = 'Imagen'
    
    def has_location(self, obj):
        """Indica si tiene ubicación GPS"""
        return '📍' if obj.location_lat and obj.location_lng else '-'
    has_location.short_description = 'Ubicación'


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    """Administración de comentarios de tareas"""
    
    list_display = [
        'task_display', 'author_display', 'content_preview', 
        'is_private', 'has_attachment', 'timestamp'
    ]
    
    list_filter = [
        'is_private', 'timestamp',
        ('task__category', admin.RelatedFieldListFilter),
        ('author__department', admin.RelatedFieldListFilter)
    ]
    
    search_fields = [
        'task__title', 'author__user__first_name', 
        'author__user__last_name', 'content'
    ]
    
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    readonly_fields = ['timestamp']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'task', 'author__user'
        )
    
    def task_display(self, obj):
        """Link a la tarea"""
        url = reverse('admin:tasks_task_change', args=[obj.task.pk])
        return format_html('<a href="{}">{}</a>', url, obj.task.title)
    task_display.short_description = 'Tarea'
    
    def author_display(self, obj):
        """Muestra el autor"""
        return obj.author.user.get_full_name()
    author_display.short_description = 'Autor'
    
    def content_preview(self, obj):
        """Vista previa del contenido"""
        preview = obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
        return preview
    content_preview.short_description = 'Contenido'
    
    def has_attachment(self, obj):
        """Indica si tiene archivo adjunto"""
        return '📎' if obj.attachment else '-'
    has_attachment.short_description = 'Adjunto'


# Configuración del sitio admin
admin.site.site_header = "Administración de Tareas Agrícolas"
admin.site.site_title = "Tasks Admin"
admin.site.index_title = "Panel de Administración de Tareas"