# core/payroll/forms/payroll_forms.py
from django import forms
from django.core.exceptions import ValidationError
from ..models import Payroll, PayrollRubro, Rubro
from core.employees.models import Employee


class PayrollForm(forms.ModelForm):
    """Formulario simplificado para crear/editar nóminas usando rubros"""
    
    class Meta:
        model = Payroll
        fields = [
            'employee', 'period', 'base_salary', 'overtime_hours', 
            'overtime_rate', 'payment_method', 'notes'
        ]
        widgets = {
            'employee': forms.Select(attrs={
                'class': 'w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'data-placeholder': 'Seleccionar empleado...'
            }),
            'period': forms.Select(attrs={
                'class': 'w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'data-placeholder': 'Seleccionar período...'
            }),
            'base_salary': forms.NumberInput(attrs={
                'class': 'w-full pl-8 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'step': '0.01',
                'min': '0',
                'readonly': True,  # Solo lectura, se toma del empleado
                'title': 'Este valor se toma automáticamente del salario del empleado'
            }),
            'overtime_hours': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'step': '0.01',
                'min': '0'
            }),
            'overtime_rate': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'step': '0.01',
                'min': '1.0',
                'value': '1.50'
            }),
            'payment_method': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Ej: Transferencia bancaria'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-vertical',
                'rows': 3,
                'placeholder': 'Observaciones adicionales...'
            }),
        }
        labels = {
            'employee': 'Empleado',
            'period': 'Período de Nómina',
            'base_salary': 'Salario Base ($)',
            'overtime_hours': 'Horas Extras',
            'overtime_rate': 'Factor Horas Extras',
            'payment_method': 'Método de Pago',
            'notes': 'Notas',
        }
        help_texts = {
            'base_salary': 'Se toma automáticamente del perfil del empleado',
            'overtime_hours': 'Número de horas extras trabajadas',
            'overtime_rate': 'Factor multiplicador para horas extras (ej: 1.5 = 50% adicional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar empleados activos
        self.fields['employee'].queryset = Employee.objects.filter(
            status='active'
        ).select_related('user', 'department').order_by('user__first_name', 'user__last_name')
        
        # Si es edición, deshabilitar empleado y período
        if self.instance and self.instance.pk:
            self.fields['employee'].widget.attrs['disabled'] = True
            self.fields['period'].widget.attrs['disabled'] = True
            
            # Auto-completar salario base si el empleado tiene salario definido
            if self.instance.employee and hasattr(self.instance.employee, 'salary'):
                self.fields['base_salary'].initial = self.instance.employee.salary

    def clean_employee(self):
        employee = self.cleaned_data.get('employee')
        if employee and not hasattr(employee, 'salary'):
            raise ValidationError(
                'El empleado seleccionado no tiene un salario definido. '
                'Por favor, configure el salario en el perfil del empleado.'
            )
        return employee

    def clean(self):
        cleaned_data = super().clean()
        employee = cleaned_data.get('employee')
        period = cleaned_data.get('period')
        
        # Validar que no exista ya una nómina para este empleado en este período
        if employee and period:
            existing = Payroll.objects.filter(employee=employee, period=period)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError(
                    f'Ya existe una nómina para {employee.user.get_full_name()} en el período {period.name}'
                )
        
        # Auto-asignar salario base del empleado
        if employee and hasattr(employee, 'salary'):
            cleaned_data['base_salary'] = employee.salary
        
        return cleaned_data

    def save(self, commit=True):
        payroll = super().save(commit=False)
        
        # Auto-completar salario base desde el empleado
        if payroll.employee and hasattr(payroll.employee, 'salary'):
            payroll.base_salary = payroll.employee.salary
        
        if commit:
            payroll.save()
            
            # Aplicar rubros automáticos solo si es nueva nómina
            if not self.instance.pk:
                payroll.aplicar_rubros_automaticos()
                payroll.aplicar_deducciones_legales()
        
        return payroll


class PayrollRubroForm(forms.ModelForm):
    """Formulario para agregar rubros a nóminas"""
    
    class Meta:
        model = PayrollRubro
        fields = ['rubro', 'monto', 'porcentaje', 'horas', 'observaciones']
        widgets = {
            'rubro': forms.Select(attrs={
                'class': 'w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'data-placeholder': 'Seleccionar rubro...',
                'onchange': 'updateRubroFields(this)'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'step': '0.01',
                'min': '0'
            }),
            'porcentaje': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'horas': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'step': '0.01',
                'min': '0'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-vertical',
                'rows': 2,
                'placeholder': 'Observaciones del rubro...'
            }),
        }
        labels = {
            'rubro': 'Rubro',
            'monto': 'Monto ($)',
            'porcentaje': 'Porcentaje (%)',
            'horas': 'Horas',
            'observaciones': 'Observaciones',
        }

    def __init__(self, *args, **kwargs):
        self.payroll = kwargs.pop('payroll', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar rubros activos
        queryset = Rubro.objects.filter(is_active=True).select_related('tipo_rubro').order_by('tipo_rubro__tipo', 'nombre')
        
        # AGREGADO: Si hay payroll, excluir rubros ya aplicados
        if self.payroll:
            rubros_aplicados_ids = self.payroll.rubros_aplicados.values_list('rubro_id', flat=True)
            queryset = queryset.exclude(id__in=rubros_aplicados_ids)
        
        self.fields['rubro'].queryset = queryset
        
        # Hacer campos condicionales según el tipo de cálculo
        self.fields['monto'].required = False
        self.fields['porcentaje'].required = False
        self.fields['horas'].required = False

    def clean(self):
        cleaned_data = super().clean()
        rubro = cleaned_data.get('rubro')
        monto = cleaned_data.get('monto')
        porcentaje = cleaned_data.get('porcentaje')
        horas = cleaned_data.get('horas')
        
        if rubro:
            # Validar que el rubro no esté ya aplicado
            if self.payroll and self.payroll.rubros_aplicados.filter(rubro=rubro).exists():
                raise ValidationError(f'El rubro "{rubro.nombre}" ya está aplicado a esta nómina.')
            
            # Validar según el tipo de cálculo del rubro
            if rubro.tipo_calculo == 'fijo':
                if not monto:
                    if rubro.monto_default:
                        cleaned_data['monto'] = rubro.monto_default
                    else:
                        raise ValidationError('Debe especificar un monto para este rubro.')
            
            elif rubro.tipo_calculo in ['porcentaje', 'porcentaje_bruto']:
                if not porcentaje:
                    if rubro.porcentaje_default:
                        cleaned_data['porcentaje'] = rubro.porcentaje_default
                    else:
                        raise ValidationError('Debe especificar un porcentaje para este rubro.')
                
                # Calcular monto automáticamente
                if porcentaje and self.payroll:
                    if rubro.tipo_calculo == 'porcentaje':
                        base_calculo = self.payroll.base_salary
                    else:  # porcentaje_bruto
                        base_calculo = self.payroll.base_salary + self.payroll.overtime_pay
                    
                    cleaned_data['monto'] = (base_calculo * porcentaje) / 100
            
            elif rubro.tipo_calculo == 'horas':
                if not horas:
                    if rubro.horas_default:
                        cleaned_data['horas'] = rubro.horas_default
                    else:
                        raise ValidationError('Debe especificar las horas para este rubro.')
                
                # Calcular monto si hay tarifa por hora
                if horas and hasattr(self.payroll.employee, 'hourly_rate') and self.payroll.employee.hourly_rate:
                    cleaned_data['monto'] = self.payroll.employee.hourly_rate * horas
                elif not monto:
                    raise ValidationError('Debe especificar un monto o configurar la tarifa por hora del empleado.')
        
        return cleaned_data

    def save(self, commit=True):
        payroll_rubro = super().save(commit=False)
        
        if self.payroll:
            payroll_rubro.payroll = self.payroll
        
        if commit:
            payroll_rubro.save()
        
        return payroll_rubro


class BulkPayrollActionForm(forms.Form):
    """Formulario para acciones masivas en nóminas"""
    
    ACTION_CHOICES = [
        ('mark_paid', 'Marcar como Pagadas'),
        ('mark_unpaid', 'Marcar como No Pagadas'),
        ('apply_rubro', 'Aplicar Rubro'),
        ('export_pdf', 'Exportar PDF'),
        ('export_csv', 'Exportar CSV'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
        }),
        label='Acción'
    )
    
    payroll_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    
    payment_method = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            'placeholder': 'Método de pago (opcional)'
        }),
        label='Método de Pago'
    )
    
    rubro = forms.ModelChoiceField(
        queryset=Rubro.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
        }),
        label='Rubro a Aplicar'
    )

    def clean_payroll_ids(self):
        payroll_ids = self.cleaned_data.get('payroll_ids')
        if payroll_ids:
            try:
                ids = [int(id.strip()) for id in payroll_ids.split(',') if id.strip()]
                if not ids:
                    raise ValidationError('No se seleccionaron nóminas.')
                return ids
            except ValueError:
                raise ValidationError('IDs de nómina inválidos.')
        return []

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        if action == 'apply_rubro' and not cleaned_data.get('rubro'):
            raise ValidationError('Debe seleccionar un rubro para aplicar.')
        
        if action == 'mark_paid' and not cleaned_data.get('payment_method'):
            cleaned_data['payment_method'] = 'Transferencia bancaria'
        
        return cleaned_data


class PayrollCalculatorForm(forms.Form):
    """Formulario para calculadora de nómina"""
    
    base_salary = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            'step': '0.01',
            'placeholder': '0.00'
        }),
        label='Salario Base'
    )
    
    overtime_hours = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            'step': '0.01',
            'placeholder': '0.00'
        }),
        label='Horas Extra'
    )
    
    overtime_rate = forms.DecimalField(
        max_digits=3,
        decimal_places=2,
        min_value=1,
        initial=1.5,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            'step': '0.01'
        }),
        label='Factor Horas Extra'
    )
    
    include_iess = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'rounded border-gray-300 text-primary-600 focus:ring-primary-500'
        }),
        label='Incluir descuento IESS (9.45%)'
    )
    
    additional_deductions = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            'step': '0.01',
            'placeholder': '0.00'
        }),
        label='Deducciones Adicionales'
    )