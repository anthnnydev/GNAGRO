from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse_lazy

try:
    from core.employees.models import Employee, Department
except ImportError:
    # En caso de que aún no hayas creado los modelos
    Employee = None
    Department = None


class CustomLoginView(LoginView):
    template_name = 'security/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('users:dashboard')
    
    def form_valid(self, form):
        messages.success(self.request, f'¡Bienvenido, {form.get_user().get_full_name()}!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Usuario o contraseña incorrectos.')
        return super().form_invalid(form)


class CustomLoginView(LoginView):
    template_name = 'security/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('users:dashboard')
    
    def form_valid(self, form):
        messages.success(self.request, f'¡Bienvenido, {form.get_user().get_full_name()}!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Usuario o contraseña incorrectos.')
        return super().form_invalid(form)