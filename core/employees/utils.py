# core/employees/utils.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging
import secrets
import string

logger = logging.getLogger(__name__)

def send_employee_credentials_email(user, password):
    """
    Envía las credenciales de acceso al nuevo empleado
    """
    try:
        subject = 'Bienvenido al Sistema de Nómina - Credenciales de Acceso'
        
        # Renderizar template HTML
        html_message = render_to_string('components/emails/employee_credentials.html', {
            'user': user,
            'password': password,
            'login_url': f"{settings.SITE_URL}/login/" if hasattr(settings, 'SITE_URL') else "http://localhost:8000/login/",
            'company_name': getattr(settings, 'COMPANY_NAME', 'Sistema de Nómina'),
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'onboarding@resend.dev'),  # CORREGIDO: usar dominio verificado como fallback
        })
        
        # Versión en texto plano
        plain_message = strip_tags(html_message)
        
        # Validar que el email del usuario esté configurado
        if not user.email:
            logger.warning(f"Usuario {user.get_full_name()} no tiene email configurado")
            return False
        
        # AGREGADO: Debug para verificar la configuración
        logger.info(f"Enviando email desde: {settings.DEFAULT_FROM_EMAIL}")
        logger.info(f"Support email configurado: {getattr(settings, 'SUPPORT_EMAIL', 'onboarding@resend.dev')}")
        
        # Enviar email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Credenciales enviadas por email a: {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando credenciales a {user.email}: {str(e)}")
        return False

def send_payroll_notification_email(employee, payroll_data):
    """
    Envía notificación de nómina al empleado
    """
    try:
        subject = f'Comprobante de Nómina - {payroll_data.get("period", "Período Actual")}'
        
        # Renderizar template HTML
        html_message = render_to_string('components/emails/payroll_notification.html', {
            'employee': employee,
            'payroll_data': payroll_data,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else "http://localhost:8000",
            'company_name': getattr(settings, 'COMPANY_NAME', 'Sistema de Nómina'),
        })
        
        # Versión en texto plano
        plain_message = strip_tags(html_message)
        
        if not employee.user.email:
            logger.warning(f"Empleado {employee.user.get_full_name()} no tiene email configurado")
            return False
        
        # Enviar email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[employee.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Notificación de nómina enviada a: {employee.user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando notificación de nómina a {employee.user.email}: {str(e)}")
        return False

def generate_secure_password():
    """
    Genera una contraseña segura aleatoria
    """
    # Caracteres permitidos
    characters = string.ascii_letters + string.digits + "!@#$%&*"
    
    # Generar contraseña de 12 caracteres
    password = ''.join(secrets.choice(characters) for _ in range(12))
    
    # Asegurar que tenga al menos una mayúscula, minúscula, número y símbolo
    if not any(c.isupper() for c in password):
        password = password[:-1] + secrets.choice(string.ascii_uppercase)
    if not any(c.islower() for c in password):
        password = password[:-2] + secrets.choice(string.ascii_lowercase) + password[-1]
    if not any(c.isdigit() for c in password):
        password = password[:-3] + secrets.choice(string.digits) + password[-2:]
    if not any(c in "!@#$%&*" for c in password):
        password = password[:-4] + secrets.choice("!@#$%&*") + password[-3:]
    
    return password

def send_password_reset_email(user, reset_link):
    """
    Envía email de restablecimiento de contraseña
    """
    try:
        subject = 'Restablecer Contraseña - Sistema de Nómina'
        
        html_message = render_to_string('components/emails/password_reset.html', {
            'user': user,
            'reset_link': reset_link,
            'company_name': getattr(settings, 'COMPANY_NAME', 'Sistema de Nómina'),
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email de restablecimiento enviado a: {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando email de restablecimiento a {user.email}: {str(e)}")
        return False

def send_bulk_notification_email(employees, subject, message, html_message=None):
    """
    Envía notificación masiva a múltiples empleados
    """
    success_count = 0
    error_count = 0
    
    for employee in employees:
        try:
            if not employee.user.email:
                logger.warning(f"Empleado {employee.user.get_full_name()} no tiene email")
                error_count += 1
                continue
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[employee.user.email],
                html_message=html_message,
                fail_silently=False,
            )
            success_count += 1
            logger.info(f"Notificación enviada a: {employee.user.email}")
            
        except Exception as e:
            error_count += 1
            logger.error(f"Error enviando a {employee.user.email}: {str(e)}")
    
    logger.info(f"Notificación masiva completada. Éxitos: {success_count}, Errores: {error_count}")
    return success_count, error_count