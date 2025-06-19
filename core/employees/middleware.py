# core/employees/middleware.py
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
    Middleware que redirige automáticamente según el tipo de usuario
    """
    
    def process_request(self, request):
        # Solo aplicar a usuarios autenticados
        if not request.user.is_authenticated:
            return None
        
        # URLs que no deben ser procesadas por este middleware
        exempt_urls = [
            '/admin/',
            '/static/',
            '/media/',
            '/api/',
            '/users/logout/',
            reverse('employees:employee_change_password'),
        ]
        
        # Verificar si la URL está exenta
        for exempt_url in exempt_urls:
            if request.path.startswith(exempt_url):
                return None
        
        # Si es empleado regular y está accediendo a URLs administrativas
        if (hasattr(request.user, 'employee_profile') and 
            (request.path.startswith('/employees/admin/') or 
             request.path.startswith('/users/dashboard/'))):
            
            # Verificar si tiene permisos administrativos
            if not (request.user.is_staff or request.user.is_superuser or 
                   getattr(request.user, 'user_type', '') in ['admin', 'hr', 'supervisor']):
                return redirect('employees:employee_dashboard')
        
        # Si es admin/staff y está accediendo a la raíz, redirigir al dashboard admin
        if ((request.user.is_staff or request.user.is_superuser or 
             getattr(request.user, 'user_type', '') in ['admin', 'hr', 'supervisor']) and
            request.path == '/' and not hasattr(request.user, 'employee_profile')):
            return redirect('users:dashboard')
        
        return None