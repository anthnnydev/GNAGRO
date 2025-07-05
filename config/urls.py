from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.users.views.dashboard import home_redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Página principal que redirige según tipo de usuario
    path('', home_redirect, name='home'),
    
    # Apps del proyecto
    path('users/', include('core.users.urls')),
    path('employees/', include('core.employees.urls')),
    path('leaves/', include('core.leaves.urls')),
    path('attendance/', include('core.attendance.urls')),
    path('payroll/', include('core.payroll.urls')),
    path('tasks/', include('core.tasks.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)