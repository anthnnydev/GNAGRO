from django import forms
from core.employees.models import EmployeeDocument


class EmployeeDocumentForm(forms.ModelForm):
    """Formulario para subir documentos del empleado"""
    
    class Meta:
        model = EmployeeDocument
        fields = ['document_type', 'name', 'file', 'notes']
        widgets = {
            'document_type': forms.Select(
                attrs={
                    'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                    'required': True
                }
            ),
            'name': forms.TextInput(
                attrs={
                    'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                    'placeholder': 'Ej: Cédula de Identidad',
                    'required': True
                }
            ),
            'file': forms.FileInput(
                attrs={
                    'class': 'sr-only',
                    'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.txt',
                    'required': True
                }
            ),
            'notes': forms.Textarea(
                attrs={
                    'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                    'rows': 3,
                    'placeholder': 'Descripción adicional del documento...'
                }
            )
        }
        labels = {
            'document_type': 'Tipo de documento',
            'name': 'Nombre del documento',
            'file': 'Archivo',
            'notes': 'Descripción (opcional)'
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            # Validar tamaño (máximo 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if file.size > max_size:
                raise forms.ValidationError(
                    f'El archivo es demasiado grande. Tamaño máximo: 10MB. '
                    f'Tu archivo: {file.size / (1024*1024):.1f}MB'
                )
            
            # Validar extensión
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.txt']
            file_extension = f'.{file.name.lower().split(".")[-1]}'
            if file_extension not in allowed_extensions:
                raise forms.ValidationError(
                    f'Tipo de archivo no permitido. Extensiones permitidas: {", ".join(allowed_extensions)}'
                )
        
        return file
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        
        if name:
            # Limpiar espacios extra
            name = name.strip()
            
            # Validar longitud
            if len(name) < 3:
                raise forms.ValidationError('El nombre debe tener al menos 3 caracteres.')
            
            if len(name) > 100:
                raise forms.ValidationError('El nombre no puede exceder 100 caracteres.')
        
        return name