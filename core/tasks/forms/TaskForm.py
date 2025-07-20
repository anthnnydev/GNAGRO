# core/tasks/forms/TaskForm.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q  # AGREGADO: Importar Q
from datetime import datetime, timedelta
from ..models import Task, TaskCategory, TaskAssignment, TaskProgress, TaskComment
from core.employees.models import Employee


class TaskForm(forms.ModelForm):
    """Formulario para crear y editar tareas"""
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'category', 'start_date', 'end_date',
            'estimated_hours', 'location', 'payment_type', 'hourly_rate',
            'fixed_amount', 'unit_rate', 'unit_description', 'priority',
            'special_instructions', 'reference_image'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'placeholder': 'Ej: Deshoje de plantas de plátano - Lote 5'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'rows': 4,
                'placeholder': 'Describe detalladamente la tarea a realizar...'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500'
            }),
            'estimated_hours': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'step': 'any',
                'min': '0.1',
                'placeholder': '8'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'placeholder': 'Ej: Lote 5, Sector Norte, Invernadero 3'
            }),
            'payment_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500'
            }),
            'hourly_rate': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'step': '0.01',
                'min': '0',
                'placeholder': '5.50'
            }),
            'fixed_amount': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'step': '0.01',
                'min': '0',
                'placeholder': '100.00'
            }),
            'unit_rate': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.50'
            }),
            'unit_description': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'placeholder': 'por planta, por metro, por kilo'
            }),
            'priority': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500'
            }),
            'special_instructions': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'rows': 3,
                'placeholder': 'Herramientas necesarias, precauciones especiales, etc.'
            }),
            'reference_image': forms.FileInput(attrs={
                'class': 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-green-50 file:text-green-700 hover:file:bg-green-100',
                'accept': 'image/*'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.supervisor = kwargs.pop('supervisor', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar categorías activas
        self.fields['category'].queryset = TaskCategory.objects.filter(is_active=True)
        
        # Establecer valores por defecto para fechas
        if not self.instance.pk:
            now = timezone.now()
            self.fields['start_date'].initial = now.replace(minute=0, second=0, microsecond=0)
            self.fields['end_date'].initial = (now + timedelta(hours=8)).replace(minute=0, second=0, microsecond=0)
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        payment_type = cleaned_data.get('payment_type')
        hourly_rate = cleaned_data.get('hourly_rate')
        fixed_amount = cleaned_data.get('fixed_amount')
        unit_rate = cleaned_data.get('unit_rate')
        unit_description = cleaned_data.get('unit_description')
        
        # Validar fechas
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError("La fecha de fin debe ser posterior a la fecha de inicio.")
            
            # No permitir crear tareas muy en el pasado (más de 1 día)
            if start_date < timezone.now() - timedelta(days=1):
                raise ValidationError("No se pueden crear tareas con fecha de inicio muy en el pasado.")
        
        # Validar campos de pago según el tipo
        if payment_type == 'hourly' and not hourly_rate:
            raise ValidationError("Debe especificar la tarifa por hora.")
        elif payment_type == 'fixed' and not fixed_amount:
            raise ValidationError("Debe especificar el monto fijo.")
        elif payment_type == 'unit':
            if not unit_rate:
                raise ValidationError("Debe especificar la tarifa por unidad.")
            if not unit_description:
                raise ValidationError("Debe describir la unidad de medida.")
        
        return cleaned_data
    
    def save(self, commit=True):
        task = super().save(commit=False)
        if self.supervisor:
            task.supervisor = self.supervisor
        if commit:
            task.save()
        return task


class TaskAssignmentForm(forms.Form):
    """Formulario para asignar empleados a una tarea"""
    
    employees = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300 rounded'
        }),
        label="Seleccionar Empleados"
    )
    
    def __init__(self, *args, **kwargs):
        task = kwargs.pop('task', None)
        supervisor = kwargs.pop('supervisor', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar empleados disponibles (activos y no asignados a esta tarea)
        queryset = Employee.objects.filter(
            status='active',
            user__user_type='employee'
        ).select_related('user', 'position', 'department')
        
        if task:
            # Excluir empleados ya asignados a esta tarea
            already_assigned = task.assigned_employees.values_list('id', flat=True)
            queryset = queryset.exclude(id__in=already_assigned)
        
        # Si es supervisor, puede asignar a empleados de su departamento o subordinados
        if supervisor and supervisor.user.user_type == 'supervisor':
            queryset = queryset.filter(
                Q(department=supervisor.department) |
                Q(supervisor=supervisor)
            )
        
        self.fields['employees'].queryset = queryset
        
        # Personalizar las etiquetas para mostrar más información
        self.fields['employees'].label_from_instance = self.employee_label
    
    def employee_label(self, employee):
        return f"{employee.user.get_full_name()} - {employee.position.title} ({employee.department.name})"


class TaskProgressForm(forms.ModelForm):
    """Formulario para reportar progreso de una tarea - CORREGIDO"""
    
    class Meta:
        model = TaskProgress
        fields = [
            'progress_description', 'progress_image', 'hours_worked_session',
            'units_completed_session'
        ]
        widgets = {
            'progress_description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'rows': 4,
                'placeholder': 'Describe el progreso realizado en esta sesión...',
                'required': True
            }),
            'progress_image': forms.FileInput(attrs={
                'class': 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
                'accept': 'image/*'
            }),
            'hours_worked_session': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'step': '0.1',
                'min': '0',
                'placeholder': '2.5'
            }),
            'units_completed_session': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'min': '0',
                'placeholder': '0'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.assignment = kwargs.pop('assignment', None)
        super().__init__(*args, **kwargs)
        
        # CORREGIDO: Configurar campos según el tipo de pago de la tarea
        if self.assignment and self.assignment.task:
            task = self.assignment.task
            payment_type = task.payment_type
            
            print(f"🔧 Configurando formulario para tipo de pago: {payment_type}")
            
            if payment_type == 'hourly':
                # Para pago por hora: horas son obligatorias, unidades no
                self.fields['hours_worked_session'].required = True
                self.fields['units_completed_session'].required = False
                self.fields['units_completed_session'].widget = forms.HiddenInput()
                print("⏰ Configurado para pago por hora")
                
            elif payment_type == 'unit':
                # Para pago por unidad: unidades son obligatorias, horas opcionales
                self.fields['units_completed_session'].required = True
                self.fields['units_completed_session'].label = f"Unidades completadas ({task.unit_description})"
                self.fields['hours_worked_session'].required = False
                print(f"📦 Configurado para pago por unidad: {task.unit_description}")
                
            elif payment_type == 'fixed':
                # Para pago fijo: horas opcionales, unidades no aplican
                self.fields['hours_worked_session'].required = False
                self.fields['units_completed_session'].required = False
                self.fields['units_completed_session'].widget = forms.HiddenInput()
                print("💰 Configurado para pago fijo")
            
            else:
                # Fallback: hacer ambos opcionales
                self.fields['hours_worked_session'].required = False
                self.fields['units_completed_session'].required = False
                print(f"❓ Tipo de pago desconocido: {payment_type}")
        
        else:
            # Sin assignment: hacer ambos campos opcionales
            self.fields['hours_worked_session'].required = False
            self.fields['units_completed_session'].required = False
            print("⚠️ No hay assignment - ambos campos opcionales")
        
        # La descripción del progreso siempre es obligatoria
        self.fields['progress_description'].required = True
    
    def clean(self):
        """Validación personalizada"""
        cleaned_data = super().clean()
        
        if not self.assignment:
            return cleaned_data
        
        task = self.assignment.task
        payment_type = task.payment_type
        
        hours_worked = cleaned_data.get('hours_worked_session')
        units_completed = cleaned_data.get('units_completed_session')
        progress_description = cleaned_data.get('progress_description')
        
        # Validar que haya descripción
        if not progress_description or not progress_description.strip():
            raise forms.ValidationError("Debes proporcionar una descripción del progreso.")
        
        # Validaciones específicas por tipo de pago
        if payment_type == 'hourly':
            if not hours_worked or hours_worked <= 0:
                raise forms.ValidationError("Debes especificar las horas trabajadas para tareas con pago por hora.")
        
        elif payment_type == 'unit':
            if not units_completed or units_completed <= 0:
                raise forms.ValidationError(f"Debes especificar las {task.unit_description} completadas.")
        
        elif payment_type == 'fixed':
            # Para pago fijo, al menos uno de los dos campos debe tener valor
            if not hours_worked and not units_completed:
                raise forms.ValidationError("Debes especificar horas trabajadas o unidades completadas.")
        
        # Validar valores negativos
        if hours_worked and hours_worked < 0:
            raise forms.ValidationError("Las horas trabajadas no pueden ser negativas.")
        
        if units_completed and units_completed < 0:
            raise forms.ValidationError("Las unidades completadas no pueden ser negativas.")
        
        return cleaned_data
    
    def save(self, commit=True):
        """Guardar con valores por defecto para campos opcionales"""
        progress = super().save(commit=False)
        
        # Asegurar valores por defecto para evitar NULL
        if not progress.hours_worked_session:
            progress.hours_worked_session = 0
        
        if not progress.units_completed_session:
            progress.units_completed_session = 0
        
        if commit:
            progress.save()
        
        return progress


class TaskCommentForm(forms.ModelForm):
    """Formulario para comentarios en tareas"""
    
    class Meta:
        model = TaskComment
        fields = ['content', 'is_private', 'attachment']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'rows': 3,
                'placeholder': 'Escribe tu comentario...'
            }),
            'is_private': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-purple-600 focus:ring-purple-500 border-gray-300 rounded'
            }),
            'attachment': forms.FileInput(attrs={
                'class': 'w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.author = kwargs.pop('author', None)
        super().__init__(*args, **kwargs)
        
        # Solo supervisores y admins pueden hacer comentarios privados
        if self.author and self.author.user.user_type not in ['supervisor', 'admin', 'hr']:
            self.fields['is_private'].widget = forms.HiddenInput()


class TaskCategoryForm(forms.ModelForm):
    """Formulario para crear categorías de tareas"""
    
    class Meta:
        model = TaskCategory
        fields = ['name', 'description', 'icon', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'placeholder': 'Ej: Deshoje, Coronar, Abonar'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'rows': 3,
                'placeholder': 'Describe esta categoría de tareas...'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500',
                'placeholder': 'fas fa-leaf'
            }),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'h-10 w-20 border border-gray-300 rounded-lg'
            })
        }


class TaskSearchForm(forms.Form):
    """Formulario para buscar y filtrar tareas"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Buscar por título, descripción o ubicación...'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=TaskCategory.objects.filter(is_active=True),
        required=False,
        empty_label="Todas las categorías",
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'Todos los estados')] + Task.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
        })
    )
    
    priority = forms.ChoiceField(
        choices=[('', 'Todas las prioridades')] + Task.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
        })
    )