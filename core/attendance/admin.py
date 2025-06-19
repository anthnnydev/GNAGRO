from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    WorkSchedule, 
    EmployeeSchedule, 
    Holiday, 
    AttendanceRule, 
    Attendance, 
    AttendanceCorrection, 
    AttendanceSummary
)


@admin.register(WorkSchedule)
class WorkScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'schedule_type', 
        'start_time', 
        'end_time', 
        'weekly_hours',
        'get_working_days',
        'late_tolerance',
        'is_active'
    ]
    list_filter = [
        'schedule_type', 
        'is_active', 
        'weekly_hours',
        'monday',
        'tuesday',
        'wednesday',
        'thursday',
        'friday',
        'saturday',
        'sunday'
    ]
    search_fields = ['name']
    ordering = ['name']
    
    fieldsets = (
        ('Información General', {
            'fields': ('name', 'schedule_type', 'is_active')
        }),
        ('Horarios', {
            'fields': ('start_time', 'end_time', 'break_duration', 'weekly_hours')
        }),
        ('Configuración', {
            'fields': ('late_tolerance',)
        }),
        ('Días de la Semana', {
            'fields': (
                ('monday', 'tuesday', 'wednesday'),
                ('thursday', 'friday', 'saturday', 'sunday')
            )
        }),
    )
    
    def get_working_days(self, obj):
        days = obj.working_days
        if len(days) > 3:
            return f"{', '.join(days[:3])}... ({len(days)} días)"
        return ', '.join(days)
    get_working_days.short_description = 'Días Laborales'
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            employee_count=Count('employee_assignments')
        )


@admin.register(EmployeeSchedule)
class EmployeeScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'employee',
        'schedule', 
        'start_date', 
        'end_date', 
        'is_active',
        'created_at'
    ]
    list_filter = [
        'is_active',
        'start_date',
        'end_date',
        'schedule__schedule_type'
    ]
    search_fields = [
        'employee__first_name',
        'employee__last_name',
        'employee__employee_number',
        'schedule__name'
    ]
    date_hierarchy = 'start_date'
    ordering = ['-start_date']
    
    fieldsets = (
        ('Asignación', {
            'fields': ('employee', 'schedule')
        }),
        ('Vigencia', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('Observaciones', {
            'fields': ('notes',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('employee', 'schedule')


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'date',
        'is_recurring',
        'is_paid',
        'is_active'
    ]
    list_filter = [
        'is_recurring',
        'is_paid',
        'is_active',
        'date'
    ]
    search_fields = ['name', 'description']
    date_hierarchy = 'date'
    ordering = ['date']
    
    fieldsets = (
        ('Información del Feriado', {
            'fields': ('name', 'date', 'description')
        }),
        ('Configuración', {
            'fields': ('is_recurring', 'is_paid', 'is_active')
        }),
    )


@admin.register(AttendanceRule)
class AttendanceRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'late_threshold',
        'overtime_threshold',
        'overtime_multiplier',
        'max_consecutive_absences',
        'require_justification',
        'is_active'
    ]
    list_filter = [
        'is_active',
        'require_justification',
        'late_threshold',
        'overtime_threshold'
    ]
    search_fields = ['name']
    ordering = ['name']
    
    fieldsets = (
        ('Información General', {
            'fields': ('name', 'is_active')
        }),
        ('Reglas de Tardanza', {
            'fields': ('late_threshold',)
        }),
        ('Reglas de Horas Extras', {
            'fields': ('overtime_threshold', 'overtime_multiplier')
        }),
        ('Reglas de Ausencias', {
            'fields': ('max_consecutive_absences', 'require_justification')
        }),
    )


class AttendanceCorrectionInline(admin.TabularInline):
    model = AttendanceCorrection
    extra = 0
    readonly_fields = ['created_at', 'approved_at']
    fields = [
        'correction_type',
        'requested_by',
        'reason',
        'status',
        'approved_by',
        'created_at'
    ]


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = [
        'employee',
        'date',
        'status',
        'clock_in',
        'clock_out',
        'total_hours',
        'get_late_status',
        'is_justified'
    ]
    list_filter = [
        'status',
        'is_late',
        'early_departure',
        'is_justified',
        'date',
        'schedule__schedule_type'
    ]
    search_fields = [
        'employee__first_name',
        'employee__last_name',
        'employee__employee_number'
    ]
    date_hierarchy = 'date'
    ordering = ['-date', 'employee__employee_number']
    
    readonly_fields = [
        'total_hours',
        'regular_hours',
        'overtime_hours',
        'is_late',
        'late_minutes',
        'early_departure',
        'early_departure_minutes',
        'worked_time_display',
        'is_complete_day',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('employee', 'date', 'schedule', 'status')
        }),
        ('Horarios', {
            'fields': (
                ('clock_in', 'clock_out'),
                ('break_start', 'break_end'),
                'break_duration'
            )
        }),
        ('Horas Calculadas', {
            'fields': (
                ('total_hours', 'worked_time_display'),
                ('regular_hours', 'overtime_hours'),
                'is_complete_day'
            ),
            'classes': ('collapse',)
        }),
        ('Estado de Asistencia', {
            'fields': (
                ('is_late', 'late_minutes'),
                ('early_departure', 'early_departure_minutes')
            ),
            'classes': ('collapse',)
        }),
        ('Ubicación y Control', {
            'fields': (
                ('clock_in_location', 'clock_out_location'),
                ('clock_in_ip', 'clock_out_ip')
            ),
            'classes': ('collapse',)
        }),
        ('Justificación', {
            'fields': ('is_justified', 'justification', 'approved_by', 'approved_at')
        }),
        ('Observaciones', {
            'fields': ('notes',)
        }),
        ('Auditoría', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [AttendanceCorrectionInline]
    
    def get_late_status(self, obj):
        if obj.is_late:
            return format_html(
                '<span style="color: red;">⚠️ {} min</span>',
                obj.late_minutes
            )
        return format_html('<span style="color: green;">✓</span>')
    get_late_status.short_description = 'Tardanza'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'employee', 
            'schedule', 
            'approved_by', 
            'created_by'
        )
    
    actions = ['mark_as_justified', 'recalculate_hours']
    
    def mark_as_justified(self, request, queryset):
        updated = queryset.update(
            is_justified=True,
            approved_by_id=request.user.employee.id if hasattr(request.user, 'employee') else None,
            approved_at=timezone.now()
        )
        self.message_user(
            request,
            f"{updated} registros marcados como justificados."
        )
    mark_as_justified.short_description = "Marcar como justificado"
    
    def recalculate_hours(self, request, queryset):
        updated = 0
        for attendance in queryset:
            attendance.calculate_hours()
            attendance.save(update_fields=['total_hours', 'regular_hours', 'overtime_hours'])
            updated += 1
        
        self.message_user(
            request,
            f"Horas recalculadas para {updated} registros."
        )
    recalculate_hours.short_description = "Recalcular horas"


@admin.register(AttendanceCorrection)
class AttendanceCorrectionAdmin(admin.ModelAdmin):
    list_display = [
        'attendance',
        'correction_type',
        'requested_by',
        'status',
        'get_status_color',
        'created_at'
    ]
    list_filter = [
        'correction_type',
        'status',
        'created_at',
        'approved_at'
    ]
    search_fields = [
        'attendance__employee__first_name',
        'attendance__employee__last_name',
        'requested_by__first_name',
        'requested_by__last_name'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información de la Corrección', {
            'fields': ('attendance', 'correction_type', 'requested_by', 'reason')
        }),
        ('Valores Originales', {
            'fields': ('original_clock_in', 'original_clock_out', 'original_status'),
            'classes': ('collapse',)
        }),
        ('Valores Corregidos', {
            'fields': ('corrected_clock_in', 'corrected_clock_out', 'corrected_status')
        }),
        ('Aprobación', {
            'fields': ('status', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status_color(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red'
        }
        return format_html(
            '<span style="color: {};">●</span>',
            colors.get(obj.status, 'gray')
        )
    get_status_color.short_description = 'Estado'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'attendance__employee',
            'requested_by',
            'approved_by'
        )
    
    actions = ['approve_corrections', 'reject_corrections']
    
    def approve_corrections(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='approved',
            approved_by_id=request.user.employee.id if hasattr(request.user, 'employee') else None,
            approved_at=timezone.now()
        )
        self.message_user(
            request,
            f"{updated} correcciones aprobadas."
        )
    approve_corrections.short_description = "Aprobar correcciones seleccionadas"
    
    def reject_corrections(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='rejected',
            approved_by_id=request.user.employee.id if hasattr(request.user, 'employee') else None,
            approved_at=timezone.now()
        )
        self.message_user(
            request,
            f"{updated} correcciones rechazadas."
        )
    reject_corrections.short_description = "Rechazar correcciones seleccionadas"


@admin.register(AttendanceSummary)
class AttendanceSummaryAdmin(admin.ModelAdmin):
    list_display = [
        'employee',
        'get_period',
        'total_work_days',
        'days_present',
        'days_absent',
        'attendance_percentage',
        'total_hours',
        'overtime_hours'
    ]
    list_filter = [
        'year',
        'month',
        'attendance_percentage'
    ]
    search_fields = [
        'employee__first_name',
        'employee__last_name',
        'employee__employee_number'
    ]
    ordering = ['-year', '-month', 'employee__employee_number']
    
    readonly_fields = [
        'get_period',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Información del Empleado', {
            'fields': ('employee', 'get_period')
        }),
        ('Días de Asistencia', {
            'fields': (
                ('total_work_days', 'days_present'),
                ('days_absent', 'days_late'),
                ('days_partial', 'attendance_percentage')
            )
        }),
        ('Horas Trabajadas', {
            'fields': (
                ('total_hours', 'regular_hours'),
                ('overtime_hours', 'total_late_minutes')
            )
        }),
        ('Fechas de Registro', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_period(self, obj):
        return f"{obj.month:02d}/{obj.year}"
    get_period.short_description = 'Período'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('employee')
    
    def has_add_permission(self, request):
        # Los resúmenes se generan automáticamente
        return False


# Configuración adicional del admin
admin.site.site_header = "Sistema de Asistencia"
admin.site.site_title = "Asistencia Admin"
admin.site.index_title = "Panel de Administración - Asistencia"