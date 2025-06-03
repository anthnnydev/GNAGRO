# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil del Usuario'
    extra = 0  # No mostrar formularios extra vacíos
    max_num = 1  # Máximo un perfil por usuario
    
    # Campos que se mostrarán en el inline
    fields = ('birth_date', 'address', 'emergency_contact_name', 'emergency_contact_phone')
    
    def get_queryset(self, request):
        """Asegurar que solo se muestre un perfil por usuario"""
        return super().get_queryset(request)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_active_employee')
    list_filter = ('user_type', 'is_active_employee', 'is_staff')
    search_fields = ('username', 'email', 'employee_id')
    
    # Incluir el inline del perfil
    inlines = (UserProfileInline,)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('user_type', 'employee_id', 'phone_number', 'profile_picture', 'is_active_employee')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('user_type', 'employee_id', 'phone_number', 'is_active_employee')
        }),
    )

# NO registres UserProfile por separado si usas inline
# @admin.register(UserProfile)  # Comentar o eliminar esta línea
# class UserProfileAdmin(admin.ModelAdmin):
#     list_display = ('user', 'birth_date', 'emergency_contact_name')