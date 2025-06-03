from django.contrib import admin
from .models import Department, Position, Employee, EmployeeDocument

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'manager', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'base_salary', 'is_active')
    list_filter = ('department', 'is_active')
    search_fields = ('title',)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_number', 'full_name', 'department', 'position', 'status')
    list_filter = ('department', 'position', 'status', 'contract_type')
    search_fields = ('employee_number', 'user__first_name', 'user__last_name', 'national_id')
    readonly_fields = ('years_of_service',)

@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee', 'document_type', 'upload_date')
    list_filter = ('document_type', 'upload_date')
    search_fields = ('name', 'employee__user__first_name', 'employee__user__last_name')