from django.urls import path
from django.contrib.auth.views import LogoutView
from core.users.views import dashboard, login, parameters, empresa

app_name = 'users'

urlpatterns = [
    path('', login.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='users:login'), name='logout'),
    
    path('dashboard/', dashboard.dashboard_view, name='dashboard'),
    path('parameters/', parameters.parameters_view, name='parameters'),
    path('profile/', dashboard.profile_view, name='profile'),
    
    path('companies/', empresa.company_list, name='company_list'),
    path('companies/create/', empresa.company_create, name='company_create'),

    path('companies/<int:company_id>/', empresa.company_detail, name='company_detail'),
    path('companies/<int:company_id>/edit/', empresa.company_edit, name='company_edit'),

    path('companies/<int:company_id>/delete/', empresa.company_delete, name='company_delete'),
    path('companies/<int:company_id>/activate/', empresa.company_activate, name='company_activate'),
    
    path('company/settings/', empresa.company_settings, name='company_settings'),

    path('ajax/company/', empresa.CompanyAjaxView.as_view(), name='company_ajax'),
    path('ajax/validate-ruc/', empresa.validate_ruc, name='validate_ruc'),
    path('ajax/company-dashboard-info/', empresa.company_dashboard_info, name='company_dashboard_info'),
]