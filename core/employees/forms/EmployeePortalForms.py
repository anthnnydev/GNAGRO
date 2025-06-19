# core/employees/forms/EmployeePortalForms.py
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import get_user_model
from core.employees.models import Employee

User = get_user_model()


class EmployeePasswordChangeForm(PasswordChangeForm):
    """Formulario personalizado para cambio de contraseña del empleado"""
    
    old_password = forms.CharField(
        label="Contraseña actual",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
            'placeholder': 'Ingresa tu contraseña actual'
        })
    )
    
    new_password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
            'placeholder': 'Ingresa tu nueva contraseña'
        }),
        help_text="Tu contraseña debe contener al menos 8 caracteres y no puede ser muy común."
    )
    
    new_password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
            'placeholder': 'Confirma tu nueva contraseña'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar mensajes de error
        self.error_messages.update({
            'password_mismatch': 'Las contraseñas no coinciden.',
            'password_incorrect': 'La contraseña actual es incorrecta.',
        })


class EmployeeProfileForm(forms.ModelForm):
    """Formulario para que el empleado actualice su información personal"""
    
    class Meta:
        model = Employee
        fields = [
            'address', 
            'emergency_contact_name', 
            'emergency_contact_phone', 
            'emergency_contact_relationship'
        ]
        widgets = {
            'address': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'rows': 3,
                'placeholder': 'Ingresa tu dirección completa'
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'placeholder': 'Nombre completo del contacto de emergencia'
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'placeholder': 'Número de teléfono'
            }),
            'emergency_contact_relationship': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
                'placeholder': 'Parentesco (ej: Madre, Esposo/a, Hermano/a)'
            })
        }
        labels = {
            'address': 'Dirección',
            'emergency_contact_name': 'Contacto de emergencia',
            'emergency_contact_phone': 'Teléfono de emergencia',
            'emergency_contact_relationship': 'Parentesco'
        }
    
    # Campo adicional para actualizar email del usuario
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
            'placeholder': 'tu@email.com'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
    
    def save(self, commit=True):
        employee = super().save(commit=False)
        
        if commit:
            # Actualizar email del usuario
            if 'email' in self.cleaned_data:
                employee.user.email = self.cleaned_data['email']
                employee.user.save()
            
            employee.save()
        
        return employee


class EmployeeRequestForm(forms.Form):
    """Formulario base para solicitudes del empleado"""
    
    REQUEST_TYPES = [
        ('vacation', 'Solicitud de vacaciones'),
        ('permission', 'Permiso'),
        ('leave', 'Licencia'),
        ('other', 'Otro')
    ]
    
    request_type = forms.ChoiceField(
        label="Tipo de solicitud",
        choices=REQUEST_TYPES,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent'
        })
    )
    
    start_date = forms.DateField(
        label="Fecha de inicio",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent'
        })
    )
    
    end_date = forms.DateField(
        label="Fecha de fin",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent'
        })
    )
    
    reason = forms.CharField(
        label="Motivo",
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
            'rows': 4,
            'placeholder': 'Describe el motivo de tu solicitud'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError(
                    "La fecha de inicio no puede ser posterior a la fecha de fin."
                )
        
        return cleaned_data