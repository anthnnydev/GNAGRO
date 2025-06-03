# core/employees/urls.py
from django.urls import path
from core.employees.views import employee

app_name = 'employees'

urlpatterns = [
    path('', employee.EmployeeListView.as_view(), name='employee_list'),
    path('create/', employee.EmployeeCreateView.as_view(), name='employee_create'),
    path('<int:pk>/', employee.EmployeeDetailView.as_view(), name='employee_detail'),
    path('<int:pk>/update/', employee.EmployeeUpdateView.as_view(), name='employee_update'),
    path('<int:pk>/delete/', employee.EmployeeDeleteView.as_view(), name='employee_delete'),
    
    path('<int:employee_pk>/documents/create/', 
         employee.EmployeeDocumentCreateView.as_view(), 
         name='employee_document_create'),
    
    # URLs AJAX
    path('ajax/search/', employee.EmployeeAjaxSearchView.as_view(), name='employee_ajax_search'),
    path('ajax/stats/', employee.EmployeeStatsView.as_view(), name='employee_stats'),
]