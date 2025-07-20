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
        # NUEVO: Importar Company aquí para evitar imports circulares
        from core.users.models import Company
        
        # Obtener datos de la empresa activa
        active_company = Company.get_active_company()
        company_data = {}
        if active_company:
            company_data = {
                'name': active_company.name,
                'email': active_company.email,
                'phone': active_company.phone,
                'website': active_company.website,
            }
        
        subject = f'Bienvenido a {company_data.get("name", "Sistema de Nómina")} - Credenciales de Acceso'
        
        # Renderizar template HTML
        html_message = render_to_string('components/emails/employee_credentials.html', {
            'user': user,
            'password': password,
            'login_url': f"{settings.SITE_URL}/login/" if hasattr(settings, 'SITE_URL') else "http://localhost:8000/login/",
            'company_data': company_data,  # NUEVO: Pasar datos de empresa
            'company_name': company_data.get('name', 'Sistema de Nómina'),  # Mantener para compatibilidad
            'support_email': company_data.get('email') or getattr(settings, 'SUPPORT_EMAIL', 'onboarding@resend.dev'),
        })
        
        # Versión en texto plano
        plain_message = strip_tags(html_message)
        
        # Validar que el email del usuario esté configurado
        if not user.email:
            logger.warning(f"Usuario {user.get_full_name()} no tiene email configurado")
            return False
        
        # Configurar remitente
        from_email = settings.DEFAULT_FROM_EMAIL
        
        # AGREGADO: Debug para verificar la configuración
        logger.info(f"Enviando email desde: {from_email}")
        logger.info(f"Support email configurado: {company_data.get('email') or getattr(settings, 'SUPPORT_EMAIL', 'onboarding@resend.dev')}")
        
        # Enviar email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Credenciales enviadas por email a: {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando credenciales a {user.email}: {str(e)}")
        return False

def send_payroll_notification_email(employee, payroll_data, company_data=None):
    """
    Envía notificación de nómina al empleado
    
    Args:
        employee: Instancia del empleado
        payroll_data: Diccionario con datos de la nómina
        company_data: Diccionario con datos de la empresa (opcional)
    
    Returns:
        bool: True si se envió correctamente, False en caso contrario
    """
    try:
        # NUEVO: Obtener datos de empresa si no se proporcionan
        if not company_data:
            from core.users.models import Company
            active_company = Company.get_active_company()
            if active_company:
                company_data = {
                    'name': active_company.name,
                    'ruc': active_company.ruc,
                    'email': active_company.email,
                    'phone': active_company.phone,
                    'website': active_company.website,
                    'address': active_company.get_full_address(),
                }
            else:
                company_data = {
                    'name': 'Sistema de Nómina',
                    'ruc': '',
                    'email': '',
                    'phone': '',
                    'website': '',
                    'address': '',
                }
        
        # Configurar subject con nombre de empresa
        company_name = company_data.get('name', 'Sistema de Nómina')
        subject = f'Comprobante de Nómina - {payroll_data.get("period", "Período Actual")} | {company_name}'
        
        # CORREGIDO: Verificar si los egresos adicionales ya están incluidos en total_deductions
        total_egresos_adicionales = 0
        
        if 'egresos_adicionales' in payroll_data:
            # Calcular suma de egresos adicionales
            total_egresos_adicionales = sum(
                egreso.get('monto', 0) for egreso in payroll_data['egresos_adicionales']
            )
            
            # Verificar si ya están incluidos en total_deductions
            current_total_deductions = payroll_data.get('total_deductions', 0)
            
            # Si total_deductions ya incluye los egresos adicionales, no los sumamos
            if abs(current_total_deductions - total_egresos_adicionales) < 0.01:
                # Los egresos adicionales YA están incluidos en total_deductions
                payroll_data['total_deducciones_completo'] = current_total_deductions
                logger.info(f"Los egresos adicionales ya están incluidos en total_deductions: ${current_total_deductions}")
            else:
                # Los egresos adicionales NO están incluidos, los sumamos
                payroll_data['total_deducciones_completo'] = current_total_deductions + total_egresos_adicionales
                logger.info(f"Sumando egresos adicionales: ${current_total_deductions} + ${total_egresos_adicionales} = ${payroll_data['total_deducciones_completo']}")
        else:
            # No hay egresos adicionales, usar total_deductions tal como está
            payroll_data['total_deducciones_completo'] = payroll_data.get('total_deductions', 0)
        
        # Renderizar template HTML
        html_message = render_to_string('components/emails/payroll_notification.html', {
            'employee': employee,
            'payroll_data': payroll_data,
            'company_data': company_data,  # NUEVO: Pasar datos de empresa
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else "http://localhost:8000",
            'company_name': company_name,  # Mantener para compatibilidad
        })
        
        # Versión en texto plano
        plain_message = strip_tags(html_message)
        
        if not employee.user.email:
            logger.warning(f"Empleado {employee.user.get_full_name()} no tiene email configurado")
            return False
        
        # Configurar remitente
        from_email = settings.DEFAULT_FROM_EMAIL
        
        # Enviar email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=[employee.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"✅ Notificación de nómina enviada a: {employee.user.email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando notificación de nómina a {employee.user.email}: {str(e)}")
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
        # NUEVO: Obtener datos de empresa
        from core.users.models import Company
        active_company = Company.get_active_company()
        company_data = {}
        if active_company:
            company_data = {
                'name': active_company.name,
                'email': active_company.email,
            }
        
        company_name = company_data.get('name', 'Sistema de Nómina')
        subject = f'Restablecer Contraseña - {company_name}'
        
        html_message = render_to_string('components/emails/password_reset.html', {
            'user': user,
            'reset_link': reset_link,
            'company_data': company_data,  # NUEVO: Pasar datos de empresa
            'company_name': company_name,  # Mantener para compatibilidad
        })
        
        plain_message = strip_tags(html_message)
        
        # Configurar remitente
        from_email = settings.DEFAULT_FROM_EMAIL
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
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
    try:
        # NUEVO: Obtener datos de empresa para configurar remitente
        from core.users.models import Company
        active_company = Company.get_active_company()
        from_email = settings.DEFAULT_FROM_EMAIL
        
        if active_company and active_company.email:
            from_email = active_company.email
            company_name = active_company.name
            # Agregar nombre de empresa al subject si no está incluido
            if company_name not in subject:
                subject = f"{subject} | {company_name}"
        
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
                    from_email=from_email,  # NUEVO: Usar email de empresa
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
        
    except Exception as e:
        logger.error(f"Error en notificación masiva: {str(e)}")
        return 0, len(employees)

def send_welcome_email(employee):
    """
    Envía email de bienvenida a nuevo empleado
    """
    try:
        from core.users.models import Company
        active_company = Company.get_active_company()
        company_data = {}
        
        if active_company:
            company_data = {
                'name': active_company.name,
                'email': active_company.email,
                'phone': active_company.phone,
                'website': active_company.website,
                'address': active_company.get_full_address(),
            }
        
        company_name = company_data.get('name', 'Sistema de Nómina')
        subject = f'¡Bienvenido a {company_name}!'
        
        html_message = render_to_string('components/emails/welcome_employee.html', {
            'employee': employee,
            'company_data': company_data,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else "http://localhost:8000",
        })
        
        plain_message = strip_tags(html_message)
        
        from_email = settings.DEFAULT_FROM_EMAIL
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=[employee.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email de bienvenida enviado a: {employee.user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando email de bienvenida a {employee.user.email}: {str(e)}")
        return False