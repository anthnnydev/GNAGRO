# Crear archivo: core/external_payments/forms.py

from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import ExternalWorker, ExternalPayment, ServiceType, ExternalPaymentDocument


class ExternalWorkerForm(forms.ModelForm):
    """Formulario para trabajadores externos"""
    
    class Meta:
        model = ExternalWorker
        fields = [
            'full_name', 'identification_type', 'identification_number',
            'phone', 'email', 'address', 'has_ruc', 'ruc_number', 
            'has_rise', 'business_name', 'notes'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo del trabajador'
            }),
            'identification_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'identification_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de identificación'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono de contacto'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dirección completa'
            }),
            'has_ruc': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'ruc_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1234567890001'
            }),
            'has_rise': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'business_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Razón social o nombre comercial'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones adicionales'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Campos requeridos
        self.fields['full_name'].required = True
        self.fields['identification_number'].required = True
        
        # Labels personalizados
        self.fields['full_name'].label = 'Nombre Completo *'
        self.fields['identification_type'].label = 'Tipo de Identificación *'
        self.fields['identification_number'].label = 'Número de Identificación *'
        self.fields['phone'].label = 'Teléfono'
        self.fields['email'].label = 'Email'
        self.fields['address'].label = 'Dirección'
        self.fields['has_ruc'].label = 'Tiene RUC'
        self.fields['ruc_number'].label = 'Número de RUC'
        self.fields['has_rise'].label = 'Tiene RISE'
        self.fields['business_name'].label = 'Razón Social'
        self.fields['notes'].label = 'Observaciones'
    
    def clean_identification_number(self):
        identification = self.cleaned_data.get('identification_number')
        
        if identification:
            # Verificar que no exista otro trabajador con la misma identificación
            existing = ExternalWorker.objects.filter(
                identification_number=identification
            )
            
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError('Ya existe un trabajador con este número de identificación.')
        
        return identification
    
    def clean_ruc_number(self):
        ruc_number = self.cleaned_data.get('ruc_number')
        has_ruc = self.cleaned_data.get('has_ruc')
        
        if has_ruc and not ruc_number:
            raise ValidationError('Debe ingresar el número de RUC.')
        
        if ruc_number and len(ruc_number) != 13:
            raise ValidationError('El RUC debe tener 13 dígitos.')
        
        return ruc_number
    
    def clean(self):
        cleaned_data = super().clean()
        has_ruc = cleaned_data.get('has_ruc')
        has_rise = cleaned_data.get('has_rise')
        
        if has_ruc and has_rise:
            raise ValidationError('No puede tener RUC y RISE al mismo tiempo.')
        
        return cleaned_data


class ExternalPaymentForm(forms.ModelForm):
    """Formulario para pagos externos"""
    
    class Meta:
        model = ExternalPayment
        fields = [
            'external_worker', 'service_type', 'work_description',
            'start_date', 'end_date', 'quantity', 'unit', 'unit_rate',
            'amount', 'has_invoice', 'invoice_number', 'invoice_date',
            'tax_withheld', 'notes'
        ]
        widgets = {
            'external_worker': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Seleccionar trabajador...'
            }),
            'service_type': forms.Select(attrs={
                'class': 'form-control',
                'data-placeholder': 'Seleccionar tipo de servicio...'
            }),
            'work_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describa detalladamente el trabajo realizado'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'unit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'día, hectárea, metro, etc.'
            }),
            'unit_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'readonly': True
            }),
            'has_invoice': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'invoice_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '001-001-000123456'
            }),
            'invoice_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'tax_withheld': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones adicionales'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar querysets
        self.fields['external_worker'].queryset = ExternalWorker.objects.filter(
            is_active=True
        ).order_by('full_name')
        
        self.fields['service_type'].queryset = ServiceType.objects.filter(
            is_active=True
        ).order_by('name')
        
        # Labels personalizados
        self.fields['external_worker'].label = 'Trabajador Externo *'
        self.fields['service_type'].label = 'Tipo de Servicio *'
        self.fields['work_description'].label = 'Descripción del Trabajo *'
        self.fields['start_date'].label = 'Fecha de Inicio *'
        self.fields['end_date'].label = 'Fecha de Fin *'
        self.fields['quantity'].label = 'Cantidad *'
        self.fields['unit'].label = 'Unidad *'
        self.fields['unit_rate'].label = 'Tarifa por Unidad *'
        self.fields['amount'].label = 'Monto Total'
        self.fields['has_invoice'].label = 'Emitió Factura'
        self.fields['invoice_number'].label = 'Número de Factura'
        self.fields['invoice_date'].label = 'Fecha de Factura'
        self.fields['tax_withheld'].label = 'Retención de Impuestos'
        self.fields['notes'].label = 'Observaciones'
        
        # Help texts
        self.fields['quantity'].help_text = 'Cantidad de unidades trabajadas'
        self.fields['unit_rate'].help_text = 'Precio por unidad'
        self.fields['amount'].help_text = 'Se calcula automáticamente (cantidad × tarifa)'
        self.fields['tax_withheld'].help_text = 'Retención aplicada según normativa vigente'
    
    def clean_end_date(self):
        start_date = self.cleaned_data.get('start_date')
        end_date = self.cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError('La fecha de fin no puede ser anterior a la fecha de inicio.')
        
        return end_date
    
    def clean_invoice_number(self):
        has_invoice = self.cleaned_data.get('has_invoice')
        invoice_number = self.cleaned_data.get('invoice_number')
        
        if has_invoice and not invoice_number:
            raise ValidationError('Debe ingresar el número de factura.')
        
        return invoice_number
    
    def clean_invoice_date(self):
        has_invoice = self.cleaned_data.get('has_invoice')
        invoice_date = self.cleaned_data.get('invoice_date')
        
        if has_invoice and not invoice_date:
            raise ValidationError('Debe ingresar la fecha de factura.')
        
        return invoice_date
    
    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        unit_rate = cleaned_data.get('unit_rate')
        amount = cleaned_data.get('amount')
        
        # Calcular monto automáticamente
        if quantity and unit_rate:
            calculated_amount = quantity * unit_rate
            cleaned_data['amount'] = calculated_amount
        
        # Validar que el trabajador puede emitir factura si se requiere
        external_worker = cleaned_data.get('external_worker')
        has_invoice = cleaned_data.get('has_invoice')
        
        if has_invoice and external_worker and not external_worker.can_issue_invoice:
            raise ValidationError(
                f'{external_worker.full_name} no puede emitir facturas (no tiene RUC ni RISE).'
            )
        
        return cleaned_data


class ServiceTypeForm(forms.ModelForm):
    """Formulario para tipos de servicios"""
    
    class Meta:
        model = ServiceType
        fields = [
            'name', 'description', 'default_unit', 'default_rate', 
            'requires_invoice'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Cosecha de maíz'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción detallada del servicio'
            }),
            'default_unit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'día, hectárea, metro, quintal, etc.'
            }),
            'default_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'requires_invoice': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Labels
        self.fields['name'].label = 'Nombre del Servicio *'
        self.fields['description'].label = 'Descripción'
        self.fields['default_unit'].label = 'Unidad por Defecto *'
        self.fields['default_rate'].label = 'Tarifa por Defecto'
        self.fields['requires_invoice'].label = 'Requiere Factura Obligatoria'
        
        # Help texts
        self.fields['default_rate'].help_text = 'Tarifa sugerida por unidad'
        self.fields['requires_invoice'].help_text = 'Marcar si siempre debe emitirse factura para este servicio'


class ExternalPaymentDocumentForm(forms.ModelForm):
    """Formulario para documentos de pagos externos"""
    
    class Meta:
        model = ExternalPaymentDocument
        fields = ['document_type', 'name', 'file', 'description']
        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del documento'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Descripción opcional'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['document_type'].label = 'Tipo de Documento *'
        self.fields['name'].label = 'Nombre del Documento *'
        self.fields['file'].label = 'Archivo *'
        self.fields['description'].label = 'Descripción'


class ExternalPaymentFilterForm(forms.Form):
    """Formulario para filtros de búsqueda de pagos externos"""
    
    STATUS_CHOICES = [
        ('', 'Todos los estados'),
        ('pending', 'Pendientes'),
        ('paid', 'Pagados'),
        ('cancelled', 'Cancelados'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por trabajador, descripción o factura...'
        })
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.filter(is_active=True),
        required=False,
        empty_label="Todos los servicios",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    worker = forms.ModelChoiceField(
        queryset=ExternalWorker.objects.filter(is_active=True),
        required=False,
        empty_label="Todos los trabajadores",
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


class BulkPaymentForm(forms.Form):
    """Formulario para marcar múltiples pagos como realizados"""
    
    PAYMENT_METHODS = [
        ('cash', 'Efectivo'),
        ('transfer', 'Transferencia Bancaria'),
        ('check', 'Cheque'),
        ('other', 'Otro'),
    ]
    
    payment_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Fecha de Pago'
    )
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHODS,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Método de Pago'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Fecha por defecto es hoy
        from django.utils import timezone
        self.fields['payment_date'].initial = timezone.now().date()