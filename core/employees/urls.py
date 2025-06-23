# core/employees/urls.py
from django.urls import path, include
from core.employees.views import employee, department, position
from core.employees.views import employee_portal, attendance_ajax, supervisor_portal

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
    
    # ===== PORTAL DEL SUPERVISOR =====
    path('supervisor/', supervisor_portal.SupervisorDashboardView.as_view(), name='supervisor_dashboard'),
    path('supervisor/team/', supervisor_portal.SupervisorTeamView.as_view(), name='supervisor_team'),
    path('supervisor/team/<int:pk>/', supervisor_portal.SupervisorEmployeeDetailView.as_view(), name='supervisor_employee_detail'),
    path('supervisor/reports/', supervisor_portal.SupervisorReportsView.as_view(), name='supervisor_reports'),
    
    # APIs del supervisor
    path('supervisor/api/stats/', supervisor_portal.supervisor_stats_api, name='supervisor_stats_api'),
    path('supervisor/api/team-performance/', supervisor_portal.supervisor_team_performance_api, name='supervisor_team_performance_api'),
    
    # ===== PORTAL DEL EMPLEADO =====
    path('dashboard/', employee_portal.EmployeeDashboardView.as_view(), name='employee_dashboard'),
    path('profile/', employee_portal.EmployeeProfileView.as_view(), name='employee_profile'),
    path('documents/', employee_portal.EmployeeDocumentsView.as_view(), name='employee_documents'),
    path('payroll/', employee_portal.EmployeePayrollView.as_view(), name='employee_payroll'),
    path('time/', employee_portal.EmployeeTimeView.as_view(), name='employee_time'),
    path('requests/', employee_portal.EmployeeRequestsView.as_view(), name='employee_requests'),
    
    # ===== NUEVAS URLs PARA GESTIÓN DE SOLICITUDES DE LICENCIA =====
    path('requests/leave/create/', employee_portal.EmployeeLeaveRequestCreateView.as_view(), name='employee_leave_request_create'),
    path('requests/leave/<int:pk>/', employee_portal.EmployeeLeaveRequestDetailView.as_view(), name='employee_leave_request_detail'),
    
    path('settings/', employee_portal.EmployeeSettingsView.as_view(), name='employee_settings'),
    path('notifications/', employee_portal.EmployeeNotificationsView.as_view(), name='employee_notifications'),
    
    # Cambio de contraseña
    path('change-password/', employee_portal.employee_change_password_view, name='employee_change_password'),
    
    # APIs de asistencia
    path('api/attendance/', include([
        path('clock-in/', attendance_ajax.clock_in_api, name='api_clock_in'),
        path('clock-out/', attendance_ajax.clock_out_api, name='api_clock_out'),
        path('break-start/', attendance_ajax.break_start_api, name='api_break_start'),
        path('break-end/', attendance_ajax.break_end_api, name='api_break_end'),
        path('status/', attendance_ajax.attendance_status_api, name='api_attendance_status'),
    ])),
    
    # Descargas
    path('documents/<int:document_id>/download/', 
         employee_portal.employee_download_document, 
         name='employee_download_document'),
]