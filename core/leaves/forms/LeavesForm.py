# core/leaves/forms.py
from django import forms
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from ..models import LeaveType, LeaveRequest, LeaveBalance


class LeaveTypeForm(forms.ModelForm):
    """
    Formulario para crear y editar tipos de licencia
    """
    class Meta:
        model = LeaveType
        fields = [
            'name', 'code', 'days_allowed', 'requires_approval',
            'is_paid', 'carry_forward', 'color', 'description', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400',
                'placeholder': 'Ej: Vacaciones Anuales'
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400 uppercase',
                'placeholder': 'Ej: VAC',
                'maxlength': '10'
            }),
            'days_allowed': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400',
                'min': '0',
                'placeholder': 'Ej: 30'
            }),
            'requires_approval': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 text-blue-600 focus:ring-blue-500 border-2 border-gray-300 rounded transition-colors duration-200 hover:border-blue-400'
            }),
            'is_paid': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 text-green-600 focus:ring-green-500 border-2 border-gray-300 rounded transition-colors duration-200 hover:border-green-400'
            }),
            'carry_forward': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 text-purple-600 focus:ring-purple-500 border-2 border-gray-300 rounded transition-colors duration-200 hover:border-purple-400'
            }),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'h-12 w-20 border-2 border-gray-300 rounded-lg cursor-pointer focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 hover:border-gray-400 shadow-sm',
                'title': 'Seleccionar color para el tipo de licencia'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400 resize-none',
                'rows': 4,
                'placeholder': 'Descripción opcional del tipo de licencia'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-5 w-5 text-emerald-600 focus:ring-emerald-500 border-2 border-gray-300 rounded transition-colors duration-200 hover:border-emerald-400'
            }),
        }
        labels = {
            'name': 'Nombre del Tipo de Licencia',
            'code': 'Código',
            'days_allowed': 'Días Permitidos',
            'requires_approval': 'Requiere Aprobación',
            'is_paid': 'Es Pagada',
            'carry_forward': 'Permite Transferencia',
            'color': 'Color Identificativo',
            'description': 'Descripción',
            'is_active': 'Activo'
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = code.upper()
            # Verificar unicidad excluyendo la instancia actual
            queryset = LeaveType.objects.filter(code=code)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise ValidationError('Ya existe un tipo de licencia con este código.')
        return code


class LeaveRequestForm(forms.ModelForm):
    """
    Formulario para crear y editar solicitudes de licencia
    """
    class Meta:
        model = LeaveRequest
        fields = [
            'employee', 'leave_type', 'start_date', 'end_date', 
            'days_requested', 'reason'
        ]
        widgets = {
            'employee': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400'
            }),
            'leave_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400'
            }),
            'days_requested': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-200 rounded-lg bg-gray-50 text-gray-600 cursor-not-allowed shadow-sm',
                'min': '1',
                'readonly': True
            }),
            'reason': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400 resize-none',
                'rows': 4,
                'placeholder': 'Motivo de la solicitud de licencia'
            }),
        }
        labels = {
            'employee': 'Empleado',
            'leave_type': 'Tipo de Licencia',
            'start_date': 'Fecha de Inicio',
            'end_date': 'Fecha de Fin',
            'days_requested': 'Días Solicitados',
            'reason': 'Motivo'
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar tipos de licencia activos
        self.fields['leave_type'].queryset = LeaveType.objects.filter(is_active=True)
        self.fields['leave_type'].empty_label = "Seleccionar tipo de licencia"
        
        # Si es una nueva solicitud y tenemos usuario, preseleccionar empleado
        if not self.instance.pk and self.user:
            try:
                # Importar aquí para evitar imports circulares - MOVIDO DENTRO DEL TRY
                from core.employees.models import Employee
                employee = Employee.objects.get(user=self.user)
                self.fields['employee'].initial = employee
            except Employee.DoesNotExist:
                pass
            except ImportError:
                # Manejar el caso donde no se puede importar Employee
                pass

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        employee = cleaned_data.get('employee')
        leave_type = cleaned_data.get('leave_type')

        # Validar fechas
        if start_date and end_date:
            if start_date > end_date:
                raise ValidationError('La fecha de inicio no puede ser posterior a la fecha de fin.')
            
            if start_date < datetime.now().date():
                raise ValidationError('La fecha de inicio no puede ser anterior a hoy.')
            
            # Calcular días automáticamente
            days_requested = (end_date - start_date).days + 1
            cleaned_data['days_requested'] = days_requested

        # Validar balance disponible
        if employee and leave_type and start_date:
            year = start_date.year
            try:
                balance = LeaveBalance.objects.get(
                    employee=employee,
                    leave_type=leave_type,
                    year=year
                )
                if balance.remaining_days < cleaned_data.get('days_requested', 0):
                    raise ValidationError(
                        f'No tienes suficientes días disponibles. '
                        f'Disponible: {balance.remaining_days} días.'
                    )
            except LeaveBalance.DoesNotExist:
                # Si no existe balance, verificar con días permitidos del tipo
                if leave_type.days_allowed < cleaned_data.get('days_requested', 0):
                    raise ValidationError(
                        f'Los días solicitados exceden el límite permitido '
                        f'({leave_type.days_allowed} días).'
                    )

        return cleaned_data


class LeaveRequestApprovalForm(forms.ModelForm):
    """
    Formulario para aprobar/rechazar solicitudes de licencia
    """
    class Meta:
        model = LeaveRequest
        fields = ['status', 'rejection_reason']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400'
            }),
            'rejection_reason': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400 resize-none',
                'rows': 4,
                'placeholder': 'Motivo del rechazo (requerido si se rechaza la solicitud)'
            }),
        }
        labels = {
            'status': 'Decisión',
            'rejection_reason': 'Motivo del Rechazo'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo mostrar opciones relevantes para aprobación
        self.fields['status'].choices = [
            ('', 'Seleccionar decisión'),
            ('approved', '✅ Aprobar'),
            ('rejected', '❌ Rechazar'),
        ]

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        rejection_reason = cleaned_data.get('rejection_reason')

        if status == 'rejected' and not rejection_reason:
            raise ValidationError('Debe proporcionar un motivo para el rechazo.')

        return cleaned_data


class LeaveBalanceForm(forms.ModelForm):
    """
    Formulario para gestionar balances de licencias
    """
    class Meta:
        model = LeaveBalance
        fields = [
            'employee', 'leave_type', 'year', 'allocated_days',
            'used_days', 'carried_forward'
        ]
        widgets = {
            'employee': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400'
            }),
            'leave_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400'
            }),
            'year': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400',
                'min': '2020',
                'max': '2030'
            }),
            'allocated_days': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400',
                'min': '0',
                'placeholder': 'Días asignados'
            }),
            'used_days': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-200 rounded-lg bg-gray-50 text-gray-600 cursor-not-allowed shadow-sm',
                'min': '0',
                'readonly': True
            }),
            'carried_forward': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400',
                'min': '0',
                'placeholder': 'Días transferidos del año anterior'
            }),
        }
        labels = {
            'employee': 'Empleado',
            'leave_type': 'Tipo de Licencia',
            'year': 'Año',
            'allocated_days': 'Días Asignados',
            'used_days': 'Días Utilizados',
            'carried_forward': 'Días Transferidos'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar tipos de licencia activos
        self.fields['leave_type'].queryset = LeaveType.objects.filter(is_active=True)
        self.fields['leave_type'].empty_label = "Seleccionar tipo de licencia"
        
        # Año actual por defecto
        if not self.instance.pk:
            self.fields['year'].initial = datetime.now().year

    def clean(self):
        cleaned_data = super().clean()
        allocated_days = cleaned_data.get('allocated_days', 0)
        used_days = cleaned_data.get('used_days', 0)
        carried_forward = cleaned_data.get('carried_forward', 0)

        if used_days > allocated_days + carried_forward:
            raise ValidationError(
                'Los días utilizados no pueden exceder los días asignados más los transferidos.'
            )

        # Calcular días restantes automáticamente
        remaining_days = allocated_days + carried_forward - used_days
        cleaned_data['remaining_days'] = remaining_days

        return cleaned_data


class LeaveRequestFilterForm(forms.Form):
    """
    Formulario para filtrar solicitudes de licencia
    """
    employee = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="Todos los empleados",
        widget=forms.Select(attrs={
            'class': 'px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400 text-sm'
        })
    )
    
    leave_type = forms.ModelChoiceField(
        queryset=LeaveType.objects.filter(is_active=True),
        required=False,
        empty_label="Todos los tipos",
        widget=forms.Select(attrs={
            'class': 'px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400 text-sm'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'Todos los estados')] + LeaveRequest.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400 text-sm'
        })
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400 text-sm'
        }),
        label='Desde'
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400 text-sm'
        }),
        label='Hasta'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Importar aquí para evitar imports circulares
        from core.employees.models import Employee
        self.fields['employee'].queryset = Employee.objects.filter(status='active').order_by('user__first_name', 'user__last_name')


class LeaveTypeFilterForm(forms.Form):
    """
    Formulario para filtrar tipos de licencia
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400',
            'placeholder': '🔍 Buscar tipo de licencia...'
        }),
        label='Buscar'
    )
    
    is_paid = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('True', 'Pagadas'),
            ('False', 'No pagadas')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400 text-sm'
        }),
        label='Tipo'
    )
    
    requires_approval = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('True', 'Requiere aprobación'),
            ('False', 'No requiere aprobación')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400 text-sm'
        }),
        label='Aprobación'
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'Todos los estados'),
            ('active', 'Activos'),
            ('inactive', 'Inactivos')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors duration-200 bg-white shadow-sm hover:border-gray-400 text-sm'
        }),
        label='Estado'
    )