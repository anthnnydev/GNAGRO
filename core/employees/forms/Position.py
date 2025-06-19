# core/employees/forms.py
from django import forms
from django.contrib.auth import get_user_model
from ..models import Department, Position, Employee

User = get_user_model()


class DepartmentForm(forms.ModelForm):
    """
    Formulario para crear y editar departamentos
    """
    class Meta:
        model = Department
        fields = ['name', 'description', 'manager', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Nombre del departamento'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Descripción del departamento',
                'rows': 4
            }),
            'manager': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
            })
        }
        labels = {
            'name': 'Nombre del Departamento',
            'description': 'Descripción',
            'manager': 'Jefe de Departamento',
            'is_active': 'Activo'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo usuarios que son empleados para el campo manager
        self.fields['manager'].queryset = User.objects.filter(
            employee_profile__isnull=False,
            is_active=True
        ).order_by('first_name', 'last_name')
        self.fields['manager'].empty_label = "Seleccionar jefe de departamento"
        
        # Hacer que ciertos campos sean requeridos
        self.fields['name'].required = True

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip().title()
            # Verificar si ya existe otro departamento con el mismo nombre
            qs = Department.objects.filter(name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Ya existe un departamento con este nombre.')
        return name


class PositionForm(forms.ModelForm):
    """
    Formulario para crear y editar cargos/posiciones
    """
    class Meta:
        model = Position
        fields = ['title', 'department', 'description', 'base_salary', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Título del cargo'
            }),
            'department': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'placeholder': 'Descripción del cargo, responsabilidades, requisitos...',
                'rows': 4
            }),
            'base_salary': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
            })
        }
        labels = {
            'title': 'Título del Cargo',
            'department': 'Departamento',
            'description': 'Descripción del Cargo',
            'base_salary': 'Salario Base',
            'is_active': 'Activo'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo departamentos activos
        self.fields['department'].queryset = Department.objects.filter(
            is_active=True
        ).order_by('name')
        self.fields['department'].empty_label = "Seleccionar departamento"
        
        # Hacer que ciertos campos sean requeridos
        self.fields['title'].required = True
        self.fields['department'].required = True
        self.fields['base_salary'].required = True

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if title:
            title = title.strip().title()
        return title

    def clean_base_salary(self):
        base_salary = self.cleaned_data.get('base_salary')
        if base_salary is not None and base_salary < 0:
            raise forms.ValidationError('El salario base no puede ser negativo.')
        return base_salary

    def clean(self):
        cleaned_data = super().clean()
        title = cleaned_data.get('title')
        department = cleaned_data.get('department')
        
        if title and department:
            # Verificar si ya existe un cargo con el mismo título en el mismo departamento
            qs = Position.objects.filter(title__iexact=title, department=department)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('Ya existe un cargo con este título en el departamento seleccionado.')
        
        return cleaned_data


class DepartmentFilterForm(forms.Form):
    """
    Formulario para filtrar departamentos
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            'placeholder': 'Buscar departamento...'
        })
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'Todos los estados'),
            ('active', 'Activos'),
            ('inactive', 'Inactivos')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
        })
    )


class PositionFilterForm(forms.Form):
    """
    Formulario para filtrar cargos/posiciones
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            'placeholder': 'Buscar cargo...'
        })
    )
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True).order_by('name'),
        required=False,
        empty_label='Todos los departamentos',
        widget=forms.Select(attrs={
            'class': 'px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
        })
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'Todos los estados'),
            ('active', 'Activos'),
            ('inactive', 'Inactivos')
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
        })
    )
    
    salary_min = forms.DecimalField(
        required=False,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={
            'class': 'px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            'placeholder': 'Salario mínimo'
        })
    )
    
    salary_max = forms.DecimalField(
        required=False,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={
            'class': 'px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500',
            'placeholder': 'Salario máximo'
        })
    )