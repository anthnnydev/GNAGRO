from django.urls import path
from .views import supervisor, employee

app_name = 'tasks'

urlpatterns = [
    # ===== URLs DEL SUPERVISOR =====
    # Dashboard principal del supervisor
    path('supervisor/', supervisor.SupervisorDashboardView.as_view(), name='supervisor_dashboard'),
    
    # Gestión de tareas
    path('supervisor/tasks/', supervisor.TaskListView.as_view(), name='task_list'),
    path('supervisor/tasks/create/', supervisor.TaskCreateView.as_view(), name='task_create'),
    path('supervisor/tasks/<int:pk>/', supervisor.TaskDetailView.as_view(), name='task_detail'),
    path('supervisor/tasks/<int:pk>/edit/', supervisor.TaskUpdateView.as_view(), name='task_update'),
    path('supervisor/tasks/<int:pk>/delete/', supervisor.TaskDeleteView.as_view(), name='task_delete'),
    path('supervisor/tasks/<int:pk>/assign/', supervisor.TaskAssignView.as_view(), name='task_assign'),
    
    # Gestión de categorías
    path('supervisor/categories/', supervisor.TaskCategoryListView.as_view(), name='category_list'),
    path('supervisor/categories/create/', supervisor.TaskCategoryCreateView.as_view(), name='category_create'),
    path('supervisor/categories/<int:pk>/edit/', supervisor.TaskCategoryUpdateView.as_view(), name='category_update'),
    path('supervisor/categories/<int:pk>/delete/', supervisor.TaskCategoryDeleteView.as_view(), name='category_delete'),
    
    # APIs del supervisor
    path('supervisor/api/stats/', supervisor.task_stats_api, name='supervisor_stats_api'),
    path('supervisor/api/assignment/<int:assignment_id>/status/', supervisor.task_assignment_status_update, name='assignment_status_update'),
    path('supervisor/api/bulk-actions/', supervisor.bulk_task_actions, name='bulk_task_actions'),
    path('supervisor/export/csv/', supervisor.export_tasks_csv, name='export_tasks_csv'),
    
    # ===== URLs DEL EMPLEADO =====
    # Dashboard de tareas del empleado
    path('', employee.EmployeeTaskDashboardView.as_view(), name='employee_task_dashboard'),
    
    # Gestión de tareas del empleado
    path('my-tasks/', employee.EmployeeTaskListView.as_view(), name='employee_task_list'),
    path('my-tasks/<int:pk>/', employee.EmployeeTaskDetailView.as_view(), name='employee_task_detail'),
    path('my-progress/', employee.EmployeeTaskProgressView.as_view(), name='employee_progress_history'),
    
    # APIs del empleado
    path('api/employee/stats/', employee.employee_task_stats_api, name='employee_stats_api'),
    path('api/employee/task/<int:assignment_id>/location/', employee.task_location_api, name='task_location_api'),
    path('api/employee/calendar/', employee.employee_task_calendar_api, name='employee_calendar_api'),
    path('api/employee/work-session/start/', employee.start_work_session, name='start_work_session'),
    path('api/employee/work-session/end/', employee.end_work_session, name='end_work_session'),
]