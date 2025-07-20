from django import forms
from django.core.exceptions import ValidationError
from .models import Company

class CompanyForm(forms.ModelForm):
    """
    Formulario para crear y editar información de la empresa
    """
    
    class Meta:
        model = Company
        fields = [
            'name', 'ruc', 'address', 'city', 'province', 'phone', 'email', 'website'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la empresa'
            }),
            'ruc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1234567890001',
                'maxlength': '13'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dirección completa de la empresa'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ciudad'
            }),
            'province': forms.Select(attrs={
                'class': 'form-control'
            }, choices=[
                ('', 'Seleccione una provincia'),
                ('Azuay', 'Azuay'),
                ('Bolívar', 'Bolívar'),
                ('Cañar', 'Cañar'),
                ('Carchi', 'Carchi'),
                ('Chimborazo', 'Chimborazo'),
                ('Cotopaxi', 'Cotopaxi'),
                ('El Oro', 'El Oro'),
                ('Esmeraldas', 'Esmeraldas'),
                ('Galápagos', 'Galápagos'),
                ('Guayas', 'Guayas'),
                ('Imbabura', 'Imbabura'),
                ('Loja', 'Loja'),
                ('Los Ríos', 'Los Ríos'),
                ('Manabí', 'Manabí'),
                ('Morona Santiago', 'Morona Santiago'),
                ('Napo', 'Napo'),
                ('Orellana', 'Orellana'),
                ('Pastaza', 'Pastaza'),
                ('Pichincha', 'Pichincha'),
                ('Santa Elena', 'Santa Elena'),
                ('Santo Domingo', 'Santo Domingo'),
                ('Sucumbíos', 'Sucumbíos'),
                ('Tungurahua', 'Tungurahua'),
                ('Zamora Chinchipe', 'Zamora Chinchipe'),
            ]),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '02XXXXXXX o 09XXXXXXXX'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'info@empresa.com'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.empresa.com'
            }),
        }
    
    def clean_ruc(self):
        """
        Validación personalizada para el RUC
        """
        ruc = self.cleaned_data.get('ruc')
        if ruc:
            # Verificar que solo contenga dígitos
            if not ruc.isdigit():
                raise ValidationError("El RUC debe contener solo números.")
            
            # Verificar longitud
            if len(ruc) != 13:
                raise ValidationError("El RUC debe tener exactamente 13 dígitos.")
            
            # Algoritmo de validación de RUC ecuatoriano
            if not self._validate_ecuadorian_ruc(ruc):
                raise ValidationError("El RUC ingresado no es válido.")
        
        return ruc
    
    def _validate_ecuadorian_ruc(self, ruc):
        """
        Algoritmo de validación para RUC ecuatoriano
        """
        try:
            # Los dos primeros dígitos deben ser válidos (01-24)
            provincia = int(ruc[:2])
            if provincia < 1 or provincia > 24:
                return False
            
            # El tercer dígito indica el tipo de contribuyente
            tercer_digito = int(ruc[2])
            if tercer_digito < 0 or tercer_digito > 9:
                return False
            
            # Verificaciones específicas según el tipo de contribuyente
            if tercer_digito <= 5:  # Persona natural
                return self._validate_cedula_algorithm(ruc[:10])
            elif tercer_digito == 6:  # Sector público
                return self._validate_sector_publico(ruc)
            elif tercer_digito == 9:  # Jurídica
                return self._validate_juridica(ruc)
            else:
                return False
                
        except (ValueError, IndexError):
            return False
    
    def _validate_cedula_algorithm(self, numero):
        """
        Algoritmo de validación para cédula (10 dígitos)
        """
        try:
            # Los dos primeros dígitos deben ser válidos (01-24)
            provincia = int(numero[:2])
            if provincia < 1 or provincia > 24:
                return False
            
            # El tercer dígito debe ser menor a 6
            if int(numero[2]) > 5:
                return False
            
            # Algoritmo de validación
            coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
            suma = 0
            
            for i in range(9):
                valor = int(numero[i]) * coeficientes[i]
                if valor >= 10:
                    valor -= 9
                suma += valor
            
            resultado = suma % 10
            if resultado != 0:
                resultado = 10 - resultado
            
            return resultado == int(numero[9])
            
        except (ValueError, IndexError):
            return False
    
    def _validate_sector_publico(self, ruc):
        """
        Validación para RUC de sector público
        """
        try:
            coeficientes = [3, 2, 7, 6, 5, 4, 3, 2]
            suma = 0
            
            for i in range(8):
                suma += int(ruc[i]) * coeficientes[i]
            
            resultado = suma % 11
            if resultado != 0:
                resultado = 11 - resultado
            
            return resultado == int(ruc[8])
            
        except (ValueError, IndexError):
            return False
    
    def _validate_juridica(self, ruc):
        """
        Validación para RUC de persona jurídica
        """
        try:
            coeficientes = [4, 3, 2, 7, 6, 5, 4, 3, 2]
            suma = 0
            
            for i in range(9):
                suma += int(ruc[i]) * coeficientes[i]
            
            resultado = suma % 11
            if resultado != 0:
                resultado = 11 - resultado
            
            return resultado == int(ruc[9])
            
        except (ValueError, IndexError):
            return False