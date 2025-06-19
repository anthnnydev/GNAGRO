# core/employees/urls_employee.py
from django.urls import path
from core.employees.views import employee_portal

app_name = 'employees'

# URLs específicas para el portal del empleado
employee_urlpatterns = [
    # Cambio de contraseña temporal
    path('change-password/', 
         employee_portal.employee_change_password_view, 
         name='employee_change_password'),
    
    # Dashboard del empleado
    path('dashboard/', 
         employee_portal.EmployeeDashboardView.as_view(), 
         name='employee_dashboard'),
    
    # Perfil del empleado
    path('profile/', 
         employee_portal.EmployeeProfileView.as_view(), 
         name='employee_profile'),
    
    # Documentos del empleado
    path('documents/', 
         employee_portal.EmployeeDocumentsView.as_view(), 
         name='employee_documents'),
    
    path('documents/<int:document_id>/download/', 
         employee_portal.employee_download_document, 
         name='employee_download_document'),
    
    # Información de nómina
    path('payroll/', 
         employee_portal.EmployeePayrollView.as_view(), 
         name='employee_payroll'),
    
    # Control de tiempo/asistencia
    path('time/', 
         employee_portal.EmployeeTimeView.as_view(), 
         name='employee_time'),
    
    # Solicitudes (vacaciones, permisos, etc.)
    path('requests/', 
         employee_portal.EmployeeRequestsView.as_view(), 
         name='employee_requests'),
    
    # Configuración del empleado
    path('settings/', 
         employee_portal.EmployeeSettingsView.as_view(), 
         name='employee_settings'),
    
    # Notificaciones
    path('notifications/', 
         employee_portal.EmployeeNotificationsView.as_view(), 
         name='employee_notifications'),
    
    # AJAX para notificaciones
    path('notifications/mark-read/', 
         employee_portal.EmployeeMarkNotificationReadView.as_view(), 
         name='employee_mark_notification_read'),
]