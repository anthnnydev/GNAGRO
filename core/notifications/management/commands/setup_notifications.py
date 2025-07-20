# core/notifications/management/commands/setup_notifications.py
from django.core.management.base import BaseCommand
from core.notifications.services import NotificationService


class Command(BaseCommand):
    help = 'Configura los tipos de notificación por defecto'

    def handle(self, *args, **options):
        try:
            NotificationService.setup_notification_types()
            self.stdout.write(
                self.style.SUCCESS('✅ Tipos de notificación configurados correctamente')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error configurando tipos de notificación: {str(e)}')
            )