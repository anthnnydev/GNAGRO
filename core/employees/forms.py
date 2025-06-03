# core/employees/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from .models import Employee, Department, Position, EmployeeDocument

User = get_user_model()


class UserEmployeeForm(forms.ModelForm):
    """Formulario para datos del usuario del empleado"""
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
            'placeholder': 'Ingresa una contraseña segura'
        }),
        required=False  # Solo requerido al crear nuevo empleado
    )
    password2 = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
            'placeholder': 'Confirma la contraseña'
        }),
        required=False  # Solo requerido al crear nuevo empleado
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'profile_picture']  # Agregado profile_picture
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Nombre de usuario único'
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
        
        # Solo requerir contraseñas para nuevos empleados
        if not self.is_new_employee:
            self.fields['password1'].required = False
            self.fields['password2'].required = False
            # Opcional: ocultar campos de contraseña en edición
            del self.fields['password1']
            del self.fields['password2']
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        
        # Solo validar si estamos creando un nuevo empleado
        if self.is_new_employee:
            if password1 and password2 and password1 != password2:
                raise ValidationError("Las contraseñas no coinciden.")
        return password2
    
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
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Solo establecer contraseña si es un nuevo empleado y se proporcionó
        if self.is_new_employee and self.cleaned_data.get("password1"):
            user.set_password(self.cleaned_data["password1"])
        
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