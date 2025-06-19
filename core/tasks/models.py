# core/tasks/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import datetime, time, timedelta

class TaskCategory(models.Model):
    """Categorías de tareas agrícolas"""
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre de la Categoría'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    icon = models.CharField(
        max_length=50,
        default='fas fa-leaf',
        verbose_name='Icono FontAwesome',
        help_text='Ejemplo: fas fa-leaf, fas fa-seedling'
    )
    
    color = models.CharField(
        max_length=7,
        default='#10B981',
        verbose_name='Color',
        help_text='Color en formato hexadecimal #RRGGBB'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Categoría de Tarea'
        verbose_name_plural = 'Categorías de Tareas'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Task(models.Model):
    """Modelo principal para tareas agrícolas"""
    
    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('assigned', 'Asignada'),
        ('in_progress', 'En Progreso'),
        ('paused', 'Pausada'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('hourly', 'Por Hora'),
        ('fixed', 'Precio Fijo'),
        ('unit', 'Por Unidad'),
    ]
    
    # Información básica
    title = models.CharField(
        max_length=200,
        verbose_name='Título de la Tarea'
    )
    
    description = models.TextField(
        verbose_name='Descripción Detallada'
    )
    
    category = models.ForeignKey(
        TaskCategory,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='Categoría'
    )
    
    # Asignación
    supervisor = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='supervised_tasks',
        verbose_name='Supervisor',
        limit_choices_to={'user__user_type__in': ['supervisor', 'admin']}
    )
    
    assigned_employees = models.ManyToManyField(
        'employees.Employee',
        through='TaskAssignment',
        related_name='assigned_tasks',
        verbose_name='Empleados Asignados'
    )
    
    # Tiempo y ubicación
    start_date = models.DateTimeField(
        verbose_name='Fecha y Hora de Inicio'
    )
    
    end_date = models.DateTimeField(
        verbose_name='Fecha y Hora de Fin'
    )
    
    estimated_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Horas Estimadas'
    )
    
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Ubicación/Sector',
        help_text='Ej: Lote 5, Sector Norte, Invernadero 3'
    )
    
    # Pago y prioridad
    payment_type = models.CharField(
        max_length=10,
        choices=PAYMENT_TYPE_CHOICES,
        default='hourly',
        verbose_name='Tipo de Pago'
    )
    
    hourly_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Tarifa por Hora'
    )
    
    fixed_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Monto Fijo'
    )
    
    unit_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Tarifa por Unidad'
    )
    
    unit_description = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Descripción de la Unidad',
        help_text='Ej: por planta, por metro, por kilo'
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name='Prioridad'
    )
    
    # Estado y seguimiento
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Estado'
    )
    
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Porcentaje de Progreso'
    )
    
    # Instrucciones especiales
    special_instructions = models.TextField(
        blank=True,
        verbose_name='Instrucciones Especiales',
        help_text='Herramientas necesarias, precauciones, etc.'
    )
    
    # Adjuntos y referencias
    reference_image = models.ImageField(
        upload_to='task_references/',
        null=True,
        blank=True,
        verbose_name='Imagen de Referencia'
    )
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Finalización'
    )
    
    class Meta:
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['supervisor']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    @property
    def is_overdue(self):
        """Verifica si la tarea está vencida"""
        if self.status in ['completed', 'cancelled']:
            return False
        return datetime.now() > self.end_date
    
    @property
    def duration_hours(self):
        """Calcula la duración en horas"""
        duration = self.end_date - self.start_date
        return duration.total_seconds() / 3600
    
    @property
    def total_assigned_employees(self):
        """Número total de empleados asignados"""
        return self.assigned_employees.count()
    
    def get_payment_display_info(self):
        """Retorna información formateada del pago"""
        if self.payment_type == 'hourly':
            return f"${self.hourly_rate}/hora"
        elif self.payment_type == 'fixed':
            return f"${self.fixed_amount} (fijo)"
        elif self.payment_type == 'unit':
            return f"${self.unit_rate}/{self.unit_description}"
        return "No especificado"


class TaskAssignment(models.Model):
    """Modelo intermedio para asignación de tareas"""
    
    ASSIGNMENT_STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('accepted', 'Aceptada'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completada'),
        ('rejected', 'Rechazada'),
    ]
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='task_assignments'
    )
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(
        max_length=15,
        choices=ASSIGNMENT_STATUS_CHOICES,
        default='pending',
        verbose_name='Estado de Asignación'
    )
    
    # Seguimiento individual
    hours_worked = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Horas Trabajadas'
    )
    
    units_completed = models.IntegerField(
        default=0,
        verbose_name='Unidades Completadas'
    )
    
    employee_notes = models.TextField(
        blank=True,
        verbose_name='Notas del Empleado'
    )
    
    supervisor_notes = models.TextField(
        blank=True,
        verbose_name='Notas del Supervisor'
    )
    
    # Calificación del trabajo
    quality_rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Calificación de Calidad (1-5)'
    )
    
    class Meta:
        unique_together = ['task', 'employee']
        verbose_name = 'Asignación de Tarea'
        verbose_name_plural = 'Asignaciones de Tareas'
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.task.title} - {self.employee.user.get_full_name()}"
    
    @property
    def calculated_payment(self):
        """Calcula el pago basado en el tipo de tarea"""
        if self.task.payment_type == 'hourly':
            return self.hours_worked * (self.task.hourly_rate or 0)
        elif self.task.payment_type == 'fixed':
            # Pago fijo dividido entre empleados asignados
            if self.status == 'completed':
                return self.task.fixed_amount / self.task.total_assigned_employees
            return 0
        elif self.task.payment_type == 'unit':
            return self.units_completed * (self.task.unit_rate or 0)
        return 0


class TaskProgress(models.Model):
    """Modelo para seguimiento detallado del progreso"""
    
    assignment = models.ForeignKey(
        TaskAssignment,
        on_delete=models.CASCADE,
        related_name='progress_reports'
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    progress_description = models.TextField(
        verbose_name='Descripción del Progreso'
    )
    
    progress_image = models.ImageField(
        upload_to='task_progress/',
        null=True,
        blank=True,
        verbose_name='Imagen del Progreso'
    )
    
    location_lat = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name='Latitud'
    )
    
    location_lng = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name='Longitud'
    )
    
    hours_worked_session = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Horas de esta Sesión'
    )
    
    units_completed_session = models.IntegerField(
        default=0,
        verbose_name='Unidades Completadas en esta Sesión'
    )
    
    class Meta:
        verbose_name = 'Reporte de Progreso'
        verbose_name_plural = 'Reportes de Progreso'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Progreso: {self.assignment} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"


class TaskComment(models.Model):
    """Comentarios y comunicación en las tareas"""
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    
    author = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        verbose_name='Autor'
    )
    
    content = models.TextField(
        verbose_name='Comentario'
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    is_private = models.BooleanField(
        default=False,
        verbose_name='Comentario Privado',
        help_text='Solo visible para supervisores'
    )
    
    attachment = models.FileField(
        upload_to='task_comments/',
        null=True,
        blank=True,
        verbose_name='Archivo Adjunto'
    )
    
    class Meta:
        verbose_name = 'Comentario de Tarea'
        verbose_name_plural = 'Comentarios de Tareas'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Comentario de {self.author.user.get_full_name()} en {self.task.title}"