# core/users/views/login.py (CORREGIDO)
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.http import HttpResponseRedirect

try:
    from core.employees.models import Employee, Department
except ImportError:
    Employee = None
    Department = None


class CustomLoginView(LoginView):
    template_name = 'security/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """
        Redirige según el tipo de usuario y si necesita cambiar contraseña
        """
        user = self.request.user
        
        # DEBUG temporal - quitar después
        print(f"=== LOGIN DEBUG ===")
        print(f"Usuario: {user.email}")
        print(f"user_type: {getattr(user, 'user_type', 'NO_TYPE')}")
        print(f"is_staff: {user.is_staff}")
        print(f"is_superuser: {user.is_superuser}")
        print(f"has_employee_profile: {hasattr(user, 'employee_profile')}")
        
        # Verificar si el usuario necesita cambiar contraseña temporal
        if getattr(user, 'needs_password_change', False):
            print("→ Redirigiendo a cambio de contraseña")
            return reverse_lazy('employees:employee_change_password')
        
        # NUEVA LÓGICA: Priorizar user_type sobre employee_profile
        user_type = getattr(user, 'user_type', 'employee')
        
        # 1. ADMINISTRADORES (prioridad máxima)
        if user_type == 'admin' or user.is_superuser:
            print("→ Redirigiendo a users:dashboard (admin)")
            return reverse_lazy('users:dashboard')
        
        # 2. SUPERVISORES
        elif user_type == 'supervisor':
            print("→ Redirigiendo a employees:supervisor_dashboard")
            return reverse_lazy('employees:supervisor_dashboard')
        
        # 3. EMPLEADOS REGULARES
        elif user_type == 'employee' and hasattr(user, 'employee_profile'):
            print("→ Redirigiendo a employees:employee_dashboard")
            return reverse_lazy('employees:employee_dashboard')
        
        # 4. STAFF SIN EMPLOYEE_PROFILE (caso especial)
        elif user.is_staff and not hasattr(user, 'employee_profile'):
            print("→ Redirigiendo a users:dashboard (staff sin employee_profile)")
            return reverse_lazy('users:dashboard')
        
        # 5. FALLBACK - usuarios sin clasificación clara
        else:
            print("→ Redirigiendo a users:dashboard (fallback)")
            return reverse_lazy('users:dashboard')
    
    def form_valid(self, form):
        """
        Procesa el formulario válido y muestra mensaje de bienvenida
        """
        user = form.get_user()
        user_type = getattr(user, 'user_type', 'employee')
        
        # Personalizar mensaje según el tipo de usuario
        if getattr(user, 'needs_password_change', False):
            messages.warning(
                self.request, 
                f'¡Bienvenido, {user.get_full_name()}! Por seguridad, debes cambiar tu contraseña temporal.'
            )
        else:
            # Mensajes personalizados por tipo
            if user_type == 'admin' or user.is_superuser:
                messages.success(
                    self.request, 
                    f'¡Bienvenido al panel administrativo, {user.get_full_name()}!'
                )
            elif user_type == 'supervisor':
                messages.success(
                    self.request, 
                    f'¡Bienvenido al panel de supervisor, {user.get_full_name()}!'
                )
            elif hasattr(user, 'employee_profile'):
                messages.success(
                    self.request, 
                    f'¡Bienvenido al portal de empleados, {user.get_full_name()}!'
                )
            else:
                messages.success(
                    self.request, 
                    f'¡Bienvenido, {user.get_full_name()}!'
                )
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """
        Maneja formulario inválido
        """
        messages.error(self.request, 'Usuario o contraseña incorrectos.')
        return super().form_invalid(form)