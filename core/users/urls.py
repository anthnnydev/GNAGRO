from django.urls import path
from django.contrib.auth.views import LogoutView
from core.users.views import dashboard, login, parameters

app_name = 'users'

urlpatterns = [
    path('', login.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='users:login'), name='logout'),
    
    path('dashboard/', dashboard.dashboard_view, name='dashboard'),
    path('parameters/', parameters.parameters_view, name='parameters'),
    path('profile/', dashboard.profile_view, name='profile'),
]