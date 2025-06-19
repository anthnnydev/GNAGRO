from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    BenefitCategory, 
    Benefit, 
    Deduction, 
    EmployeeBenefit, 
    EmployeeDeduction
)


@admin.register(BenefitCategory)
class BenefitCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'benefits_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información General', {
            'fields': ('name', 'code', 'description')
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def benefits_count(self, obj):
        count = obj.benefits.count()
        if count > 0:
            url = reverse('admin:benefits_benefit_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}">{} beneficios</a>', url, count)
        return '0 beneficios'
    benefits_count.short_description = 'Beneficios'


@admin.register(Benefit)
class BenefitAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'category', 'calculation_type', 
        'amount_display', 'frequency', 'is_taxable', 'is_active'
    ]
    list_filter = [
        'category', 'calculation_type', 'frequency', 
        'is_taxable', 'is_active', 'created_at'
    ]
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información General', {
            'fields': ('name', 'code', 'category', 'description')
        }),
        ('Configuración de Cálculo', {
            'fields': ('calculation_type', 'amount', 'frequency')
        }),
        ('Límites', {
            'fields': ('min_amount', 'max_amount'),
            'classes': ('collapse',)
        }),
        ('Configuración Fiscal', {
            'fields': ('is_taxable',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def amount_display(self, obj):
        if obj.calculation_type == 'percentage':
            return f"{obj.amount}%"
        elif obj.calculation_type == 'fixed':
            return f"${obj.amount:,.2f}"
        else:
            return f"${obj.amount:,.2f}"
    amount_display.short_description = 'Monto'


@admin.register(Deduction)
class DeductionAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'calculation_type', 'amount_display', 
        'frequency', 'is_mandatory', 'is_active'
    ]
    list_filter = [
        'calculation_type', 'frequency', 'is_mandatory', 
        'is_active', 'created_at'
    ]
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información General', {
            'fields': ('name', 'code', 'description')
        }),
        ('Configuración de Cálculo', {
            'fields': ('calculation_type', 'amount', 'frequency')
        }),
        ('Límites', {
            'fields': ('min_amount', 'max_amount'),
            'classes': ('collapse',)
        }),
        ('Configuración', {
            'fields': ('is_mandatory',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def amount_display(self, obj):
        if obj.calculation_type == 'percentage':
            return f"{obj.amount}%"
        elif obj.calculation_type == 'fixed':
            return f"${obj.amount:,.2f}"
        else:
            return f"${obj.amount:,.2f}"
    amount_display.short_description = 'Monto'


class EmployeeBenefitInline(admin.TabularInline):
    model = EmployeeBenefit
    extra = 0
    fields = ['benefit', 'custom_amount', 'start_date', 'end_date', 'is_active']
    readonly_fields = ['created_at', 'updated_at']


class EmployeeDeductionInline(admin.TabularInline):
    model = EmployeeDeduction
    extra = 0
    fields = ['deduction', 'custom_amount', 'start_date', 'end_date', 'is_active']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(EmployeeBenefit)
class EmployeeBenefitAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'benefit', 'amount_display', 
        'start_date', 'end_date', 'is_active'
    ]
    list_filter = [
        'benefit__category', 'benefit', 'is_active', 
        'start_date', 'end_date'
    ]
    search_fields = [
        'employee__first_name', 'employee__last_name', 
        'employee__employee_id', 'benefit__name'
    ]
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Asignación', {
            'fields': ('employee', 'benefit')
        }),
        ('Configuración', {
            'fields': ('custom_amount', 'start_date', 'end_date')
        }),
        ('Estado y Notas', {
            'fields': ('is_active', 'notes')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def amount_display(self, obj):
        if obj.custom_amount:
            return f"${obj.custom_amount:,.2f} (personalizado)"
        else:
            if obj.benefit.calculation_type == 'percentage':
                return f"{obj.benefit.amount}% (del salario)"
            else:
                return f"${obj.benefit.amount:,.2f}"
    amount_display.short_description = 'Monto'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('employee', 'benefit')


@admin.register(EmployeeDeduction)
class EmployeeDeductionAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'deduction', 'amount_display', 
        'start_date', 'end_date', 'is_active'
    ]
    list_filter = [
        'deduction', 'is_active', 'start_date', 'end_date'
    ]
    search_fields = [
        'employee__first_name', 'employee__last_name', 
        'employee__employee_id', 'deduction__name'
    ]
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Asignación', {
            'fields': ('employee', 'deduction')
        }),
        ('Configuración', {
            'fields': ('custom_amount', 'start_date', 'end_date')
        }),
        ('Estado y Notas', {
            'fields': ('is_active', 'notes')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def amount_display(self, obj):
        if obj.custom_amount:
            return f"${obj.custom_amount:,.2f} (personalizado)"
        else:
            if obj.deduction.calculation_type == 'percentage':
                return f"{obj.deduction.amount}% (del salario)"
            else:
                return f"${obj.deduction.amount:,.2f}"
    amount_display.short_description = 'Monto'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('employee', 'deduction')


# Configuración adicional del admin
admin.site.site_header = "Administración de Beneficios y Deducciones"
admin.site.site_title = "Benefits Admin"
admin.site.index_title = "Panel de Administración"