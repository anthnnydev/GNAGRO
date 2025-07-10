from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

class EmployeePasswordChangeMiddleware(MiddlewareMixin):
    """
    Middleware que redirige a empleados con contraseña temporal
    al formulario de cambio de contraseña
    """
    
    def process_request(self, request):
        # Solo aplicar a usuarios autenticados
        if not request.user.is_authenticated:
            return None
        
        # Solo aplicar a empleados
        if not hasattr(request.user, 'employee_profile'):
            return None
        
        # Verificar si necesita cambiar contraseña
        if not getattr(request.user, 'needs_password_change', False):
            return None
        
        # URLs que están permitidas aunque necesite cambiar contraseña
        allowed_urls = [
            reverse('employees:employee_change_password'),
            reverse('users:logout'),
            '/users/logout/',
            '/logout/',
            '/accounts/logout/',
        ]
        
        # Permitir acceso a APIs y recursos estáticos
        if (request.path.startswith('/static/') or 
            request.path.startswith('/media/') or
            request.path.startswith('/api/')):
            return None
        
        # Si está en una URL permitida, no redirigir
        if request.path in allowed_urls:
            return None
        
        # Redirigir al cambio de contraseña
        return redirect('employees:employee_change_password')


class EmployeeAccessMiddleware(MiddlewareMixin):
    """
    Middleware que redirige automáticamente según el tipo de usuario - 3 ROLES
    """
    
    def process_request(self, request):
        # Solo aplicar a usuarios autenticados
        if not request.user.is_authenticated:
            return None
        
        # URLs que no deben ser procesadas por este middleware
        exempt_urls = [
            '/admin/',  # Django admin
            '/static/',
            '/media/',
            '/api/',
            '/users/logout/',
            '/employees/change-password/',
        ]
        
        # Verificar si la URL está exenta
        for exempt_url in exempt_urls:
            if request.path.startswith(exempt_url):
                return None
        
        # Solo aplicar si el usuario tiene employee_profile
        if not hasattr(request.user, 'employee_profile'):
            return None
        
        # Obtener el tipo de usuario
        user_type = getattr(request.user, 'user_type', 'employee')
        
        # ==================== REDIRECCIONES PARA ADMINISTRADORES ====================
        if user_type == 'admin' or request.user.is_superuser:
            
            # Administradores van al dashboard de users
            if request.path == '/' or request.path == '/employees/':
                return redirect('users:dashboard')
            
            # Permitir acceso libre a TODAS las URLs
            return None
        
        # ==================== REDIRECCIONES PARA SUPERVISORES ====================
        elif user_type == 'supervisor':
            
            if request.path == '/' or request.path == '/employees/':
                return redirect('employees:supervisor_dashboard')
            
            if request.path == '/employees/dashboard/':
                return redirect('employees:supervisor_dashboard')
        
        # ==================== REDIRECCIONES PARA EMPLEADOS REGULARES ====================
        elif user_type == 'employee':
            
            # Si está accediendo a URLs de supervisor, redirigir al empleado
            if request.path.startswith('/employees/supervisor/'):
                return redirect('employees:employee_dashboard')
            
            # Si está accediendo a URLs administrativas sin permisos
            if (request.path.startswith('/employees/admin/') or 
                request.path.startswith('/users/dashboard/')):
                return redirect('employees:employee_dashboard')
            
            # Si está accediendo a la raíz, redirigir al dashboard de empleado
            if request.path == '/' or request.path == '/employees/':
                return redirect('employees:employee_dashboard')
        
        return None