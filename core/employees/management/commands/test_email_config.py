# management/commands/test_email_config.py
# Crear este archivo en: core/employees/management/commands/test_email_config.py

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail
import os

class Command(BaseCommand):
    help = 'Verifica la configuración de email y envía un email de prueba'

    def add_arguments(self, parser):
        parser.add_argument('--to', type=str, help='Email de destino para la prueba')

    def handle(self, *args, **options):
        self.stdout.write("🔍 Verificando configuración de email...")
        
        # Verificar variables de entorno
        self.stdout.write(f"RESEND_API_KEY: {'✅ Configurado' if os.environ.get('RESEND_API_KEY') else '❌ No configurado'}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {os.environ.get('DEFAULT_FROM_EMAIL', 'No configurado')}")
        self.stdout.write(f"SUPPORT_EMAIL: {os.environ.get('SUPPORT_EMAIL', 'No configurado')}")
        
        # Verificar settings de Django
        self.stdout.write("\n📧 Configuración de Django:")
        self.stdout.write(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        self.stdout.write(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        self.stdout.write(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"SUPPORT_EMAIL: {getattr(settings, 'SUPPORT_EMAIL', 'No configurado')}")
        
        # Verificar dominio
        from_email = settings.DEFAULT_FROM_EMAIL
        if '@resend.dev' in from_email or 'onboarding@resend.dev' in from_email:
            self.stdout.write("✅ Usando dominio verificado de Resend")
        else:
            self.stdout.write("⚠️  ADVERTENCIA: No estás usando el dominio verificado de Resend")
        
        # Enviar email de prueba si se proporciona destinatario
        if options['to']:
            self.stdout.write(f"\n📤 Enviando email de prueba a: {options['to']}")
            try:
                send_mail(
                    subject='Prueba de configuración de email',
                    message='Este es un email de prueba para verificar la configuración.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[options['to']],
                    fail_silently=False,
                )
                self.stdout.write("✅ Email de prueba enviado exitosamente")
            except Exception as e:
                self.stdout.write(f"❌ Error enviando email de prueba: {str(e)}")
        else:
            self.stdout.write("\n💡 Para enviar un email de prueba, usa: --to tu-email@ejemplo.com")