# core/positions/models.py
from django.db import models
from decimal import Decimal

class Position(models.Model):
    """
    Modelo para cargos/posiciones en la empresa  
    """
    LEVEL_CHOICES = [
        ('entry', 'Nivel de Entrada'),
        ('junior', 'Junior'),
        ('mid', 'Intermedio'),
        ('senior', 'Senior'),
        ('lead', 'Líder'),
        ('manager', 'Gerente'),
        ('director', 'Director'),
        ('executive', 'Ejecutivo'),
    ]
    
    title = models.CharField(
        max_length=100,
        verbose_name='Título del Cargo'
    )
    
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código del Cargo'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción del Cargo'
    )
    
    requirements = models.TextField(
        blank=True,
        verbose_name='Requisitos'
    )
    
    responsibilities = models.TextField(
        blank=True,
        verbose_name='Responsabilidades'
    )
    
    level = models.CharField(
        max_length=15,
        choices=LEVEL_CHOICES,
        default='entry',
        verbose_name='Nivel'
    )
    
    min_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Salario Mínimo'
    )
    
    max_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Salario Máximo'
    )
    
    is_supervisory = models.BooleanField(
        default=False,
        verbose_name='Cargo de Supervisión'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Cargo'
        verbose_name_plural = 'Cargos'
        db_table = 'positions_position'
        ordering = ['title']
    
    def __str__(self):
        return self.title
    
    @property
    def salary_range(self):
        """Rango salarial formateado"""
        return f"${self.min_salary:,.2f} - ${self.max_salary:,.2f}"


class PositionSkill(models.Model):
    """
    Habilidades/competencias requeridas para un cargo
    """
    SKILL_TYPES = [
        ('technical', 'Técnica'),
        ('soft', 'Blanda'),
        ('certification', 'Certificación'),
        ('language', 'Idioma'),
    ]
    
    PROFICIENCY_LEVELS = [
        ('basic', 'Básico'),
        ('intermediate', 'Intermedio'),
        ('advanced', 'Avanzado'),
        ('expert', 'Experto'),
    ]
    
    position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        related_name='skills',
        verbose_name='Cargo'
    )
    
    skill_name = models.CharField(
        max_length=100,
        verbose_name='Nombre de la Habilidad'
    )
    
    skill_type = models.CharField(
        max_length=15,
        choices=SKILL_TYPES,
        verbose_name='Tipo'
    )
    
    required_level = models.CharField(
        max_length=15,
        choices=PROFICIENCY_LEVELS,
        verbose_name='Nivel Requerido'
    )
    
    is_mandatory = models.BooleanField(
        default=False,
        verbose_name='Obligatorio'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Habilidad del Cargo'
        verbose_name_plural = 'Habilidades del Cargo'
        db_table = 'positions_skill'
        unique_together = ['position', 'skill_name']
    
    def __str__(self):
        return f"{self.skill_name} ({self.position.title})"


class PositionHistory(models.Model):
    """
    Historial de cambios en los cargos
    """
    position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name='Cargo'
    )
    
    field_changed = models.CharField(
        max_length=50,
        verbose_name='Campo Modificado'
    )
    
    old_value = models.TextField(
        blank=True,
        verbose_name='Valor Anterior'
    )
    
    new_value = models.TextField(
        blank=True,
        verbose_name='Valor Nuevo'
    )
    
    changed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Modificado por'
    )
    
    change_reason = models.TextField(
        blank=True,
        verbose_name='Razón del Cambio'
    )
    
    changed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Historial de Cargo'
        verbose_name_plural = 'Historiales de Cargo'
        db_table = 'positions_history'
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.position.title} - {self.field_changed}"