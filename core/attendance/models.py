from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from datetime import datetime, time, timedelta, date
from decimal import Decimal

class WorkSchedule(models.Model):
    """
    Horarios de trabajo
    """
    SCHEDULE_TYPES = [
        ('fixed', 'Horario Fijo'),
        ('flexible', 'Horario Flexible'),
        ('shift', 'Por Turnos'),
        ('remote', 'Trabajo Remoto'),
    ]
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre del Horario'
    )
    
    schedule_type = models.CharField(
        max_length=15,
        choices=SCHEDULE_TYPES,
        default='fixed',
        verbose_name='Tipo de Horario'
    )
    
    start_time = models.TimeField(
        verbose_name='Hora de Inicio'
    )
    
    end_time = models.TimeField(
        verbose_name='Hora de Fin'
    )
    
    break_duration = models.DurationField(
        default=timedelta(hours=1),
        verbose_name='Duración del Descanso'
    )
    
    weekly_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=40.00,
        verbose_name='Horas Semanales'
    )
    
    # Tolerancia para tardanzas
    late_tolerance = models.IntegerField(
        default=15,
        verbose_name='Tolerancia de Tardanza (minutos)'
    )
    
    # Días de la semana
    monday = models.BooleanField(default=True, verbose_name='Lunes')
    tuesday = models.BooleanField(default=True, verbose_name='Martes')
    wednesday = models.BooleanField(default=True, verbose_name='Miércoles')
    thursday = models.BooleanField(default=True, verbose_name='Jueves')
    friday = models.BooleanField(default=True, verbose_name='Viernes')
    saturday = models.BooleanField(default=False, verbose_name='Sábado')
    sunday = models.BooleanField(default=False, verbose_name='Domingo')
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Horario de Trabajo'
        verbose_name_plural = 'Horarios de Trabajo'
        db_table = 'attendance_schedule'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"
    
    @property
    def working_days(self):
        """Lista de días laborales"""
        days = []
        if self.monday: days.append('Lunes')
        if self.tuesday: days.append('Martes')
        if self.wednesday: days.append('Miércoles')
        if self.thursday: days.append('Jueves')
        if self.friday: days.append('Viernes')
        if self.saturday: days.append('Sábado')
        if self.sunday: days.append('Domingo')
        return days
    
    @property
    def daily_hours(self):
        """Horas de trabajo por día"""
        start = datetime.combine(datetime.today(), self.start_time)
        end = datetime.combine(datetime.today(), self.end_time)
        if end < start:
            end += timedelta(days=1)
        work_duration = end - start - self.break_duration
        return work_duration.total_seconds() / 3600
    
    def is_work_day(self, date_obj):
        """Verifica si una fecha es día laboral según el horario"""
        weekday = date_obj.weekday()  # 0=Monday, 6=Sunday
        days_map = {
            0: self.monday,
            1: self.tuesday,
            2: self.wednesday,
            3: self.thursday,
            4: self.friday,
            5: self.saturday,
            6: self.sunday,
        }
        return days_map.get(weekday, False)


class EmployeeSchedule(models.Model):
    """
    Asignación de horarios a empleados
    """
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='Empleado'
    )
    
    schedule = models.ForeignKey(
        WorkSchedule,
        on_delete=models.CASCADE,
        related_name='employee_assignments',
        verbose_name='Horario'
    )
    
    start_date = models.DateField(
        verbose_name='Fecha de Inicio'
    )
    
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de Fin'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Notas'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Horario de Empleado'
        verbose_name_plural = 'Horarios de Empleados'
        db_table = 'attendance_employee_schedule'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.schedule.name}"
    
    def clean(self):
        """Validación personalizada"""
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError('La fecha de fin no puede ser anterior a la fecha de inicio.')


class Holiday(models.Model):
    """
    Días feriados y festivos
    """
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre del Feriado'
    )
    
    date = models.DateField(
        verbose_name='Fecha'
    )
    
    is_recurring = models.BooleanField(
        default=False,
        verbose_name='Se Repite Anualmente'
    )
    
    is_paid = models.BooleanField(
        default=True,
        verbose_name='Es Remunerado'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Descripción'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Feriado'
        verbose_name_plural = 'Feriados'
        db_table = 'attendance_holiday'
        ordering = ['date']
        unique_together = ['name', 'date']
    
    def __str__(self):
        return f"{self.name} - {self.date}"


class AttendanceRule(models.Model):
    """
    Reglas de asistencia personalizables
    """
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre de la Regla'
    )
    
    # Reglas de tardanza
    late_threshold = models.IntegerField(
        default=15,
        verbose_name='Umbral de Tardanza (minutos)'
    )
    
    # Reglas de horas extras
    overtime_threshold = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=8.00,
        verbose_name='Umbral de Horas Extras (horas)'
    )
    
    overtime_multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.50,
        verbose_name='Multiplicador de Horas Extras'
    )
    
    # Reglas de ausencias
    max_consecutive_absences = models.IntegerField(
        default=3,
        verbose_name='Máximo de Ausencias Consecutivas'
    )
    
    require_justification = models.BooleanField(
        default=True,
        verbose_name='Requiere Justificación'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Regla de Asistencia'
        verbose_name_plural = 'Reglas de Asistencia'
        db_table = 'attendance_rule'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Attendance(models.Model):
    """
    Registro de asistencia diaria
    """
    STATUS_CHOICES = [
        ('present', 'Presente'),
        ('absent', 'Ausente'),
        ('late', 'Tardanza'),
        ('partial', 'Parcial'),
        ('holiday', 'Feriado'),
        ('vacation', 'Vacaciones'),
        ('sick', 'Enfermedad'),
        ('remote', 'Trabajo Remoto'),
    ]
    
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='attendance_records',
        verbose_name='Empleado'
    )
    
    date = models.DateField(
        verbose_name='Fecha'
    )
    
    schedule = models.ForeignKey(
        WorkSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Horario Asignado'
    )
    
    clock_in = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de Entrada'
    )
    
    clock_out = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Hora de Salida'
    )
    
    break_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Inicio de Descanso'
    )
    
    break_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Fin de Descanso'
    )
    
    total_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.00,
        verbose_name='Horas Totales'
    )
    
    regular_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.00,
        verbose_name='Horas Regulares'
    )
    
    overtime_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.00,
        verbose_name='Horas Extras'
    )
    
    break_duration = models.DurationField(
        default=timedelta(0),
        verbose_name='Duración del Descanso'
    )
    
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='present',
        verbose_name='Estado'
    )
    
    is_late = models.BooleanField(
        default=False,
        verbose_name='Llegó Tarde'
    )
    
    late_minutes = models.IntegerField(
        default=0,
        verbose_name='Minutos de Tardanza'
    )
    
    early_departure = models.BooleanField(
        default=False,
        verbose_name='Salida Temprana'
    )
    
    early_departure_minutes = models.IntegerField(
        default=0,
        verbose_name='Minutos de Salida Temprana'
    )
    
    # Ubicación (GPS)
    clock_in_location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Ubicación de Entrada'
    )
    
    clock_out_location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Ubicación de Salida'
    )
    
    # IP Address para control
    clock_in_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP de Entrada'
    )
    
    clock_out_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP de Salida'
    )
    
    # Justificaciones
    is_justified = models.BooleanField(
        default=False,
        verbose_name='Justificado'
    )
    
    justification = models.TextField(
        blank=True,
        verbose_name='Justificación'
    )
    
    approved_by = models.ForeignKey(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_attendance',
        verbose_name='Aprobado por'
    )
    
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Aprobación'
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name='Notas'
    )
    
    # Campos de auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Creado por'
    )
    
    class Meta:
        verbose_name = 'Registro de Asistencia'
        verbose_name_plural = 'Registros de Asistencia'
        db_table = 'attendance_attendance'
        ordering = ['-date', '-clock_in']
        unique_together = ['employee', 'date']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.date} ({self.status})"
    
    def clean(self):
        """Validaciones personalizadas"""
        if self.clock_in and self.clock_out and self.clock_out < self.clock_in:
            raise ValidationError('La hora de salida no puede ser anterior a la hora de entrada.')
        
        if self.break_start and self.break_end and self.break_end < self.break_start:
            raise ValidationError('La hora de fin de descanso no puede ser anterior al inicio.')
    
    def save(self, *args, **kwargs):
        """Override save para cálculos automáticos"""
        self.calculate_hours()
        self.determine_status()
        super().save(*args, **kwargs)
    
    def calculate_hours(self):
        """Calcula las horas trabajadas automáticamente"""
        if not self.clock_in or not self.clock_out:
            return
        
        # Calcular tiempo total trabajado
        start = datetime.combine(self.date, self.clock_in)
        end = datetime.combine(self.date, self.clock_out)
        
        # Si la salida es al día siguiente
        if end < start:
            end += timedelta(days=1)
        
        total_time = end - start
        
        # Restar tiempo de descanso
        if self.break_start and self.break_end:
            break_start = datetime.combine(self.date, self.break_start)
            break_end = datetime.combine(self.date, self.break_end)
            if break_end > break_start:
                self.break_duration = break_end - break_start
                total_time -= self.break_duration
        
        # Convertir a horas decimales
        self.total_hours = Decimal(str(total_time.total_seconds() / 3600))
        
        # Calcular horas regulares y extras
        if self.schedule:
            expected_hours = Decimal(str(self.schedule.daily_hours))
            if self.total_hours > expected_hours:
                self.regular_hours = expected_hours
                self.overtime_hours = self.total_hours - expected_hours
            else:
                self.regular_hours = self.total_hours
                self.overtime_hours = Decimal('0.00')
    
    def determine_status(self):
        """Determina el estado basado en los datos de asistencia"""
        if not self.clock_in:
            self.status = 'absent'
            return
        
        if self.schedule:
            # Verificar tardanza
            scheduled_start = self.schedule.start_time
            if self.clock_in > scheduled_start:
                minutes_late = (
                    datetime.combine(self.date, self.clock_in) - 
                    datetime.combine(self.date, scheduled_start)
                ).total_seconds() / 60
                
                if minutes_late > self.schedule.late_tolerance:
                    self.is_late = True
                    self.late_minutes = int(minutes_late)
                    self.status = 'late'
                else:
                    self.status = 'present'
            
            # Verificar salida temprana
            if self.clock_out:
                scheduled_end = self.schedule.end_time
                if self.clock_out < scheduled_end:
                    minutes_early = (
                        datetime.combine(self.date, scheduled_end) - 
                        datetime.combine(self.date, self.clock_out)
                    ).total_seconds() / 60
                    
                    if minutes_early > 30:  # Más de 30 minutos temprano
                        self.early_departure = True
                        self.early_departure_minutes = int(minutes_early)
                        if self.status == 'present':
                            self.status = 'partial'
    
    @property
    def worked_time_display(self):
        """Tiempo trabajado en formato legible"""
        if not self.total_hours:
            return "0h 0m"
        
        hours = int(self.total_hours)
        minutes = int((self.total_hours - hours) * 60)
        return f"{hours}h {minutes}m"
    
    @property
    def is_complete_day(self):
        """Verifica si es un día completo de trabajo"""
        if not self.schedule or not self.total_hours:
            return False
        return self.total_hours >= Decimal(str(self.schedule.daily_hours))


class AttendanceCorrection(models.Model):
    """
    Correcciones de asistencia
    """
    CORRECTION_TYPES = [
        ('clock_in', 'Corrección de Entrada'),
        ('clock_out', 'Corrección de Salida'),
        ('break', 'Corrección de Descanso'),
        ('status', 'Corrección de Estado'),
        ('hours', 'Corrección de Horas'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
    ]
    
    attendance = models.ForeignKey(
        Attendance,
        on_delete=models.CASCADE,
        related_name='corrections',
        verbose_name='Registro de Asistencia'
    )
    
    correction_type = models.CharField(
        max_length=15,
        choices=CORRECTION_TYPES,
        verbose_name='Tipo de Corrección'
    )
    
    requested_by = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='attendance_corrections',
        verbose_name='Solicitado por'
    )
    
    reason = models.TextField(
        verbose_name='Motivo de la Corrección'
    )
    
    # Valores originales
    original_clock_in = models.TimeField(null=True, blank=True)
    original_clock_out = models.TimeField(null=True, blank=True)
    original_status = models.CharField(max_length=15, blank=True)
    
    # Valores corregidos
    corrected_clock_in = models.TimeField(null=True, blank=True)
    corrected_clock_out = models.TimeField(null=True, blank=True)
    corrected_status = models.CharField(max_length=15, blank=True)
    
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Estado'
    )
    
    approved_by = models.ForeignKey(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_corrections',
        verbose_name='Aprobado por'
    )
    
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Aprobación'
    )
    
    rejection_reason = models.TextField(
        blank=True,
        verbose_name='Motivo de Rechazo'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Corrección de Asistencia'
        verbose_name_plural = 'Correcciones de Asistencia'
        db_table = 'attendance_correction'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Corrección: {self.attendance} - {self.correction_type}"


class AttendanceSummary(models.Model):
    """
    Resumen mensual de asistencia por empleado
    """
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='attendance_summaries',
        verbose_name='Empleado'
    )
    
    year = models.IntegerField(verbose_name='Año')
    month = models.IntegerField(verbose_name='Mes')
    
    total_work_days = models.IntegerField(default=0, verbose_name='Días Laborales')
    days_present = models.IntegerField(default=0, verbose_name='Días Presente')
    days_absent = models.IntegerField(default=0, verbose_name='Días Ausente')
    days_late = models.IntegerField(default=0, verbose_name='Días con Tardanza')
    days_partial = models.IntegerField(default=0, verbose_name='Días Parciales')
    
    total_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        verbose_name='Horas Totales'
    )
    
    regular_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        verbose_name='Horas Regulares'
    )
    
    overtime_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        verbose_name='Horas Extras'
    )
    
    total_late_minutes = models.IntegerField(
        default=0,
        verbose_name='Total Minutos de Tardanza'
    )
    
    attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name='Porcentaje de Asistencia'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Resumen de Asistencia'
        verbose_name_plural = 'Resúmenes de Asistencia'
        db_table = 'attendance_summary'
        unique_together = ['employee', 'year', 'month']
        ordering = ['-year', '-month', 'employee__employee_number']
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.month}/{self.year}"