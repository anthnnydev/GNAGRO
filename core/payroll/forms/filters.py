from django import forms
from ..models import PayrollPeriod, Rubro, TipoRubro
from employees.models import Employee


class PayrollFilterForm(forms.Form):
    """Formulario de filtros para lista de nóminas"""
    
    period = forms.ModelChoiceField(
        queryset=PayrollPeriod.objects.all(),
        required=False,
        empty_label="Todos los períodos",
        widget=forms.Select(attrs={
            'class': 'form-control select2'
        })
    )
    
    employee = forms.ModelChoiceField(
        queryset=Employee.objects.filter(is_active=True),
        required=False,
        empty_label="Todos los empleados",
        widget=forms.Select(attrs={
            'class': 'form-control select2'
        })
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('paid', 'Pagados'),
            ('unpaid', 'No Pagados'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre o número de empleado...'
        })
    )


class RubroFilterForm(forms.Form):
    """Formulario de filtros para lista de rubros"""
    
    tipo = forms.ModelChoiceField(
        queryset=TipoRubro.objects.filter(is_active=True),
        required=False,
        empty_label="Todos los tipos",
        widget=forms.Select(attrs={
            'class': 'form-control select2'
        })
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('active', 'Activos'),
            ('inactive', 'Inactivos'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre o código...'
        })
    )