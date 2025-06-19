# core/users/views/login.py
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
        
        # Verificar si el usuario necesita cambiar contraseña temporal
        if getattr(user, 'needs_password_change', False):
            return reverse_lazy('employees:employee_change_password')
        
        # Redirección basada en el tipo de usuario
        if hasattr(user, 'employee_profile'):
            # Es un empleado regular - dirigir al portal del empleado
            return reverse_lazy('employees:employee_dashboard')
        
        elif (user.is_superuser or user.is_staff or 
              getattr(user, 'user_type', '') in ['admin', 'hr', 'supervisor']):
            # Es administrador/staff - dirigir al dashboard administrativo
            return reverse_lazy('users:dashboard')
        
        else:
            # Usuario sin perfil específico - dirigir al dashboard por defecto
            return reverse_lazy('users:dashboard')
    
    def form_valid(self, form):
        """
        Procesa el formulario válido y muestra mensaje de bienvenida
        """
        user = form.get_user()
        
        # Personalizar mensaje según el tipo de usuario
        if hasattr(user, 'employee_profile'):
            if getattr(user, 'needs_password_change', False):
                messages.warning(
                    self.request, 
                    f'¡Bienvenido, {user.get_full_name()}! Por seguridad, debes cambiar tu contraseña temporal.'
                )
            else:
                messages.success(
                    self.request, 
                    f'¡Bienvenido al portal de empleados, {user.get_full_name()}!'
                )
        else:
            messages.success(
                self.request, 
                f'¡Bienvenido al panel administrativo, {user.get_full_name()}!'
            )
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """
        Maneja formulario inválido
        """
        messages.error(self.request, 'Usuario o contraseña incorrectos.')
        return super().form_invalid(form)