# core/tasks/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

class TasksRedirectMiddleware(MiddlewareMixin):
    """
    Middleware que redirige automáticamente según el tipo de usuario en la app de tareas
    """
    
    def process_request(self, request):
        # Solo aplicar a usuarios autenticados
        if not request.user.is_authenticated:
            return None
        
        # Solo aplicar si el usuario tiene employee_profile
        if not hasattr(request.user, 'employee_profile'):
            return None
        
        # Solo aplicar a URLs de la app tasks
        if not request.path.startswith('/tasks/'):
            return None
        
        # URLs que no deben ser procesadas por este middleware
        exempt_paths = [
            '/tasks/api/',
            '/tasks/supervisor/api/',
        ]
        
        # Verificar si la URL está exenta
        for exempt_path in exempt_paths:
            if request.path.startswith(exempt_path):
                return None
        
        # Obtener el tipo de usuario
        user_type = getattr(request.user, 'user_type', 'employee')
        
        # Si es supervisor/admin/hr accediendo a URLs de empleado, redirigir
        if user_type in ['supervisor', 'admin', 'hr']:
            # Si está accediendo a la raíz de tasks o URLs de empleado
            if (request.path == '/tasks/' or 
                request.path.startswith('/tasks/my-') or
                request.path == '/tasks/employee/'):
                return redirect('tasks:supervisor_dashboard')
            
            # Si está accediendo a una URL que no es de supervisor, redirigir
            if (request.path.startswith('/tasks/') and 
                not request.path.startswith('/tasks/supervisor/') and
                not request.path.startswith('/tasks/api/')):
                return redirect('tasks:supervisor_dashboard')
        
        # Si es empleado regular accediendo a URLs de supervisor, redirigir
        elif user_type == 'employee':
            if request.path.startswith('/tasks/supervisor/'):
                return redirect('tasks:employee_task_dashboard')
        
        return None