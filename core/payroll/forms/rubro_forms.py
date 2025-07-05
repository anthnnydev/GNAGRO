from django import forms
from ..models import Rubro, TipoRubro

class TipoRubroForm(forms.ModelForm):
    """Formulario para tipos de rubro"""
    
    class Meta:
        model = TipoRubro
        fields = ['nombre', 'tipo', 'descripcion', 'is_active']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Ej: Deducciones Legales'
            }),
            'tipo': forms.Select(attrs={
                'class': 'w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-vertical',
                'rows': 3,
                'placeholder': 'Descripción del tipo de rubro...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
            }),
        }
        labels = {
            'nombre': 'Nombre del Tipo',
            'tipo': 'Tipo',
            'descripcion': 'Descripción',
            'is_active': 'Activo',
        }

class RubroForm(forms.ModelForm):
    """Formulario para rubros"""
    
    class Meta:
        model = Rubro
        fields = [
            'tipo_rubro', 'codigo', 'nombre', 'descripcion', 'tipo_calculo',
            'porcentaje_default', 'monto_default', 'es_obligatorio',
            'aplicar_automaticamente', 'is_active'
        ]
        widgets = {
            'tipo_rubro': forms.Select(attrs={
                'class': 'w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'data-placeholder': 'Seleccionar tipo...'
            }),
            'codigo': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 uppercase',
                'placeholder': 'Ej: IESS, BON_PROD',
                'style': 'text-transform: uppercase;'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Ej: Aporte IESS'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-vertical',
                'rows': 3,
                'placeholder': 'Descripción detallada del rubro...'
            }),
            'tipo_calculo': forms.Select(attrs={
                'class': 'w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'id': 'id_tipo_calculo'
            }),
            'porcentaje_default': forms.NumberInput(attrs={
                'class': 'w-full pl-4 pr-8 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'monto_default': forms.NumberInput(attrs={
                'class': 'w-full pl-8 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'step': '0.01',
                'min': '0'
            }),
            'es_obligatorio': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
            }),
            'aplicar_automaticamente': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
            }),
        }
        labels = {
            'tipo_rubro': 'Tipo de Rubro',
            'codigo': 'Código',
            'nombre': 'Nombre',
            'descripcion': 'Descripción',
            'tipo_calculo': 'Tipo de Cálculo',
            'porcentaje_default': 'Porcentaje por Defecto (%)',
            'monto_default': 'Monto por Defecto ($)',
            'es_obligatorio': 'Es Obligatorio',
            'aplicar_automaticamente': 'Aplicar Automáticamente',
            'is_active': 'Activo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar tipos activos
        self.fields['tipo_rubro'].queryset = TipoRubro.objects.filter(is_active=True)

    def clean_codigo(self):
        codigo = self.cleaned_data['codigo'].upper()
        
        # Verificar unicidad
        existing = Rubro.objects.filter(codigo=codigo)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise forms.ValidationError('Ya existe un rubro con este código.')
        
        return codigo

    def clean(self):
        cleaned_data = super().clean()
        tipo_calculo = cleaned_data.get('tipo_calculo')
        porcentaje_default = cleaned_data.get('porcentaje_default')
        monto_default = cleaned_data.get('monto_default')
        
        # Validar valores por defecto según tipo de cálculo
        if tipo_calculo in ['porcentaje', 'porcentaje_bruto']:
            if porcentaje_default is None:
                raise forms.ValidationError(
                    'Debe especificar un porcentaje por defecto para este tipo de cálculo.'
                )
        
        elif tipo_calculo == 'fijo':
            if monto_default is None:
                raise forms.ValidationError(
                    'Debe especificar un monto por defecto para este tipo de cálculo.'
                )
        
        return cleaned_data