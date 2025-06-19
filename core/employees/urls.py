# core/employees/urls.py
from django.urls import path, include
from core.employees.views import employee, department, position
from core.employees.views import employee_portal

app_name = 'employees'

urlpatterns = [
    # ===== URLs ADMINISTRATIVAS =====
    # Employee URLs (Admin)
    path('admin/', employee.EmployeeListView.as_view(), name='employee_list'),
    path('admin/create/', employee.EmployeeCreateView.as_view(), name='employee_create'),
    path('admin/<int:pk>/', employee.EmployeeDetailView.as_view(), name='employee_detail'),
    path('admin/<int:pk>/update/', employee.EmployeeUpdateView.as_view(), name='employee_update'),
    path('admin/<int:pk>/delete/', employee.EmployeeDeleteView.as_view(), name='employee_delete'),
    
    path('admin/<int:employee_pk>/documents/create/', 
         employee.EmployeeDocumentCreateView.as_view(), 
         name='employee_document_create'),
    
    # Department URLs (Admin)
    path('admin/departments/', department.DepartmentListView.as_view(), name='department_list'),
    path('admin/departments/create/', department.DepartmentCreateView.as_view(), name='department_create'),
    path('admin/departments/<int:pk>/update/', department.DepartmentUpdateView.as_view(), name='department_update'),
    path('admin/departments/<int:pk>/delete/', department.DepartmentDeleteView.as_view(), name='department_delete'),
    
    # Position URLs (Admin)
    path('admin/positions/', position.PositionListView.as_view(), name='position_list'),
    path('admin/positions/create/', position.PositionCreateView.as_view(), name='position_create'),
    path('admin/positions/<int:pk>/update/', position.PositionUpdateView.as_view(), name='position_update'),
    path('admin/positions/<int:pk>/delete/', position.PositionDeleteView.as_view(), name='position_delete'),
    
    # AJAX URLs (Admin)
    path('admin/ajax/search/', employee.EmployeeAjaxSearchView.as_view(), name='employee_ajax_search'),
    path('admin/ajax/stats/', employee.EmployeeStatsView.as_view(), name='employee_stats'),
    path('admin/ajax/positions-by-department/', position.get_positions_by_department, name='positions_by_department'),
    path('admin/ajax/department-stats/', position.department_stats, name='department_stats'),
    
    # ===== URLs DEL PORTAL DEL EMPLEADO =====
    # Cambio de contraseña temporal (debe ser la primera para interceptar)
    path('change-password/', 
         employee_portal.employee_change_password_view, 
         name='employee_change_password'),
    
    # Dashboard del empleado (página principal)
    path('', 
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
    
    # AJAX para notificaciones del empleado
    path('notifications/mark-read/', 
         employee_portal.EmployeeMarkNotificationReadView.as_view(), 
         name='employee_mark_notification_read'),
]