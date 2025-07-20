# core/employees/views/employee_portal.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.views.generic import TemplateView, UpdateView, CreateView, DetailView
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum, Count
from django.http import HttpResponse, Http404
from django.views.decorators.clickjacking import xframe_options_exempt
from django.template.loader import render_to_string
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views import View
from django.utils import timezone
from datetime import date, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO

import csv
import mimetypes
import os
import json

from core.employees.models import Employee, EmployeeDocument
from core.employees.forms.EmployeePortalForms import EmployeePasswordChangeForm, EmployeeProfileForm
from django.contrib.auth.forms import PasswordChangeForm

# IMPORTACIONES PARA TAREAS
try:
    from core.tasks.models import TaskAssignment, TaskProgress, TaskComment, Task
    TASKS_APP_AVAILABLE = True
except ImportError:
    TASKS_APP_AVAILABLE = False

# IMPORTACIONES PARA ASISTENCIA - AGREGAR ESTO
try:
    from core.attendance.models import Attendance, EmployeeSchedule, WorkSchedule
    ATTENDANCE_APP_AVAILABLE = True
except ImportError:
    ATTENDANCE_APP_AVAILABLE = False
    
# IMPORTACIONES PARA LICENCIAS - AGREGAR ESTO AL INICIO DEL ARCHIVO
try:
    from core.leaves.models import LeaveRequest, LeaveBalance, LeaveType
    from core.leaves.forms.LeavesForm import LeaveRequestForm
    LEAVES_APP_AVAILABLE = True
except ImportError:
    LEAVES_APP_AVAILABLE = False 
    
# IMPORTACIONES PARA PAYROLL - AGREGAR ESTO AL INICIO DEL ARCHIVO
try:
    from core.payroll.models import Payroll, PayrollPeriod, PayrollRubro, AdelantoQuincena
    PAYROLL_APP_AVAILABLE = True
except ImportError:
    PAYROLL_APP_AVAILABLE = False


class EmployeePasswordChangeRequiredMixin:
    """Mixin que redirige a cambio de contraseña si es necesario"""
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'employee_profile'):
            # Verificar si necesita cambiar contraseña temporal
            if hasattr(request.user, 'needs_password_change') and request.user.needs_password_change:
                # Solo permitir acceso a la vista de cambio de contraseña
                if request.resolver_match.url_name != 'employee_change_password':
                    return redirect('employees:employee_change_password')
        return super().dispatch(request, *args, **kwargs)


class EmployeeLoginRequiredMixin(LoginRequiredMixin):
    """Mixin que verifica que el usuario sea empleado"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not hasattr(request.user, 'employee_profile'):
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('users:login')
        
        return super().dispatch(request, *args, **kwargs)


@login_required
def employee_change_password_view(request):
    """Vista para cambio de contraseña temporal del empleado"""
    
    if not hasattr(request.user, 'employee_profile'):
        messages.error(request, 'No tienes permisos para acceder a esta sección.')
        return redirect('core:home')
    
    # Verificar si necesita cambiar contraseña
    needs_change = getattr(request.user, 'needs_password_change', False)
    
    if request.method == 'POST':
        form = EmployeePasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Marcar que ya no necesita cambiar contraseña
            user.needs_password_change = False
            user.save()
            
            # Mantener la sesión activa después del cambio
            update_session_auth_hash(request, user)
            
            messages.success(request, 'Tu contraseña ha sido cambiada exitosamente.')
            return redirect('employees:employee_dashboard')
    else:
        form = EmployeePasswordChangeForm(request.user)
    
    context = {
        'form': form,
        'needs_change': needs_change,
        'employee': request.user.employee_profile
    }
    
    return render(request, 'pages/employee/auth/change_password.html', context)

class EmployeeDocumentCreateView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, CreateView):
    """Vista para que el empleado suba sus propios documentos"""
    model = EmployeeDocument
    template_name = 'pages/employee/documents/upload_document.html'
    fields = ['document_type', 'name', 'file', 'notes']
    
    def form_valid(self, form):
        try:
            # Asignar el empleado actual
            form.instance.employee = self.request.user.employee_profile
            
            # Validaciones del archivo
            uploaded_file = form.cleaned_data['file']
            
            # Validar tamaño del archivo (máximo 10MB)
            max_size = 10 * 1024 * 1024  # 10MB en bytes
            if uploaded_file.size > max_size:
                messages.error(
                    self.request, 
                    f'El archivo es demasiado grande. Tamaño máximo permitido: 10MB. '
                    f'Tu archivo: {uploaded_file.size / (1024*1024):.1f}MB'
                )
                return self.form_invalid(form)
            
            # Validar tipo de archivo
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.txt']
            file_extension = uploaded_file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                messages.error(
                    self.request,
                    f'Tipo de archivo no permitido. Extensiones permitidas: {", ".join(allowed_extensions)}'
                )
                return self.form_invalid(form)
            
            # Intentar guardar
            response = super().form_valid(form)
            
            messages.success(
                self.request, 
                f'Documento "{form.instance.name}" subido exitosamente.'
            )
            
            return response
            
        except Exception as e:
            messages.error(
                self.request, 
                f'Error al subir el documento: {str(e)}'
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        # Mostrar errores específicos del formulario
        if form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(
                        self.request, 
                        f'Error en {field}: {error}'
                    )
        
        if form.non_field_errors():
            for error in form.non_field_errors():
                messages.error(self.request, f'Error: {error}')
        
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse('employees:employee_documents')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee'] = self.request.user.employee_profile
        context['title'] = 'Subir Documento'
        return context


@login_required
def employee_document_upload_ajax(request):
    """Vista AJAX para subir documentos"""
    
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        employee = request.user.employee_profile
        
        # Obtener datos del formulario
        document_type = request.POST.get('document_type')
        name = request.POST.get('name')
        notes = request.POST.get('description', '')  # El frontend usa 'description'
        uploaded_file = request.FILES.get('file')
        
        # Validaciones
        if not all([document_type, name, uploaded_file]):
            return JsonResponse({
                'success': False, 
                'error': 'Faltan campos requeridos: tipo de documento, nombre y archivo'
            })
        
        # Validar que el tipo de documento sea válido
        valid_types = [choice[0] for choice in EmployeeDocument.DOCUMENT_TYPES]
        if document_type not in valid_types:
            return JsonResponse({
                'success': False, 
                'error': f'Tipo de documento no válido. Opciones: {", ".join(valid_types)}'
            })
        
        # Validar tamaño del archivo (máximo 10MB)
        max_size = 10 * 1024 * 1024  # 10MB en bytes
        if uploaded_file.size > max_size:
            return JsonResponse({
                'success': False, 
                'error': f'Archivo demasiado grande. Máximo: 10MB. Tu archivo: {uploaded_file.size / (1024*1024):.1f}MB'
            })
        
        # Validar extensión del archivo
        allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.txt']
        file_extension = f'.{uploaded_file.name.lower().split(".")[-1]}'
        if file_extension not in allowed_extensions:
            return JsonResponse({
                'success': False, 
                'error': f'Extensión no permitida. Permitidas: {", ".join(allowed_extensions)}'
            })
        
        # Crear el documento
        document = EmployeeDocument.objects.create(
            employee=employee,
            document_type=document_type,
            name=name,
            file=uploaded_file,
            notes=notes
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Documento "{name}" subido exitosamente',
            'document': {
                'id': document.id,
                'name': document.name,
                'type': document.get_document_type_display(),
                'upload_date': document.upload_date.strftime('%d/%m/%Y %H:%M'),
                'file_url': document.file.url if document.file else None,
                'size': document.file.size if document.file else 0
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': f'Error interno del servidor: {str(e)}'
        }, status=500)


@login_required
def employee_document_delete(request, document_id):
    """Vista para eliminar documento del empleado"""
    
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        # Verificar que el documento pertenezca al empleado
        document = get_object_or_404(
            EmployeeDocument, 
            id=document_id, 
            employee=request.user.employee_profile
        )
        
        if request.method == 'POST' or request.method == 'DELETE':
            document_name = document.name
            
            # Eliminar el archivo físico si existe
            if document.file:
                try:
                    import os
                    if os.path.isfile(document.file.path):
                        os.remove(document.file.path)
                except:
                    pass  # Si no se puede eliminar el archivo, continuar
            
            # Eliminar el registro de la base de datos
            document.delete()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Documento "{document_name}" eliminado exitosamente'
                })
            else:
                messages.success(request, f'Documento "{document_name}" eliminado exitosamente')
                return redirect('employees:employee_documents')
        
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
            else:
                messages.error(request, 'Método no permitido')
                return redirect('employees:employee_documents')
            
    except EmployeeDocument.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Documento no encontrado'}, status=404)
        else:
            messages.error(request, 'Documento no encontrado')
            return redirect('employees:employee_documents')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        else:
            messages.error(request, f'Error al eliminar documento: {str(e)}')
            return redirect('employees:employee_documents')


class EmployeeDashboardView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Dashboard principal del empleado UNIFICADO (Personal + Tareas)"""
    template_name = 'pages/employee/dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        # ==================== INFORMACIÓN PERSONAL ====================
        context['employee'] = employee
        
        # Estadísticas personales
        context['years_of_service'] = employee.years_of_service
        context['days_until_birthday'] = self.get_days_until_birthday(employee)
        
        # Información del departamento
        context['department_colleagues'] = Employee.objects.filter(
            department=employee.department,
            status='active'
        ).exclude(id=employee.id).count()
        
        # Documentos del empleado
        context['document_count'] = employee.documents.count()
        context['recent_documents'] = employee.documents.order_by('-upload_date')[:3]
        
        # Información de supervisión
        if employee.subordinates.exists():
            context['subordinates_count'] = employee.subordinates.filter(status='active').count()
            context['subordinates'] = employee.subordinates.filter(status='active')[:5]
        
        # ==================== INFORMACIÓN DE TAREAS ====================
        if TASKS_APP_AVAILABLE:
            # Estadísticas de tareas del empleado
            assignments_stats = TaskAssignment.objects.filter(employee=employee).aggregate(
                total=Count('id'),
                pending=Count('id', filter=Q(status='pending')),
                accepted=Count('id', filter=Q(status='accepted')),
                in_progress=Count('id', filter=Q(status='in_progress')),
                completed=Count('id', filter=Q(status='completed')),
                rejected=Count('id', filter=Q(status='rejected')),
                total_hours=Sum('hours_worked') or 0,
                total_units=Sum('units_completed') or 0
            )
            context['assignments_stats'] = assignments_stats
            
            # Tareas urgentes asignadas
            urgent_assignments = TaskAssignment.objects.filter(
                employee=employee,
                status__in=['pending', 'accepted', 'in_progress'],
                task__priority='urgent'
            ).select_related('task', 'task__category').order_by('task__end_date')[:3]
            context['urgent_assignments'] = urgent_assignments
            
            # Actividad reciente del empleado
            recent_progress = TaskProgress.objects.filter(
                assignment__employee=employee
            ).select_related('assignment__task').order_by('-timestamp')[:5]
            context['recent_progress'] = recent_progress
            
            # Tareas próximas a vencer (próximas 24 horas)
            upcoming_deadline = TaskAssignment.objects.filter(
                employee=employee,
                status__in=['pending', 'accepted', 'in_progress'],
                task__end_date__range=[
                    timezone.now(),
                    timezone.now() + timedelta(hours=24)
                ]
            ).select_related('task').order_by('task__end_date')[:5]
            context['upcoming_deadline'] = upcoming_deadline
            
            # Tareas recientes (últimas 5 asignaciones)
            recent_assignments = TaskAssignment.objects.filter(
                employee=employee
            ).select_related('task', 'task__category').order_by('-assigned_at')[:5]
            context['recent_assignments'] = recent_assignments
            
            # Earnings del mes (calculado basado en tareas completadas)
            current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_earnings = 0
            completed_assignments_this_month = TaskAssignment.objects.filter(
                employee=employee,
                status='completed',
                completed_at__gte=current_month_start
            )
            
            for assignment in completed_assignments_this_month:
                monthly_earnings += assignment.calculated_payment
            
            context['monthly_earnings'] = monthly_earnings
            
            # Indicador de si tiene tareas (para mostrar/ocultar secciones)
            context['has_tasks'] = assignments_stats['total'] > 0
            
            # Progreso estadísticas para gráficos
            if assignments_stats['total'] > 0:
                context['completion_rate'] = int((assignments_stats['completed'] / assignments_stats['total']) * 100)
            else:
                context['completion_rate'] = 100
        else:
            # Si no hay app de tareas, establecer valores por defecto
            context['assignments_stats'] = {
                'total': 0, 'pending': 0, 'accepted': 0, 'in_progress': 0, 
                'completed': 0, 'rejected': 0, 'total_hours': 0, 'total_units': 0
            }
            context['urgent_assignments'] = []
            context['recent_progress'] = []
            context['upcoming_deadline'] = []
            context['recent_assignments'] = []
            context['monthly_earnings'] = 0
            context['has_tasks'] = False
            context['completion_rate'] = 100
        
        # Próximos eventos (placeholder para futuras funcionalidades)
        context['upcoming_events'] = []
        
        return context
    
    def get_days_until_birthday(self, employee):
        """Calcula días hasta el próximo cumpleaños"""
        if not employee.birth_date:
            return None
            
        today = date.today()
        birthday_this_year = employee.birth_date.replace(year=today.year)
        
        if birthday_this_year < today:
            birthday_next_year = employee.birth_date.replace(year=today.year + 1)
            return (birthday_next_year - today).days
        else:
            return (birthday_this_year - today).days


# ==================== RESTO DE VISTAS SIN CAMBIOS ====================

class EmployeeProfileView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista del perfil del empleado"""
    template_name = 'pages/employee/profile/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        context['employee'] = employee
        context['user'] = self.request.user
        
        # Información adicional
        context['supervisor'] = employee.supervisor
        context['subordinates'] = employee.subordinates.filter(status='active')
        context['department_info'] = employee.department
        context['position_info'] = employee.position
        
        return context


class EmployeeDocumentsView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista de documentos del empleado"""
    template_name = 'pages/employee/documents/documents.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        # Obtener documentos del empleado
        documents = employee.documents.all().order_by('-upload_date')
        
        # Agrupar por tipo de documento
        documents_by_type = {}
        for doc in documents:
            doc_type = doc.get_document_type_display()
            if doc_type not in documents_by_type:
                documents_by_type[doc_type] = []
            documents_by_type[doc_type].append(doc)
        
        context['employee'] = employee
        context['documents'] = documents
        context['documents_by_type'] = documents_by_type
        context['document_types'] = EmployeeDocument.DOCUMENT_TYPES
        
        return context


class EmployeePayrollView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista de información de nómina del empleado COMPLETAMENTE CORREGIDA PARA RUBROS"""
    template_name = 'pages/employee/payroll/payroll.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        context['employee'] = employee
        
        if PAYROLL_APP_AVAILABLE:
            # Información salarial básica
            context['current_salary'] = employee.salary
            context['position_base_salary'] = employee.position.base_salary if employee.position else employee.salary
            
            # Obtener registros de nómina del empleado (últimos 12 meses)
            one_year_ago = timezone.now().date() - timedelta(days=365)
            payroll_records = Payroll.objects.filter(
                employee=employee,
                period__start_date__gte=one_year_ago
            ).select_related('period').prefetch_related('rubros_aplicados__rubro__tipo_rubro').order_by('-period__start_date')
            
            # Formatear los registros para el template
            formatted_records = []
            for payroll in payroll_records:
                # Calcular bonos y extras usando properties del modelo
                total_bonuses = (
                    payroll.overtime_pay + 
                    payroll.total_ingresos_rubros
                )
                
                # Calcular deducciones usando properties del modelo
                total_deductions = payroll.total_egresos_rubros
                
                formatted_records.append({
                    'id': payroll.id,
                    'period': f"{payroll.period.start_date.strftime('%b %Y')}",
                    'period_full': f"{payroll.period.start_date.strftime('%d/%m/%Y')} - {payroll.period.end_date.strftime('%d/%m/%Y')}",
                    'base_salary': payroll.base_salary,
                    'bonuses': total_bonuses,
                    'deductions': total_deductions,
                    'net_total': payroll.net_pay,  # Usar property
                    'is_paid': payroll.is_paid,
                    'payment_date': payroll.payment_date,
                    'start_date': payroll.period.start_date,
                    'end_date': payroll.period.end_date,
                })
            
            context['payroll_records'] = formatted_records
            
            # Cálculos para el mes actual
            current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).date()
            current_month_payroll = None
            
            # Buscar nómina del mes actual
            for payroll in payroll_records:
                if payroll.period.start_date >= current_month_start:
                    current_month_payroll = payroll
                    break
            
            if current_month_payroll:
                # Si hay nómina del mes actual, usar esos datos
                context['current_month_earnings'] = current_month_payroll.net_pay
                
                # Desglose detallado del mes actual usando properties
                context['current_month_bonuses'] = (
                    current_month_payroll.overtime_pay + 
                    current_month_payroll.total_ingresos_rubros
                )
                
                context['current_month_deductions'] = current_month_payroll.total_egresos_rubros
                context['current_month_overtime'] = current_month_payroll.overtime_pay
                
            else:
                # Si no hay nómina del mes actual, usar salario base
                context['current_month_earnings'] = employee.salary
                context['current_month_bonuses'] = 0
                context['current_month_deductions'] = 0
                context['current_month_overtime'] = 0
            
            # Cálculos anuales
            current_year = timezone.now().year
            year_payrolls = [p for p in payroll_records if p.period.start_date.year == current_year]
            
            # Ganancia total del año (calcular usando properties en Python)
            ytd_earnings = sum(payroll.net_pay for payroll in year_payrolls)
            context['ytd_earnings'] = ytd_earnings
            
            # Estadísticas adicionales
            context['months_worked_this_year'] = len(year_payrolls)
            
            # Promedio mensual basado en nóminas reales
            if context['months_worked_this_year'] > 0:
                context['monthly_average'] = ytd_earnings / context['months_worked_this_year']
            else:
                context['monthly_average'] = employee.salary
            
            # Bonos y deducciones totales del año usando properties
            year_bonuses = sum(
                payroll.overtime_pay + payroll.total_ingresos_rubros 
                for payroll in year_payrolls
            )
            year_deductions = sum(
                payroll.total_egresos_rubros 
                for payroll in year_payrolls
            )
            
            context['ytd_bonuses'] = year_bonuses
            context['ytd_deductions'] = year_deductions
            
            # Adelantos pendientes del empleado
            adelantos_pendientes = AdelantoQuincena.objects.filter(
                employee=employee,
                is_descontado=False
            ).order_by('-fecha_adelanto')
            
            context['adelantos_pendientes'] = adelantos_pendientes
            context['total_adelantos_pendientes'] = sum(
                adelanto.monto for adelanto in adelantos_pendientes
            ) if adelantos_pendientes else 0
            
            # Próximo período de pago
            try:
                next_period = PayrollPeriod.objects.filter(
                    start_date__gt=timezone.now().date(),
                    status='draft'
                ).order_by('start_date').first()
                
                if next_period:
                    context['next_pay_date'] = next_period.pay_date
                    context['next_period_name'] = next_period.name
                else:
                    # Si no hay período futuro, estimar fin de mes
                    today = timezone.now().date()
                    if today.month == 12:
                        next_month = today.replace(year=today.year + 1, month=1, day=1)
                    else:
                        next_month = today.replace(month=today.month + 1, day=1)
                    
                    last_day = next_month - timedelta(days=1)
                    context['next_pay_date'] = last_day
                    context['next_period_name'] = f"Estimado - {last_day.strftime('%B %Y')}"
                    
            except Exception:
                context['next_pay_date'] = None
                context['next_period_name'] = "Por definir"
            
        else:
            # Si no hay app de payroll, usar valores por defecto
            context['current_salary'] = employee.salary
            context['position_base_salary'] = employee.position.base_salary if employee.position else employee.salary
            context['payroll_records'] = []
            context['current_month_earnings'] = employee.salary
            context['current_month_bonuses'] = 0
            context['current_month_deductions'] = 0
            context['current_month_overtime'] = 0
            context['ytd_earnings'] = employee.salary * timezone.now().month
            context['months_worked_this_year'] = timezone.now().month
            context['monthly_average'] = employee.salary
            context['ytd_bonuses'] = 0
            context['ytd_deductions'] = 0
            context['adelantos_pendientes'] = []
            context['total_adelantos_pendientes'] = 0
            context['next_pay_date'] = None
            context['next_period_name'] = "Por configurar"
        
        return context


class EmployeeTimeView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista de control de tiempo/asistencia del empleado ACTUALIZADA"""
    template_name = 'pages/employee/time/time.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        context['employee'] = employee
        
        # Obtener el horario actual del empleado
        today = timezone.now().date()
        current_schedule = None
        
        try:
            from core.attendance.models import EmployeeSchedule
            employee_schedule = EmployeeSchedule.objects.filter(
                employee=employee,
                is_active=True,
                start_date__lte=today,
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=today)
            ).select_related('schedule').first()
            
            if employee_schedule:
                current_schedule = employee_schedule.schedule
        except ImportError:
            pass
        
        context['current_schedule'] = current_schedule
        
        # Obtener registros del mes actual
        month_start = today.replace(day=1)
        
        try:
            from core.attendance.models import Attendance
            attendance_records = Attendance.objects.filter(
                employee=employee,
                date__gte=month_start,
                date__lte=today
            ).order_by('-date')
            
            context['attendance_records'] = attendance_records
            
            # Estadísticas del mes
            monthly_stats = attendance_records.aggregate(
                total_hours=Sum('total_hours'),
                total_overtime=Sum('overtime_hours'),
                total_days=Count('id'),
                days_present=Count('id', filter=Q(status='present')),
                days_late=Count('id', filter=Q(status='late')),
            )
            
            context['monthly_hours'] = monthly_stats['total_hours'] or 0
            context['overtime_hours'] = monthly_stats['total_overtime'] or 0
            context['days_worked'] = monthly_stats['total_days'] or 0
            context['days_present'] = monthly_stats['days_present'] or 0
            context['days_late'] = monthly_stats['days_late'] or 0
            
            # Verificar si hay registro activo hoy
            today_record = attendance_records.filter(date=today).first()
            context['today_record'] = today_record
            
            # Determinar estado actual
            if today_record:
                if today_record.clock_in and not today_record.clock_out:
                    context['is_working'] = True
                    context['work_start_time'] = today_record.clock_in
                    # Verificar si está en descanso
                    context['is_on_break'] = (today_record.break_start and not today_record.break_end)
                else:
                    context['is_working'] = False
                    context['is_on_break'] = False
            else:
                context['is_working'] = False
                context['is_on_break'] = False
            
        except ImportError:
            # Si no existe la app de attendance, usar valores por defecto
            context['attendance_records'] = []
            context['monthly_hours'] = 0
            context['overtime_hours'] = 0
            context['days_worked'] = 0
            context['is_working'] = False
            context['is_on_break'] = False
            context['today_record'] = None
        
        # Calcular promedio diario
        if context['days_worked'] > 0:
            context['daily_average'] = round(float(context['monthly_hours']) / context['days_worked'], 1)
        else:
            context['daily_average'] = 0.0
        
        return context


class EmployeeRequestsView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista de solicitudes del empleado (vacaciones, permisos, etc.) ACTUALIZADA"""
    template_name = 'pages/employee/requests/requests.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        context['employee'] = employee
        
        if LEAVES_APP_AVAILABLE:
            # Solicitudes de licencia del empleado
            leave_requests = LeaveRequest.objects.filter(
                employee=employee
            ).select_related('leave_type', 'approved_by').order_by('-created_at')
            
            context['leave_requests'] = leave_requests
            
            # Estadísticas de solicitudes
            requests_stats = {
                'total': leave_requests.count(),
                'pending': leave_requests.filter(status='pending').count(),
                'approved': leave_requests.filter(status='approved').count(),
                'rejected': leave_requests.filter(status='rejected').count()
            }
            context['requests_stats'] = requests_stats
            
            # Balance de licencias del año actual
            current_year = timezone.now().year
            leave_balances = LeaveBalance.objects.filter(
                employee=employee,
                year=current_year
            ).select_related('leave_type')
            
            context['leave_balances'] = leave_balances
            
            # Tipos de licencia disponibles
            available_leave_types = LeaveType.objects.filter(is_active=True)
            context['available_leave_types'] = available_leave_types
            
            # Solicitudes urgentes o próximas
            urgent_requests = leave_requests.filter(
                status='pending',
                start_date__lte=timezone.now().date() + timedelta(days=7)
            )[:3]
            context['urgent_requests'] = urgent_requests
            
            # Calcular balance de vacaciones específico
            vacation_balance = 15  # Valor por defecto
            for balance in leave_balances:
                if balance.leave_type.code == 'VAC':  # Código para vacaciones
                    vacation_balance = balance.remaining_days
                    break
            context['vacation_balance'] = vacation_balance
            
        else:
            # Si no hay app de licencias, establecer valores por defecto
            context['leave_requests'] = []
            context['requests_stats'] = {
                'total': 0, 'pending': 0, 'approved': 0, 'rejected': 0
            }
            context['leave_balances'] = []
            context['available_leave_types'] = []
            context['urgent_requests'] = []
            context['vacation_balance'] = 15
        
        # Placeholder para otros tipos de solicitudes futuras
        context['other_requests'] = []
        
        return context


class EmployeeLeaveRequestCreateView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, CreateView):
    """Vista para que el empleado cree solicitudes de licencia desde su portal"""
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'pages/employee/requests/form_leave_request.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        try:
            # Asignar el empleado actual
            form.instance.employee = self.request.user.employee_profile
            
            # Calcular días solicitados automáticamente
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            if start_date and end_date:
                form.instance.days_requested = (end_date - start_date).days + 1
            
            # Validaciones adicionales
            leave_type = form.cleaned_data['leave_type']
            
            # Validar anticipación para vacaciones
            if leave_type.code == 'VAC':  # Código para vacaciones
                days_ahead = (start_date - timezone.now().date()).days
                if days_ahead < 15:
                    messages.error(
                        self.request, 
                        'Las vacaciones deben solicitarse con al menos 15 días de anticipación.'
                    )
                    return self.form_invalid(form)
            
            # Validar balance disponible
            if LEAVES_APP_AVAILABLE:
                try:
                    balance = LeaveBalance.objects.get(
                        employee=form.instance.employee,
                        leave_type=leave_type,
                        year=start_date.year
                    )
                    if balance.remaining_days < form.instance.days_requested:
                        messages.error(
                            self.request, 
                            f'No tienes suficientes días disponibles. '
                            f'Disponible: {balance.remaining_days} días, '
                            f'Solicitado: {form.instance.days_requested} días.'
                        )
                        return self.form_invalid(form)
                except LeaveBalance.DoesNotExist:
                    # Si no existe balance, usar los días permitidos del tipo
                    if leave_type.days_allowed < form.instance.days_requested:
                        messages.error(
                            self.request, 
                            f'Los días solicitados ({form.instance.days_requested}) '
                            f'exceden el límite permitido ({leave_type.days_allowed} días).'
                        )
                        return self.form_invalid(form)
            
            # Intentar guardar
            response = super().form_valid(form)
            
            messages.success(
                self.request, 
                f'Tu solicitud de {leave_type.name} ha sido enviada correctamente. '
                f'Será revisada por tu supervisor.'
            )
            
            return response
            
        except Exception as e:
            # Debug: mostrar el error específico
            messages.error(
                self.request, 
                f'Error al crear la solicitud: {str(e)}'
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        # Debug: mostrar errores específicos del formulario
        if form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(
                        self.request, 
                        f'Error en {field}: {error}'
                    )
        
        # Debug: mostrar errores no relacionados con campos
        if form.non_field_errors():
            for error in form.non_field_errors():
                messages.error(self.request, f'Error: {error}')
        
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse('employees:employee_requests')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee'] = self.request.user.employee_profile
        context['title'] = 'Nueva Solicitud de Licencia'
        
        # Obtener balances disponibles
        if LEAVES_APP_AVAILABLE:
            current_year = timezone.now().year
            context['leave_balances'] = LeaveBalance.objects.filter(
                employee=self.request.user.employee_profile,
                year=current_year
            ).select_related('leave_type')
        else:
            context['leave_balances'] = []
        
        return context
    
class EmployeeLeaveRequestUpdateView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, UpdateView):
    """Vista para que el empleado edite solicitudes de licencia pendientes"""
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'pages/employee/requests/form_leave_request.html'
    
    def get_queryset(self):
        # Solo permitir editar propias solicitudes pendientes
        return LeaveRequest.objects.filter(
            employee=self.request.user.employee_profile,
            status='pending'  # Solo pendientes se pueden editar
        )
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        try:
            # Recalcular días solicitados
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            if start_date and end_date:
                form.instance.days_requested = (end_date - start_date).days + 1
            
            # Validaciones adicionales
            leave_type = form.cleaned_data['leave_type']
            
            # Validar anticipación para vacaciones
            if leave_type.code == 'VAC':  # Código para vacaciones
                days_ahead = (start_date - timezone.now().date()).days
                if days_ahead < 15:
                    messages.error(
                        self.request, 
                        'Las vacaciones deben solicitarse con al menos 15 días de anticipación.'
                    )
                    return self.form_invalid(form)
            
            # Validar balance disponible
            if LEAVES_APP_AVAILABLE:
                try:
                    balance = LeaveBalance.objects.get(
                        employee=form.instance.employee,
                        leave_type=leave_type,
                        year=start_date.year
                    )
                    
                    # Considerar los días de la solicitud original (si cambió el tipo de licencia)
                    original_days = 0
                    if self.object.leave_type == leave_type:
                        original_days = self.object.days_requested
                    
                    available_days = balance.remaining_days + original_days
                    
                    if available_days < form.instance.days_requested:
                        messages.error(
                            self.request, 
                            f'No tienes suficientes días disponibles. '
                            f'Disponible: {available_days} días, '
                            f'Solicitado: {form.instance.days_requested} días.'
                        )
                        return self.form_invalid(form)
                        
                except LeaveBalance.DoesNotExist:
                    # Si no existe balance, usar los días permitidos del tipo
                    if leave_type.days_allowed < form.instance.days_requested:
                        messages.error(
                            self.request, 
                            f'Los días solicitados ({form.instance.days_requested}) '
                            f'exceden el límite permitido ({leave_type.days_allowed} días).'
                        )
                        return self.form_invalid(form)
            
            # Marcar como modificada
            form.instance.modified_at = timezone.now()
            
            # Intentar guardar
            response = super().form_valid(form)
            
            messages.success(
                self.request, 
                f'Tu solicitud de {leave_type.name} ha sido actualizada correctamente. '
                f'Los cambios serán revisados por tu supervisor.'
            )
            
            return response
            
        except Exception as e:
            messages.error(
                self.request, 
                f'Error al actualizar la solicitud: {str(e)}'
            )
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        # Mostrar errores específicos del formulario
        if form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(
                        self.request, 
                        f'Error en {field}: {error}'
                    )
        
        if form.non_field_errors():
            for error in form.non_field_errors():
                messages.error(self.request, f'Error: {error}')
        
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse('employees:employee_leave_request_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee'] = self.request.user.employee_profile
        context['title'] = 'Editar Solicitud de Licencia'
        context['is_edit'] = True  # Flag para indicar que es edición
        
        # Obtener balances disponibles
        if LEAVES_APP_AVAILABLE:
            current_year = timezone.now().year
            context['leave_balances'] = LeaveBalance.objects.filter(
                employee=self.request.user.employee_profile,
                year=current_year
            ).select_related('leave_type')
        else:
            context['leave_balances'] = []
        
        return context


class EmployeeLeaveRequestDetailView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, DetailView):
    """Vista para ver detalles de una solicitud de licencia del empleado"""
    model = LeaveRequest
    template_name = 'pages/employee/requests/leave_request_detail.html'
    context_object_name = 'leave_request'
    
    def get_queryset(self):
        # Solo permitir ver propias solicitudes
        return LeaveRequest.objects.filter(
            employee=self.request.user.employee_profile
        ).select_related('leave_type', 'approved_by')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee'] = self.request.user.employee_profile
        
        # Verificar si se puede editar (solo pendientes)
        context['can_edit'] = self.object.status == 'pending'
        
        return context


class EmployeeSettingsView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, UpdateView):
    """Vista de configuración del empleado"""
    template_name = 'pages/employee/settings/settings.html'
    form_class = EmployeeProfileForm
    success_url = reverse_lazy('employees:employee_settings')
    
    def get_object(self):
        return self.request.user.employee_profile
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee'] = self.get_object()
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Tu información ha sido actualizada exitosamente.')
        return super().form_valid(form)


class EmployeeNotificationsView(EmployeeLoginRequiredMixin, EmployeePasswordChangeRequiredMixin, TemplateView):
    """Vista de notificaciones del empleado"""
    template_name = 'pages/employee/notifications/notifications.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.request.user.employee_profile
        
        context['employee'] = employee
        
        # Placeholder para notificaciones
        context['notifications'] = [
            {
                'id': 1,
                'title': 'Bienvenido al sistema',
                'message': 'Tu cuenta ha sido creada exitosamente.',
                'type': 'info',
                'date': timezone.now(),
                'read': False
            }
        ]
        
        return context


# Vista AJAX para marcar notificaciones como leídas
class EmployeeMarkNotificationReadView(EmployeeLoginRequiredMixin, View):
    """Vista AJAX para marcar notificaciones como leídas"""
    
    def post(self, request):
        notification_id = request.POST.get('notification_id')
        # Implementar lógica para marcar notificación como leída
        return JsonResponse({'success': True})


# Vista para descargar documentos del empleado
@login_required
def employee_download_document(request, document_id):
    """Vista para descargar documentos del empleado - VERSIÓN CORREGIDA"""
    
    if not hasattr(request.user, 'employee_profile'):
        messages.error(request, 'No tienes permisos para acceder a este documento.')
        return redirect('core:home')
    
    try:
        document = get_object_or_404(
            EmployeeDocument, 
            id=document_id, 
            employee=request.user.employee_profile
        )
        
        if not document.file:
            messages.error(request, 'El archivo no está disponible.')
            return redirect('employees:employee_documents')
        
        # Verificar que el archivo existe físicamente
        try:
            import os
            if not os.path.isfile(document.file.path):
                messages.error(request, 'El archivo no se encuentra en el servidor.')
                return redirect('employees:employee_documents')
        except:
            messages.error(request, 'Error al acceder al archivo.')
            return redirect('employees:employee_documents')
        
        # Retornar el archivo como descarga
        from django.http import FileResponse
        import mimetypes
        
        file_path = document.file.path
        file_name = document.file.name.split('/')[-1]  # Obtener solo el nombre del archivo
        
        # Detectar el tipo MIME
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        response = FileResponse(
            open(file_path, 'rb'),
            content_type=content_type,
            as_attachment=True,
            filename=file_name
        )
        
        return response
        
    except EmployeeDocument.DoesNotExist:
        messages.error(request, 'Documento no encontrado.')
        return redirect('employees:employee_documents')
    except Exception as e:
        messages.error(request, f'Error al descargar el documento: {str(e)}')
        return redirect('employees:employee_documents')
    
    
@login_required
@xframe_options_exempt  # Permite mostrar en iframe
def employee_document_view(request, document_id):
    """Vista para mostrar documentos en iframe sin restricciones X-Frame-Options"""
    
    if not hasattr(request.user, 'employee_profile'):
        raise Http404("Documento no encontrado")
    
    try:
        document = get_object_or_404(
            EmployeeDocument, 
            id=document_id, 
            employee=request.user.employee_profile
        )
        
        if not document.file:
            raise Http404("Archivo no disponible")
        
        # Verificar que el archivo existe
        if not os.path.isfile(document.file.path):
            raise Http404("Archivo no encontrado en el servidor")
        
        # Obtener tipo MIME
        content_type, _ = mimetypes.guess_type(document.file.path)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        # Para PDFs, asegurar que se muestre inline
        if content_type == 'application/pdf':
            content_type = 'application/pdf'
        
        # Leer y retornar el archivo
        with open(document.file.path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=content_type)
            
            # Para PDFs y imágenes, mostrar inline
            if content_type.startswith(('application/pdf', 'image/')):
                response['Content-Disposition'] = f'inline; filename="{document.file.name.split("/")[-1]}"'
            else:
                response['Content-Disposition'] = f'attachment; filename="{document.file.name.split("/")[-1]}"'
            
            # Remover X-Frame-Options para permitir iframe
            response['X-Frame-Options'] = 'SAMEORIGIN'
            
            return response
            
    except EmployeeDocument.DoesNotExist:
        raise Http404("Documento no encontrado")
    except Exception as e:
        raise Http404(f"Error al acceder al documento: {str(e)}")


@login_required  
def employee_document_thumbnail(request, document_id):
    """Vista para generar miniaturas de documentos (opcional)"""
    
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        document = get_object_or_404(
            EmployeeDocument, 
            id=document_id, 
            employee=request.user.employee_profile
        )
        
        # Para imágenes, retornar la imagen redimensionada
        if document.file and document.file.name.lower().endswith(('.jpg', '.jpeg', '.png')):
            try:
                from PIL import Image
                from io import BytesIO
                
                # Abrir imagen original
                with Image.open(document.file.path) as img:
                    # Redimensionar manteniendo aspecto
                    img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                    
                    # Guardar en buffer
                    buffer = BytesIO()
                    format = 'JPEG' if img.mode == 'RGB' else 'PNG'
                    img.save(buffer, format=format)
                    buffer.seek(0)
                    
                    content_type = 'image/jpeg' if format == 'JPEG' else 'image/png'
                    return HttpResponse(buffer.getvalue(), content_type=content_type)
                    
            except ImportError:
                # Si PIL no está disponible, retornar imagen original
                pass
        
        # Para otros tipos, retornar icono por defecto
        return HttpResponse(status=404)
        
    except EmployeeDocument.DoesNotExist:
        return HttpResponse(status=404)
    except Exception:
        return HttpResponse(status=500)


# ==================== APIS PARA TAREAS (OPCIONALES) ====================

@login_required
def employee_task_stats_api(request):
    """API para estadísticas de tareas del empleado"""
    if not hasattr(request.user, 'employee_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    if not TASKS_APP_AVAILABLE:
        return JsonResponse({'error': 'Tasks app not available'}, status=404)
    
    employee = request.user.employee_profile
    
    # Estadísticas por estado
    status_stats = TaskAssignment.objects.filter(employee=employee).values('status').annotate(
        count=Count('id')
    )
    
    # Productividad semanal (últimas 4 semanas)
    weeks_data = []
    for i in range(4):
        week_start = timezone.now() - timedelta(weeks=i+1)
        week_end = timezone.now() - timedelta(weeks=i)
        
        completed = TaskAssignment.objects.filter(
            employee=employee,
            status='completed',
            completed_at__range=[week_start, week_end]
        ).count()
        
        hours_worked = TaskProgress.objects.filter(
            assignment__employee=employee,
            timestamp__range=[week_start, week_end]
        ).aggregate(Sum('hours_worked_session'))['hours_worked_session__sum'] or 0
        
        weeks_data.append({
            'week': f'Semana {4-i}',
            'completed': completed,
            'hours': float(hours_worked)
        })
    
    # Distribución por categoría
    category_stats = TaskAssignment.objects.filter(employee=employee).values(
        'task__category__name', 'task__category__color'
    ).annotate(count=Count('id'))
    
    # Earnings por mes (últimos 6 meses)
    earnings_data = []
    for i in range(6):
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30*i)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_end = month_end - timedelta(days=month_end.day)
        
        completed_assignments = TaskAssignment.objects.filter(
            employee=employee,
            status='completed',
            completed_at__range=[month_start, month_end]
        )
        
        month_earnings = sum(assignment.calculated_payment for assignment in completed_assignments)
        
        earnings_data.append({
            'month': month_start.strftime('%B %Y'),
            'earnings': float(month_earnings)
        })
    
    return JsonResponse({
        'status_stats': list(status_stats),
        'productivity': weeks_data,
        'category_stats': list(category_stats),
        'earnings': list(reversed(earnings_data))
    })
    
@login_required
def employee_payroll_receipt_download(request, payroll_id):
    """Descargar recibo de pago individual"""
    
    if not hasattr(request.user, 'employee_profile'):
        messages.error(request, 'No tienes permisos para acceder a este documento.')
        return redirect('core:home')
    
    if not PAYROLL_APP_AVAILABLE:
        messages.error(request, 'Funcionalidad de nómina no disponible.')
        return redirect('employees:employee_payroll')
    
    try:
        # Verificar que el recibo pertenezca al empleado
        payroll = get_object_or_404(
            Payroll, 
            id=payroll_id, 
            employee=request.user.employee_profile
        )
        
        # Generar PDF del recibo
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Header de la empresa
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, height - 50, "GNAGRO S.A.")
        p.setFont("Helvetica", 12)
        p.drawString(50, height - 70, "Recibo de Pago")
        
        # Información del empleado
        y_position = height - 120
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y_position, "INFORMACIÓN DEL EMPLEADO")
        
        y_position -= 25
        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"Nombre: {payroll.employee.user.get_full_name()}")
        y_position -= 15
        p.drawString(50, y_position, f"ID Empleado: {payroll.employee.employee_number}")
        y_position -= 15
        p.drawString(50, y_position, f"Departamento: {payroll.employee.department.name if payroll.employee.department else 'N/A'}")
        y_position -= 15
        p.drawString(50, y_position, f"Período: {payroll.period.start_date.strftime('%d/%m/%Y')} - {payroll.period.end_date.strftime('%d/%m/%Y')}")
        
        # Detalles del pago
        y_position -= 40
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y_position, "DETALLES DEL PAGO")
        
        y_position -= 25
        p.setFont("Helvetica", 10)
        
        # Ingresos
        p.drawString(50, y_position, "INGRESOS:")
        y_position -= 15
        p.drawString(70, y_position, f"Salario Base: ${payroll.base_salary:,.2f}")
        y_position -= 15
        
        if payroll.overtime_pay > 0:
            p.drawString(70, y_position, f"Horas Extras: ${payroll.overtime_pay:,.2f}")
            y_position -= 15
        
        if payroll.bonus > 0:
            p.drawString(70, y_position, f"Bonificaciones: ${payroll.bonus:,.2f}")
            y_position -= 15
        
        if payroll.commission > 0:
            p.drawString(70, y_position, f"Comisiones: ${payroll.commission:,.2f}")
            y_position -= 15
        
        if payroll.allowances > 0:
            p.drawString(70, y_position, f"Subsidios: ${payroll.allowances:,.2f}")
            y_position -= 15
        
        # Rubros adicionales de ingreso
        ingresos_adicionales = payroll.rubros_aplicados.filter(
            rubro__tipo_rubro__tipo='ingreso'
        )
        for rubro in ingresos_adicionales:
            p.drawString(70, y_position, f"{rubro.rubro.nombre}: ${rubro.monto:,.2f}")
            y_position -= 15
        
        # Total bruto
        y_position -= 10
        p.setFont("Helvetica-Bold", 10)
        p.drawString(70, y_position, f"TOTAL BRUTO: ${payroll.gross_pay:,.2f}")
        
        # Deducciones
        y_position -= 25
        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, "DEDUCCIONES:")
        y_position -= 15
        
        if payroll.income_tax > 0:
            p.drawString(70, y_position, f"Impuesto a la Renta: ${payroll.income_tax:,.2f}")
            y_position -= 15
        
        if payroll.social_security > 0:
            p.drawString(70, y_position, f"Seguridad Social: ${payroll.social_security:,.2f}")
            y_position -= 15
        
        if payroll.health_insurance > 0:
            p.drawString(70, y_position, f"Seguro de Salud: ${payroll.health_insurance:,.2f}")
            y_position -= 15
        
        if payroll.other_deductions > 0:
            p.drawString(70, y_position, f"Otras Deducciones: ${payroll.other_deductions:,.2f}")
            y_position -= 15
        
        # Rubros adicionales de egreso
        egresos_adicionales = payroll.rubros_aplicados.filter(
            rubro__tipo_rubro__tipo='egreso'
        )
        for rubro in egresos_adicionales:
            p.drawString(70, y_position, f"{rubro.rubro.nombre}: ${rubro.monto:,.2f}")
            if rubro.es_adelanto and rubro.fecha_adelanto:
                p.drawString(90, y_position - 10, f"(Adelanto del {rubro.fecha_adelanto.strftime('%d/%m/%Y')})")
                y_position -= 10
            y_position -= 15
        
        # Total deducciones
        y_position -= 10
        p.setFont("Helvetica-Bold", 10)
        total_deducciones = payroll.total_deductions
        egresos_total = sum(rubro.monto for rubro in egresos_adicionales)
        total_deducciones += egresos_total
        
        p.drawString(70, y_position, f"TOTAL DEDUCCIONES: ${total_deducciones:,.2f}")
        
        # Total neto (destacado)
        y_position -= 30
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y_position, f"TOTAL NETO: ${payroll.net_pay:,.2f}")
        
        # Información de pago
        y_position -= 40
        p.setFont("Helvetica", 10)
        if payroll.is_paid and payroll.payment_date:
            p.drawString(50, y_position, f"Fecha de Pago: {payroll.payment_date.strftime('%d/%m/%Y')}")
            y_position -= 15
            if payroll.payment_method:
                p.drawString(50, y_position, f"Método de Pago: {payroll.payment_method}")
        else:
            p.drawString(50, y_position, "Estado: Pendiente de Pago")
        
        # Footer
        p.setFont("Helvetica", 8)
        p.drawString(50, 50, f"Generado el {timezone.now().strftime('%d/%m/%Y %H:%M')}")
        p.drawString(50, 35, "Este es un documento generado automáticamente.")
        
        p.showPage()
        p.save()
        
        buffer.seek(0)
        
        # Crear respuesta HTTP con el PDF
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="recibo_pago_{payroll.employee.employee_number}_{payroll.period.start_date.strftime("%Y%m")}.pdf"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'Error al generar el recibo: {str(e)}')
        return redirect('employees:employee_payroll')


@login_required
def employee_payroll_export(request):
    """Exportar historial de nómina del empleado"""
    
    if not hasattr(request.user, 'employee_profile'):
        messages.error(request, 'No tienes permisos para acceder a esta funcionalidad.')
        return redirect('core:home')
    
    if not PAYROLL_APP_AVAILABLE:
        messages.error(request, 'Funcionalidad de nómina no disponible.')
        return redirect('employees:employee_payroll')
    
    employee = request.user.employee_profile
    export_format = request.GET.get('export', 'csv')
    
    try:
        # Obtener registros de nómina (último año)
        one_year_ago = timezone.now().date() - timedelta(days=365)
        payrolls = Payroll.objects.filter(
            employee=employee,
            period__start_date__gte=one_year_ago
        ).select_related('period').order_by('-period__start_date')
        
        if export_format == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="nomina_{employee.employee_number}_{timezone.now().strftime("%Y%m%d")}.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'Período', 'Fecha Inicio', 'Fecha Fin',
                'Salario Base', 'Horas Extras', 'Bonos', 'Comisiones', 'Subsidios',
                'Total Bruto', 'Imp. Renta', 'Seg. Social', 'Seg. Salud', 'Otras Deducciones',
                'Total Deducciones', 'Total Neto', 'Estado', 'Fecha Pago'
            ])
            
            for payroll in payrolls:
                writer.writerow([
                    payroll.period.name,
                    payroll.period.start_date.strftime('%d/%m/%Y'),
                    payroll.period.end_date.strftime('%d/%m/%Y'),
                    f"{payroll.base_salary:.2f}",
                    f"{payroll.overtime_pay:.2f}",
                    f"{payroll.bonus:.2f}",
                    f"{payroll.commission:.2f}",
                    f"{payroll.allowances:.2f}",
                    f"{payroll.gross_pay:.2f}",
                    f"{payroll.income_tax:.2f}",
                    f"{payroll.social_security:.2f}",
                    f"{payroll.health_insurance:.2f}",
                    f"{payroll.other_deductions:.2f}",
                    f"{payroll.total_deductions:.2f}",
                    f"{payroll.net_pay:.2f}",
                    'Pagado' if payroll.is_paid else 'Pendiente',
                    payroll.payment_date.strftime('%d/%m/%Y') if payroll.payment_date else ''
                ])
            
            return response
            
        elif export_format == 'json':
            data = []
            for payroll in payrolls:
                data.append({
                    'periodo': payroll.period.name,
                    'fecha_inicio': payroll.period.start_date.isoformat(),
                    'fecha_fin': payroll.period.end_date.isoformat(),
                    'salario_base': float(payroll.base_salary),
                    'horas_extras': float(payroll.overtime_pay),
                    'bonos': float(payroll.bonus),
                    'comisiones': float(payroll.commission),
                    'subsidios': float(payroll.allowances),
                    'total_bruto': float(payroll.gross_pay),
                    'impuesto_renta': float(payroll.income_tax),
                    'seguridad_social': float(payroll.social_security),
                    'seguro_salud': float(payroll.health_insurance),
                    'otras_deducciones': float(payroll.other_deductions),
                    'total_deducciones': float(payroll.total_deductions),
                    'total_neto': float(payroll.net_pay),
                    'estado': 'pagado' if payroll.is_paid else 'pendiente',
                    'fecha_pago': payroll.payment_date.isoformat() if payroll.payment_date else None
                })
            
            response = HttpResponse(
                json.dumps(data, indent=2, ensure_ascii=False), 
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="nomina_{employee.employee_number}_{timezone.now().strftime("%Y%m%d")}.json"'
            
            return response
        
        else:
            messages.error(request, 'Formato de exportación no válido.')
            return redirect('employees:employee_payroll')
            
    except Exception as e:
        messages.error(request, f'Error al exportar datos: {str(e)}')
        return redirect('employees:employee_payroll')