# core/leaves/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Q
from django.contrib.admin import SimpleListFilter
from django.utils import timezone
from .models import LeaveType, LeaveRequest, LeaveBalance


class LeaveRequestStatusFilter(SimpleListFilter):
    """Filtro personalizado para el estado de las solicitudes"""
    title = 'Estado'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return LeaveRequest.STATUS_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class LeaveRequestYearFilter(SimpleListFilter):
    """Filtro para el año de las solicitudes"""
    title = 'Año'
    parameter_name = 'year'

    def lookups(self, request, model_admin):
        years = LeaveRequest.objects.dates('start_date', 'year')
        return [(year.year, year.year) for year in years]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(start_date__year=self.value())
        return queryset


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'days_allowed', 'is_paid', 
        'requires_approval', 'carry_forward', 'color_display', 'is_active'
    ]
    
    list_filter = ['is_paid', 'requires_approval', 'carry_forward', 'is_active']
    
    search_fields = ['name', 'code', 'description']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'code', 'description')
        }),
        ('Configuración', {
            'fields': (
                'days_allowed', 'is_paid', 'requires_approval', 
                'carry_forward', 'color'
            )
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def color_display(self, obj):
        """Muestra el color como un cuadro de color"""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; border-radius: 3px;"></div>',
            obj.color
        )
    color_display.short_description = 'Color'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = [
        'employee_display', 'leave_type', 'start_date', 'end_date', 
        'days_requested', 'status_display', 'approved_by', 'created_at'
    ]
    
    list_filter = [
        LeaveRequestStatusFilter, 
        LeaveRequestYearFilter,
        'leave_type', 
        'leave_type__requires_approval',
        'created_at'
    ]
    
    search_fields = [
        'employee__first_name', 'employee__last_name', 
        'employee__employee_number', 'reason'
    ]
    
    readonly_fields = ['created_at', 'updated_at', 'days_requested_calculation']
    
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Información de la Solicitud', {
            'fields': ('employee', 'leave_type', 'reason')
        }),
        ('Fechas', {
            'fields': ('start_date', 'end_date', 'days_requested', 'days_requested_calculation')
        }),
        ('Estado y Aprobación', {
            'fields': ('status', 'approved_by', 'approved_date', 'rejection_reason')
        }),
        ('Información del Sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_requests', 'reject_requests', 'cancel_requests']
    
    def employee_display(self, obj):
        """Muestra el empleado con enlace"""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:employees_employee_change', args=[obj.employee.pk]),
            obj.employee.get_full_name() if hasattr(obj.employee, 'get_full_name') else str(obj.employee)
        )
    employee_display.short_description = 'Empleado'
    
    def status_display(self, obj):
        """Muestra el estado con colores"""
        colors = {
            'pending': '#ffc107',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'cancelled': '#6c757d'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#000'),
            obj.get_status_display()
        )
    status_display.short_description = 'Estado'
    
    def days_requested_calculation(self, obj):
        """Muestra el cálculo de días solicitados"""
        if obj.start_date and obj.end_date:
            calculated_days = (obj.end_date - obj.start_date).days + 1
            return f"{calculated_days} días (calculado automáticamente)"
        return "No calculado"
    days_requested_calculation.short_description = 'Cálculo de Días'
    
    def requires_approval(self, obj):
        """Indica si requiere aprobación"""
        return obj.leave_type.requires_approval
    requires_approval.boolean = True
    requires_approval.short_description = 'Requiere Aprobación'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'employee', 'leave_type', 'approved_by'
        )
    
    def approve_requests(self, request, queryset):
        """Acción para aprobar solicitudes"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Intentar obtener el empleado del usuario actual
        approved_by = None
        if hasattr(request.user, 'employee'):
            approved_by = request.user.employee
        
        updated = queryset.filter(status='pending').update(
            status='approved',
            approved_by=approved_by,
            approved_date=timezone.now()
        )
        self.message_user(request, f'{updated} solicitudes fueron aprobadas.')
    approve_requests.short_description = 'Aprobar solicitudes seleccionadas'
    
    def reject_requests(self, request, queryset):
        """Acción para rechazar solicitudes"""
        updated = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f'{updated} solicitudes fueron rechazadas.')
    reject_requests.short_description = 'Rechazar solicitudes seleccionadas'
    
    def cancel_requests(self, request, queryset):
        """Acción para cancelar solicitudes"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} solicitudes fueron canceladas.')
    cancel_requests.short_description = 'Cancelar solicitudes seleccionadas'


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = [
        'employee_display', 'leave_type', 'year', 
        'allocated_days', 'used_days', 'remaining_days', 
        'carried_forward', 'balance_status'
    ]
    
    list_filter = ['year', 'leave_type', 'employee__department'] 
    
    search_fields = [
        'employee__first_name', 'employee__last_name', 
        'employee__employee_number'
    ]
    
    readonly_fields = ['balance_calculation']
    
    fieldsets = (
        ('Información del Balance', {
            'fields': ('employee', 'leave_type', 'year')
        }),
        ('Días', {
            'fields': (
                'allocated_days', 'used_days', 'remaining_days', 
                'carried_forward', 'balance_calculation'
            )
        }),
    )
    
    def employee_display(self, obj):
        """Muestra el empleado con enlace"""
        return format_html(
            '<a href="{}">{}</a>',
            reverse('admin:employees_employee_change', args=[obj.employee.pk]),
            obj.employee.get_full_name() if hasattr(obj.employee, 'get_full_name') else str(obj.employee)
        )
    employee_display.short_description = 'Empleado'
    
    def balance_status(self, obj):
        """Muestra el estado del balance con colores"""
        if obj.remaining_days < 0:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">Sobrepasado</span>'
            )
        elif obj.remaining_days == 0:
            return format_html(
                '<span style="color: #ffc107; font-weight: bold;">Agotado</span>'
            )
        else:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">Disponible</span>'
            )
    balance_status.short_description = 'Estado del Balance'
    
    def balance_calculation(self, obj):
        """Muestra el cálculo del balance"""
        total_available = obj.allocated_days + obj.carried_forward
        return format_html(
            '<strong>Disponibles:</strong> {} días<br>'
            '<strong>Usados:</strong> {} días<br>'
            '<strong>Restantes:</strong> {} días<br>'
            '<small>(Asignados: {} + Transferidos: {} = Total: {})</small>',
            total_available,
            obj.used_days,
            obj.remaining_days,
            obj.allocated_days,
            obj.carried_forward,
            total_available
        )
    balance_calculation.short_description = 'Cálculo del Balance'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'employee', 'leave_type'
        )


# Configuración adicional del admin
admin.site.site_header = 'Administración de Licencias'
admin.site.site_title = 'Sistema de Licencias'
admin.site.index_title = 'Panel de Administración'