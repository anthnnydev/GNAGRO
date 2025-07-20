import os
import resend
from pathlib import Path
from decouple import config

from dotenv import load_dotenv
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-n+09mx^-bo&9zp(xr7&j-s)c(h-9o0y%7kjo7_4uej8bj_r7ad'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    #APPS
    'core.users',
    'core.employees',
    'core.payroll',
    'core.reports',
    'core.attendance',
    'core.leaves',
    'core.notifications',
    'core.tasks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    'core.employees.middleware.EmployeePasswordChangeMiddleware',
    'core.employees.middleware.EmployeeAccessMiddleware',
]

# AGREGAR ESTA LÍNEA:
ROOT_URLCONF = 'config.urls'

# Modelo de usuario personalizado
AUTH_USER_MODEL = 'users.User'

# URLs de autenticación - ACTUALIZADO
LOGIN_URL = '/users/'  # Página de login
LOGOUT_URL = '/users/logout/'
LOGIN_REDIRECT_URL = '/'  # Redirige a home_redirect que decide según el usuario

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ BASE_DIR / 'templates' ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.employees.context_processors.dashboard_stats',
                'core.users.context_processors.company_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tesis_db',
        'USER': 'postgres',
        'PASSWORD': 'anthony2003',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Guayaquil'
USE_I18N = True
USE_TZ = True

# Configuración de X-Frame-Options para permitir iframes del mismo origen
X_FRAME_OPTIONS = 'SAMEORIGIN' 
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

if DEBUG:
    # Permitir visualización en iframe durante desarrollo
    X_FRAME_OPTIONS = 'SAMEORIGIN'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# EMAIL SETTINGS
# Looking to send emails in production? Check out our Email API/SMTP product!
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.resend.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = 'resend'
EMAIL_HOST_PASSWORD = os.environ.get('RESEND_API_KEY')

# Email por defecto para envíos - USANDO DOMINIO DE RESEND (no requiere verificación)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Sistema de Nómina <onboarding@resend.dev>')

# Configuraciones adicionales para emails
COMPANY_NAME = os.environ.get('COMPANY_NAME', 'GNAGRO')
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'onboarding@resend.dev')

# URL base del sitio
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')

# Configuración de timeout para emails (opcional)
EMAIL_TIMEOUT = 30

# Crear directorio de logs si no existe
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGS_DIR, 'email.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'core.employees.utils': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.core.mail': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        # Logger para errores de email
        'email_errors': {
            'handlers': ['console', 'file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console'],
    },
}
# O si quieres usar Resend en desarrollo también, mantén la configuración SMTP

# Configuración de seguridad para emails
SECURE_EMAIL_SETTINGS = {
    'MAX_RECIPIENTS_PER_EMAIL': 50,  # Límite de destinatarios por email
    'EMAIL_RATE_LIMIT': 100,  # Emails por hora (ajustar según tu plan de Resend)
    'RETRY_FAILED_EMAILS': True,
}