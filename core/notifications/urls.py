from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Vistas principales
    path('', views.notification_list, name='notification_list'),
    path('<int:pk>/', views.notification_detail, name='notification_detail'),
    path('preferences/', views.notification_preferences, name='preferences'),
    
    # API AJAX
    path('api/unread-count/', views.get_unread_count, name='api_unread_count'),
    path('api/recent/', views.get_recent_notifications, name='api_recent'),
    path('api/dashboard/', views.dashboard_notifications, name='api_dashboard'),
    
    # Acciones AJAX
    path('api/<int:pk>/mark-read/', views.mark_as_read, name='api_mark_read'),
    path('api/mark-all-read/', views.mark_all_as_read, name='api_mark_all_read'),
    path('api/<int:pk>/delete/', views.delete_notification, name='api_delete'),
]