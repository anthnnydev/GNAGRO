from django import forms
from django.core.exceptions import ValidationError
from ..models import AdelantoQuincena
from core.employees.models import Employee
from datetime import date
from decimal import Decimal


class AdelantoQuincenaForm(forms.ModelForm):
    """Formulario para adelantos de quincena"""
    
    class Meta:
        model = AdelantoQuincena
        fields = ['employee', 'monto', 'fecha_adelanto', 'motivo']
        widgets = {
            'employee': forms.Select(attrs={
                'class': 'w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'data-placeholder': 'Seleccionar empleado...'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'w-full pl-8 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'step': '0.01',
                'min': '0.01'
            }),
            'fecha_adelanto': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'type': 'date'
            }),
            'motivo': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-vertical',
                'rows': 3,
                'placeholder': 'Motivo del adelanto...'
            }),
        }
        labels = {
            'employee': 'Empleado',
            'monto': 'Monto del Adelanto ($)',
            'fecha_adelanto': 'Fecha del Adelanto',
            'motivo': 'Motivo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Cambiar is_active por status='active'
        self.fields['employee'].queryset = Employee.objects.filter(status='active')
        
        # Establecer fecha por defecto
        if not self.instance.pk:
            self.fields['fecha_adelanto'].initial = date.today()

    def clean_fecha_adelanto(self):
        fecha = self.cleaned_data['fecha_adelanto']
        
        # No permitir fechas futuras
        if fecha > date.today():
            raise ValidationError('No se pueden registrar adelantos con fecha futura.')
        
        return fecha

    def clean_monto(self):
        monto = self.cleaned_data['monto']
        
        if monto <= 0:
            raise ValidationError('El monto debe ser mayor a cero.')
        
        # Validar límite máximo (opcional, basado en salario del empleado)
        employee = self.cleaned_data.get('employee')
        if employee and hasattr(employee, 'salary') and employee.salary:
            # CORRECCIÓN: Convertir 0.5 a Decimal para evitar el error
            max_adelanto = employee.salary * Decimal('0.5')  # Máximo 50% del salario
            if monto > max_adelanto:
                raise ValidationError(
                    f'El adelanto no puede superar el 50% del salario (${max_adelanto:.2f})'
                )
        
        return monto