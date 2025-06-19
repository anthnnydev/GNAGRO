from django import forms
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta, time
from ..models import WorkSchedule, EmployeeSchedule, Holiday, AttendanceRule


class WorkScheduleForm(forms.ModelForm):
    """Formulario para horarios de trabajo"""
    
    class Meta:
        model = WorkSchedule
        fields = [
            'name', 'schedule_type', 'start_time', 'end_time', 
            'weekly_hours', 'late_tolerance',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'placeholder': 'Ej: Horario Administrativo Mañana'
            }),
            'schedule_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'type': 'time'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'type': 'time'
            }),
            'weekly_hours': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'step': '0.25',
                'min': '0'
            }),
            'late_tolerance': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'min': '0',
                'max': '60'
            }),
            'monday': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'tuesday': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'wednesday': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'thursday': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'friday': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'saturday': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'sunday': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Campo personalizado para duración del descanso
        self.fields['break_hours'] = forms.IntegerField(
            initial=1,
            min_value=0,
            max_value=8,
            required=False,
            widget=forms.NumberInput(attrs={
                'class': 'w-20 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'min': '0',
                'max': '8'
            }),
            help_text='Horas de descanso'
        )
        
        self.fields['break_minutes'] = forms.IntegerField(
            initial=0,
            min_value=0,
            max_value=59,
            required=False,
            widget=forms.NumberInput(attrs={
                'class': 'w-20 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'min': '0',
                'max': '59'
            }),
            help_text='Minutos de descanso'
        )
        
        # Si tenemos una instancia, extraer las horas y minutos del break_duration
        if self.instance and self.instance.pk and self.instance.break_duration:
            total_seconds = self.instance.break_duration.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            self.fields['break_hours'].initial = hours
            self.fields['break_minutes'].initial = minutes

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        break_hours = cleaned_data.get('break_hours', 0)
        break_minutes = cleaned_data.get('break_minutes', 0)
        
        # Validar que al menos un día esté seleccionado
        weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        if not any(cleaned_data.get(day, False) for day in weekdays):
            raise ValidationError('Debe seleccionar al menos un día de trabajo.')
        
        # Validar que la hora de fin sea posterior a la hora de inicio (si no es turno nocturno)
        if start_time and end_time:
            # Para turnos nocturnos, end_time puede ser menor que start_time
            if end_time <= start_time:
                # Verificar si es un turno nocturno válido
                schedule_type = cleaned_data.get('schedule_type')
                if schedule_type != 'shift':
                    raise ValidationError('La hora de fin debe ser posterior a la hora de inicio para horarios no nocturnos.')
        
        # Validar break_hours y break_minutes
        if break_hours is None:
            break_hours = 0
        if break_minutes is None:
            break_minutes = 0
            
        if break_hours < 0 or break_hours > 8:
            raise ValidationError('Las horas de descanso deben estar entre 0 y 8.')
            
        if break_minutes < 0 or break_minutes > 59:
            raise ValidationError('Los minutos de descanso deben estar entre 0 y 59.')
        
        # Asegurar que los valores estén en cleaned_data
        cleaned_data['break_hours'] = break_hours
        cleaned_data['break_minutes'] = break_minutes
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Asignar break_duration desde los campos separados
        break_hours = self.cleaned_data.get('break_hours', 0)
        break_minutes = self.cleaned_data.get('break_minutes', 0)
        
        # Asegurar que tenemos valores válidos
        if break_hours is None:
            break_hours = 0
        if break_minutes is None:
            break_minutes = 0
            
        instance.break_duration = timedelta(hours=int(break_hours), minutes=int(break_minutes))
        
        if commit:
            instance.save()
        return instance


class EmployeeScheduleForm(forms.ModelForm):
    """Formulario para asignación de horarios a empleados"""
    
    class Meta:
        model = EmployeeSchedule
        fields = ['employee', 'schedule', 'start_date', 'end_date', 'is_active', 'notes']
        widgets = {
            'employee': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
            }),
            'schedule': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'rows': 3,
                'placeholder': 'Notas adicionales sobre la asignación...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo horarios activos
        self.fields['schedule'].queryset = WorkSchedule.objects.filter(is_active=True)
        # Filtrar solo empleados activos usando el campo 'status' en lugar de 'is_active'
        # Asumiendo que 'active' es el valor para empleados activos
        self.fields['employee'].queryset = self.fields['employee'].queryset.filter(status='active')
        
    def clean(self):
        cleaned_data = super().clean()
        employee = cleaned_data.get('employee')
        schedule = cleaned_data.get('schedule')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # Validar que la fecha de fin sea posterior a la fecha de inicio
        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError('La fecha de fin debe ser posterior a la fecha de inicio.')
        
        # Validar que no exista otra asignación activa para el mismo empleado en el mismo período
        if employee and schedule and start_date:
            existing_assignments = EmployeeSchedule.objects.filter(
                employee=employee,
                is_active=True
            )
            
            # Si estamos editando, excluir la instancia actual
            if self.instance and self.instance.pk:
                existing_assignments = existing_assignments.exclude(pk=self.instance.pk)
            
            # Verificar solapamiento de fechas
            for assignment in existing_assignments:
                assignment_end = assignment.end_date if assignment.end_date else datetime.date.today() + timedelta(days=365)
                current_end = end_date if end_date else datetime.date.today() + timedelta(days=365)
                
                if (start_date <= assignment_end and current_end >= assignment.start_date):
                    raise ValidationError(
                        f'Ya existe una asignación activa para {employee} que se solapa con estas fechas. '
                        f'Asignación existente: {assignment.start_date} - {assignment.end_date or "Sin fecha fin"}'
                    )
        
        return cleaned_data


class HolidayForm(forms.ModelForm):
    """Formulario para feriados"""
    
    class Meta:
        model = Holiday
        fields = ['name', 'date', 'is_recurring', 'is_paid', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'placeholder': 'Ej: Año Nuevo, Día del Trabajador'
            }),
            'date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'type': 'date'
            }),
            'is_recurring': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'is_paid': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'rows': 3,
                'placeholder': 'Descripción del feriado...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
        }


class AttendanceRuleForm(forms.ModelForm):
    """Formulario para reglas de asistencia"""
    
    class Meta:
        model = AttendanceRule
        fields = [
            'name', 'late_threshold', 'overtime_threshold', 'overtime_multiplier',
            'max_consecutive_absences', 'require_justification', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'placeholder': 'Ej: Reglas Administrativas, Reglas Operativas'
            }),
            'late_threshold': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'min': '0',
                'max': '120'
            }),
            'overtime_threshold': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'step': '0.25',
                'min': '0'
            }),
            'overtime_multiplier': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'step': '0.25',
                'min': '1.0'
            }),
            'max_consecutive_absences': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
                'min': '1',
                'max': '30'
            }),
            'require_justification': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
        }


class WorkScheduleSearchForm(forms.Form):
    """Formulario de búsqueda para horarios"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors',
            'placeholder': 'Buscar por nombre o tipo...'
        })
    )
    
    schedule_type = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos los tipos')] + WorkSchedule.SCHEDULE_TYPES,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
        })
    )
    
    is_active = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Todos'),
            ('true', 'Activos'),
            ('false', 'Inactivos')
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
        })
    )