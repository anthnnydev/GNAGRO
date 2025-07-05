# core/payroll/forms/period_forms.py
from django import forms
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from calendar import monthrange
from ..models import PayrollPeriod

class PayrollPeriodForm(forms.ModelForm):
    """Formulario para períodos de nómina con coordinación automática de fechas"""
    
    class Meta:
        model = PayrollPeriod
        fields = [
            'name', 'period_type', 'start_date', 'end_date', 
            'pay_date', 'status', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Ej: Enero 2024, Quincena 1 - Enero 2024',
                'id': 'id_name'  # ← Agregar
            }),
            'period_type': forms.Select(attrs={
                'class': 'w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'id': 'id_period_type'  # ← Agregar
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'type': 'date',
                'id': 'id_start_date'  # ← Agregar
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'type': 'date',
                'id': 'id_end_date'  # ← Agregar
            }),
            'pay_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'type': 'date',
                'id': 'id_pay_date'  # ← Agregar
            }),
            'status': forms.Select(attrs={
                'class': 'w-full py-2 px-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'id': 'id_status'  # ← Agregar
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-vertical',
                'rows': 3,
                'placeholder': 'Información adicional sobre este período...',
                'id': 'id_notes'  # ← Agregar
            }),
        }
        labels = {
            'name': 'Nombre del Período',
            'period_type': 'Tipo de Período',
            'start_date': 'Fecha de Inicio',
            'end_date': 'Fecha de Fin',
            'pay_date': 'Fecha de Pago',
            'status': 'Estado',
            'notes': 'Notas',
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        pay_date = cleaned_data.get('pay_date')
        period_type = cleaned_data.get('period_type')

        # Validar fechas básicas
        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError('La fecha de fin debe ser posterior a la fecha de inicio.')

        if end_date and pay_date:
            if pay_date < end_date:
                raise ValidationError('La fecha de pago debe ser igual o posterior a la fecha de fin.')

        # Validar coherencia con tipo de período
        if start_date and end_date and period_type:
            days_diff = (end_date - start_date).days + 1
            
            if period_type == 'weekly' and days_diff != 7:
                raise ValidationError('Un período semanal debe tener exactamente 7 días.')
            
            elif period_type == 'biweekly':
                if days_diff < 14 or days_diff > 16:
                    raise ValidationError('Un período quincenal debe tener entre 14 y 16 días.')
            
            elif period_type == 'monthly':
                month_days = monthrange(start_date.year, start_date.month)[1]
                if start_date.day != 1 or end_date.day != month_days:
                    raise ValidationError(
                        'Un período mensual debe comenzar el día 1 y terminar el último día del mes.'
                    )

        # Validar solapamiento con otros períodos
        existing_periods = PayrollPeriod.objects.filter(
            start_date__lte=end_date,
            end_date__gte=start_date
        )
        
        if self.instance and self.instance.pk:
            existing_periods = existing_periods.exclude(pk=self.instance.pk)
        
        if existing_periods.exists():
            period_names = ', '.join([p.name for p in existing_periods[:3]])
            raise ValidationError(
                f'Este período se solapa con períodos existentes: {period_names}'
            )

        return cleaned_data

    def suggest_dates_for_period_type(self, period_type, reference_date):
        """Sugerir fechas automáticamente según el tipo de período"""
        if period_type == 'monthly':
            start_date = reference_date.replace(day=1)
            end_date = reference_date.replace(
                day=monthrange(reference_date.year, reference_date.month)[1]
            )
            pay_date = end_date + timedelta(days=5)
            
        elif period_type == 'biweekly':
            if reference_date.day <= 15:
                # Primera quincena
                start_date = reference_date.replace(day=1)
                end_date = reference_date.replace(day=15)
            else:
                # Segunda quincena
                start_date = reference_date.replace(day=16)
                end_date = reference_date.replace(
                    day=monthrange(reference_date.year, reference_date.month)[1]
                )
            pay_date = end_date + timedelta(days=3)
            
        elif period_type == 'weekly':
            # Calcular el lunes de la semana
            days_since_monday = reference_date.weekday()
            start_date = reference_date - timedelta(days=days_since_monday)
            end_date = start_date + timedelta(days=6)
            pay_date = end_date + timedelta(days=3)
            
        else:
            return None, None, None
            
        return start_date, end_date, pay_date