import re
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from ..models import Employee, Department, Position, EmployeeDocument
from ..utils import generate_secure_password

User = get_user_model()


class UserEmployeeForm(forms.ModelForm):
    """Formulario para datos del usuario del empleado"""
    
    # NUEVO: Campo para seleccionar el tipo de usuario
    user_type = forms.ChoiceField(
        label="Tipo de Usuario",
        choices=User.USER_TYPE_CHOICES,
        initial='employee',
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
        }),
        help_text="Selecciona el rol que tendrá este usuario en el sistema"
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'profile_picture', 'user_type']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Se generará automáticamente',
                'readonly': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'correo@ejemplo.com'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Nombres'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Apellidos'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': '0998765432'
            }),
            'profile_picture': forms.ClearableFileInput(attrs={
                'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100',
                'accept': 'image/jpeg,image/jpg,image/png'
            })
        }
    
    def __init__(self, *args, **kwargs):
        # Extraer si es un nuevo empleado o edición
        self.is_new_employee = kwargs.pop('is_new_employee', True)
        super().__init__(*args, **kwargs)
        
        # Marcar email como requerido para nuevos empleados
        if self.is_new_employee:
            self.fields['email'].required = True
            # Para nuevos empleados, el username se genera automáticamente
            self.fields['username'].widget.attrs['placeholder'] = 'Se generará automáticamente basado en nombres y apellidos'
        else:
            # Para edición, permitir modificar el username
            self.fields['username'].widget.attrs.pop('readonly', None)
            self.fields['username'].widget.attrs['placeholder'] = 'Nombre de usuario único'
        
        # Personalizar las opciones del tipo de usuario con descripciones
        self.fields['user_type'].choices = [
            ('employee', 'Empleado - Acceso básico al portal'),
            ('supervisor', 'Supervisor - Puede crear y gestionar tareas'),
            ('hr', 'Recursos Humanos - Gestión completa de empleados'),
            ('admin', 'Administrador - Acceso completo al sistema'),
        ]
    
    def generate_username(self, first_name, last_name):
        """
        Genera un username basado en el formato: inicial_nombre + apellido + inicial_segundo_apellido + número
        Ejemplo: Anthony Alexander Lopez Martinez -> alopezm6
        """
        if not first_name or not last_name:
            return None
        
        # Limpiar y dividir nombres y apellidos
        first_names = self.clean_name_parts(first_name)
        last_names = self.clean_name_parts(last_name)
        
        if not first_names or not last_names:
            return None
        
        # Tomar la primera letra del primer nombre
        first_initial = first_names[0][0].lower()
        
        # Tomar el primer apellido completo
        first_lastname = last_names[0].lower()
        
        # Tomar la primera letra del segundo apellido (si existe)
        second_lastname_initial = last_names[1][0].lower() if len(last_names) > 1 else ''
        
        # Formar el username base
        base_username = f"{first_initial}{first_lastname}{second_lastname_initial}"
        
        # Verificar si ya existe y agregar número si es necesario
        username = base_username
        counter = 1
        
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        return username
    
    def clean_name_parts(self, name):
        """
        Limpia y divide un nombre completo en partes individuales
        Elimina caracteres especiales y espacios extra
        """
        if not name:
            return []
        
        # Eliminar caracteres especiales y normalizar espacios
        cleaned_name = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]', '', name.strip())
        # Dividir por espacios y filtrar partes vacías
        parts = [part.strip() for part in cleaned_name.split() if part.strip()]
        
        return parts
    
    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        
        # Solo generar username automáticamente para nuevos empleados
        if self.is_new_employee and first_name and last_name:
            generated_username = self.generate_username(first_name, last_name)
            if generated_username:
                cleaned_data['username'] = generated_username
            else:
                raise ValidationError("No se pudo generar un nombre de usuario válido. Verifique los nombres y apellidos.")
        
        return cleaned_data
    
    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            # Validar tamaño del archivo (máximo 2MB)
            if picture.size > 2 * 1024 * 1024:
                raise ValidationError("La imagen no debe superar los 2MB.")
            
            # Validar tipo de archivo
            valid_extensions = ['jpg', 'jpeg', 'png']
            ext = picture.name.split('.')[-1].lower()
            if ext not in valid_extensions:
                raise ValidationError("Solo se permiten archivos JPG, JPEG y PNG.")
        
        return picture
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.is_new_employee and not email:
            raise ValidationError("El email es requerido para nuevos empleados.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # NUEVO: Asignar el tipo de usuario seleccionado
        user.user_type = self.cleaned_data.get('user_type', 'employee')
        
        # Asignar permisos staff según el tipo de usuario
        if user.user_type in ['admin', 'hr']:
            user.is_staff = True
        elif user.user_type == 'supervisor':
            user.is_staff = False  # Los supervisores no necesitan acceso al admin de Django
        else:
            user.is_staff = False
        
        # Generar contraseña automáticamente para nuevos empleados
        if self.is_new_employee:
            password = generate_secure_password()
            user.set_password(password)
            # Guardar la contraseña para enviarla por email
            user._generated_password = password
        
        if commit:
            user.save()
        return user


class EmployeeForm(forms.ModelForm):
    """Formulario para datos del empleado"""
    
    class Meta:
        model = Employee
        fields = [
            'national_id', 'gender', 'birth_date', 'marital_status', 'address',
            'employee_number', 'department', 'position', 'supervisor',
            'hire_date', 'contract_type', 'salary', 'status',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship'
        ]
        widgets = {
            'national_id': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': '1234567890'
            }),
            'gender': forms.Select(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
            }),
            'birth_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
            }),
            'marital_status': forms.Select(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
            }),
            'address': forms.Textarea(attrs={
                'rows': 3,
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Dirección completa del empleado'
            }),
            'employee_number': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'EMP-001'
            }),
            'department': forms.Select(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
            }),
            'position': forms.Select(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
            }),
            'supervisor': forms.Select(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
            }),
            'hire_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
            }),
            'contract_type': forms.Select(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
            }),
            'salary': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': '1000.00'
            }),
            'status': forms.Select(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Nombre completo del contacto de emergencia'
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': '0998765432'
            }),
            'emergency_contact_relationship': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Padre, Madre, Cónyuge, etc.'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar supervisores activos
        self.fields['supervisor'].queryset = Employee.objects.filter(
            status='active'
        ).select_related('user')
        self.fields['supervisor'].empty_label = "Sin supervisor"
        
        # Filtrar departamentos activos
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        
        # Filtrar posiciones activas
        self.fields['position'].queryset = Position.objects.filter(is_active=True)
    
    def clean_employee_number(self):
        employee_number = self.cleaned_data.get('employee_number')
        if Employee.objects.filter(employee_number=employee_number).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError("Este número de empleado ya existe.")
        return employee_number
    
    def clean_national_id(self):
        national_id = self.cleaned_data.get('national_id')
        if Employee.objects.filter(national_id=national_id).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError("Esta cédula ya está registrada.")
        return national_id


class EmployeeDocumentForm(forms.ModelForm):
    """Formulario para documentos de empleados"""
    
    class Meta:
        model = EmployeeDocument
        fields = ['document_type', 'name', 'file', 'notes']
        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500'
            }),
            'name': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Nombre descriptivo del documento'
            }),
            'file': forms.FileInput(attrs={
                'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100',
                'accept': '.pdf,.doc,.docx,.png,.jpg,.jpeg'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Notas adicionales sobre el documento (opcional)'
            }),
        }


class EmployeeSearchForm(forms.Form):
    """Formulario para búsqueda de empleados"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm',
            'placeholder': 'Buscar por nombre, número de empleado o cédula...'
        })
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label="Todos los departamentos",
        widget=forms.Select(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )
    status = forms.ChoiceField(
        choices=[('', 'Todos los estados')] + Employee.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
        })
    )