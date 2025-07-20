# core/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.conf import settings

class User(AbstractUser):
    """
    Modelo de usuario personalizado que extiende AbstractUser
    """
    USER_TYPE_CHOICES = [
        ('employee', 'Empleado'),
        ('supervisor', 'Supervisor'),
        ('admin', 'Administrador'),
    ]
    
    user_type = models.CharField(
        max_length=15,
        choices=USER_TYPE_CHOICES,
        default='employee',
        verbose_name='Tipo de Usuario'
    )
    
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name='ID Empleado'
    )
    
    # Validador para números de teléfono ecuatorianos
    phone_regex = RegexValidator(
        regex=r'^09\d{8}$',
        message="El número debe tener 10 dígitos y comenzar con '09'. Ejemplo: 0998765432."
    )
    
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        verbose_name='Teléfono'
    )
    
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        null=True,
        blank=True,
        verbose_name='Foto de Perfil'
    )
    
    is_active_employee = models.BooleanField(
        default=True,
        verbose_name='Empleado Activo'
    )
    
    needs_password_change = models.BooleanField(
        default=False,
        verbose_name='Necesita cambiar contraseña',
        help_text='Indica si el usuario debe cambiar su contraseña temporal'
    )
    
    # Redefinimos para evitar conflictos con auth.User (E304)
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        db_table = 'users_user'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.employee_id or self.username})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    @property
    def is_supervisor(self):
        return self.user_type == 'supervisor'
    
    @property
    def is_admin_user(self):
        return self.user_type == 'admin'


class UserProfile(models.Model):
    """
    Perfil extendido del usuario con información adicional
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Nacimiento'
    )
    
    address = models.TextField(
        max_length=500,
        blank=True,
        verbose_name='Dirección'
    )
    
    emergency_contact_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Contacto de Emergencia'
    )
    
    # Validador para teléfono de emergencia (formato internacional)
    emergency_phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="El número debe estar en formato: '+999999999'. Hasta 15 dígitos."
    )
    
    emergency_contact_phone = models.CharField(
        validators=[emergency_phone_regex],
        max_length=17,
        blank=True,
        verbose_name='Teléfono de Emergencia'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'
        db_table = 'users_profile'
    
    def __str__(self):
        return f"Perfil de {self.user.get_full_name()}"
    
    
class Company(models.Model):
    """
    Modelo para almacenar información de la empresa
    """
    name = models.CharField(
        max_length=200,
        verbose_name='Nombre de la Empresa'
    )
    
    # Validador para RUC ecuatoriano (13 dígitos)
    ruc_regex = RegexValidator(
        regex=r'^\d{13}',
        message="El RUC debe tener exactamente 13 dígitos. Ejemplo: 1234567890001."
    )
    
    ruc = models.CharField(
        max_length=13,
        validators=[ruc_regex],
        unique=True,
        verbose_name='RUC'
    )
    
    address = models.TextField(
        max_length=500,
        verbose_name='Dirección'
    )
    
    city = models.CharField(
        max_length=100,
        verbose_name='Ciudad'
    )
    
    province = models.CharField(
        max_length=100,
        verbose_name='Provincia'
    )
    
    # Validador para teléfono de empresa (formato ecuatoriano)
    phone_regex = RegexValidator(
        regex=r'^0[2-9]\d{7}$|^09\d{8}',
        message="Formato: convencional 02XXXXXXX o celular 09XXXXXXXX."
    )
    
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        verbose_name='Teléfono'
    )
    
    email = models.EmailField(
        verbose_name='Email'
    )
    
    website = models.URLField(
        blank=True,
        verbose_name='Sitio Web'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Empresa Activa'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        db_table = 'users_company'
    
    def __str__(self):
        return f"{self.name} - {self.ruc}"
    
    @classmethod
    def get_active_company(cls):
        """
        Retorna la empresa activa del sistema
        """
        return cls.objects.filter(is_active=True).first()
    
    def get_full_address(self):
        """
        Retorna la dirección completa de la empresa
        """
        return f"{self.address}, {self.city}, {self.province}"