# core/notifications/apps.py
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.notifications'
    verbose_name = 'Notificaciones'

    def ready(self):
        # Solo importar signals, NO hacer consultas a la BD
        import core.notifications.signals