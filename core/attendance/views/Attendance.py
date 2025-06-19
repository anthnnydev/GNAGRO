from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import permission_required
from django.utils.decorators import method_decorator
from ..models import WorkSchedule, EmployeeSchedule, Holiday, AttendanceRule
from core.attendance.forms.AttendanceForm import WorkScheduleForm, EmployeeScheduleForm, HolidayForm, AttendanceRuleForm, WorkScheduleSearchForm


# ============ WORK SCHEDULE VIEWS ============

class WorkScheduleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Vista para listar horarios de trabajo"""
    model = WorkSchedule
    template_name = 'components/parameters/attendance/list.html'
    context_object_name = 'work_schedules'
    permission_required = 'attendance.view_workschedule'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = WorkSchedule.objects.all().annotate(
            employee_count=Count('employee_assignments')
        )
        
        # Filtros de búsqueda
        search = self.request.GET.get('search')
        schedule_type = self.request.GET.get('schedule_type')
        is_active = self.request.GET.get('is_active')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(schedule_type__icontains=search)
            )
        
        if schedule_type:
            queryset = queryset.filter(schedule_type=schedule_type)
            
        if is_active:
            queryset = queryset.filter(is_active=is_active == 'true')
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = WorkScheduleSearchForm(self.request.GET)
        context['search_query'] = self.request.GET.get('search', '')
        context['total_schedules'] = WorkSchedule.objects.count()
        context['active_schedules'] = WorkSchedule.objects.filter(is_active=True).count()
        context['schedule_types'] = WorkSchedule.SCHEDULE_TYPES
        return context


class WorkScheduleDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Vista para ver detalles de un horario de trabajo"""
    model = WorkSchedule
    template_name = 'components/parameters/attendance/detail.html'
    context_object_name = 'work_schedule'
    permission_required = 'attendance.view_workschedule'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee_assignments'] = EmployeeSchedule.objects.filter(
            schedule=self.object
        ).select_related('employee')[:10]
        context['total_employees'] = EmployeeSchedule.objects.filter(
            schedule=self.object,
            is_active=True
        ).count()
        return context


class WorkScheduleCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para crear un nuevo horario de trabajo"""
    model = WorkSchedule
    form_class = WorkScheduleForm
    template_name = 'components/parameters/attendance/form.html'
    permission_required = 'attendance.add_workschedule'
    success_url = reverse_lazy('attendance:work_schedule_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Horario "{form.instance.name}" creado exitosamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Error al crear el horario. Verifique los datos ingresados.')
        return super().form_invalid(form)


class WorkScheduleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para actualizar un horario de trabajo"""
    model = WorkSchedule
    form_class = WorkScheduleForm
    template_name = 'components/parameters/attendance/form.html'
    permission_required = 'attendance.change_workschedule'
    success_url = reverse_lazy('attendance:work_schedule_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Horario "{form.instance.name}" actualizado exitosamente.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Error al actualizar el horario. Verifique los datos ingresados.')
        return super().form_invalid(form)


class WorkScheduleDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista para eliminar un horario de trabajo"""
    model = WorkSchedule
    template_name = 'components/parameters/attendance/delete.html'
    permission_required = 'attendance.delete_workschedule'
    success_url = reverse_lazy('attendance:work_schedule_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Verificar si hay empleados asignados
        employee_count = EmployeeSchedule.objects.filter(
            schedule=self.object,
            is_active=True
        ).count()
        
        if employee_count > 0:
            messages.error(
                request, 
                f'No se puede eliminar el horario "{self.object.name}" porque tiene {employee_count} empleado(s) asignado(s).'
            )
            return redirect('attendance:work_schedule_detail', pk=self.object.pk)
        
        messages.success(request, f'Horario "{self.object.name}" eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)


# ============ EMPLOYEE SCHEDULE VIEWS ============

class EmployeeScheduleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Vista para listar asignaciones de horarios a empleados"""
    model = EmployeeSchedule
    template_name = 'components/parameters/attendance/employee_schedule/list.html'
    context_object_name = 'employee_schedules'
    permission_required = 'attendance.view_employeeschedule'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = EmployeeSchedule.objects.select_related(
            'employee__user', 'schedule'
        ).order_by('-start_date')
        
        # Filtros
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(employee__user__first_name__icontains=search) |
                Q(employee__user__last_name__icontains=search) |
                Q(employee__employee_number__icontains=search)
            )
        
        schedule_id = self.request.GET.get('schedule')
        if schedule_id:
            queryset = queryset.filter(schedule_id=schedule_id)
        
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['schedules'] = WorkSchedule.objects.filter(is_active=True)
        return context


class EmployeeScheduleCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para crear una nueva asignación de horario"""
    model = EmployeeSchedule
    form_class = EmployeeScheduleForm
    template_name = 'components/parameters/attendance/employee_schedule/form.html'
    permission_required = 'attendance.add_employeeschedule'
    success_url = reverse_lazy('attendance:employee_schedule_list')
    
    def get_initial(self):
        initial = super().get_initial()
        # Pre-seleccionar horario si viene como parámetro
        schedule_id = self.request.GET.get('schedule')
        if schedule_id:
            initial['schedule'] = schedule_id
        return initial
    
    def form_valid(self, form):
        messages.success(self.request, 'Asignación de horario creada exitosamente.')
        return super().form_valid(form)


class EmployeeScheduleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para actualizar una asignación de horario"""
    model = EmployeeSchedule
    form_class = EmployeeScheduleForm
    template_name = 'components/parameters/attendance/employee_schedule/form.html'
    permission_required = 'attendance.change_employeeschedule'
    success_url = reverse_lazy('attendance:employee_schedule_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Asignación de horario actualizada exitosamente.')
        return super().form_valid(form)


# ============ HOLIDAY VIEWS ============

class HolidayListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Vista para listar feriados"""
    model = Holiday
    template_name = 'components/parameters/attendance/holiday/list.html'
    context_object_name = 'holidays'
    permission_required = 'attendance.view_holiday'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Holiday.objects.all()
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.order_by('date')


class HolidayCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para crear un nuevo feriado"""
    model = Holiday
    form_class = HolidayForm
    template_name = 'components/parameters/attendance/holiday/form.html'
    permission_required = 'attendance.add_holiday'
    success_url = reverse_lazy('attendance:holiday_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Feriado "{form.instance.name}" creado exitosamente.')
        return super().form_valid(form)


class HolidayUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para actualizar un feriado"""
    model = Holiday
    form_class = HolidayForm
    template_name = 'components/parameters/attendance/holiday/form.html'
    permission_required = 'attendance.change_holiday'
    success_url = reverse_lazy('attendance:holiday_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Feriado "{form.instance.name}" actualizado exitosamente.')
        return super().form_valid(form)


class HolidayDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista para eliminar un feriado"""
    model = Holiday
    template_name = 'components/parameters/attendance/holiday/delete.html'
    permission_required = 'attendance.delete_holiday'
    success_url = reverse_lazy('attendance:holiday_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f'Feriado "{self.object.name}" eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)


# ============ ATTENDANCE RULE VIEWS ============

class AttendanceRuleListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Vista para listar reglas de asistencia"""
    model = AttendanceRule
    template_name = 'components/parameters/attendance/rule/list.html'
    context_object_name = 'attendance_rules'
    permission_required = 'attendance.view_attendancerule'
    paginate_by = 20


class AttendanceRuleCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para crear una nueva regla de asistencia"""
    model = AttendanceRule
    form_class = AttendanceRuleForm
    template_name = 'components/parameters/attendance/rule/form.html'
    permission_required = 'attendance.add_attendancerule'
    success_url = reverse_lazy('attendance:attendance_rule_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Regla "{form.instance.name}" creada exitosamente.')
        return super().form_valid(form)


class AttendanceRuleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para actualizar una regla de asistencia"""
    model = AttendanceRule
    form_class = AttendanceRuleForm
    template_name = 'components/parameters/attendance/rule/form.html'
    permission_required = 'attendance.change_attendancerule'
    success_url = reverse_lazy('attendance:attendance_rule_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Regla "{form.instance.name}" actualizada exitosamente.')
        return super().form_valid(form)


class AttendanceRuleDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista para eliminar una regla de asistencia"""
    model = AttendanceRule
    template_name = 'components/parameters/attendance/rule/delete.html'
    permission_required = 'attendance.delete_attendancerule'
    success_url = reverse_lazy('attendance:attendance_rule_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        messages.success(request, f'Regla "{self.object.name}" eliminada exitosamente.')
        return super().delete(request, *args, **kwargs)


# ============ AJAX VIEWS ============

@require_POST
@permission_required('attendance.change_workschedule')
def toggle_schedule_status(request, schedule_id):
    """Vista AJAX para cambiar el estado de un horario"""
    try:
        schedule = get_object_or_404(WorkSchedule, id=schedule_id)
        schedule.is_active = not schedule.is_active
        schedule.save()
        
        return JsonResponse({
            'success': True,
            'is_active': schedule.is_active,
            'message': f'Horario {"activado" if schedule.is_active else "desactivado"} exitosamente.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error al cambiar el estado del horario.'
        })