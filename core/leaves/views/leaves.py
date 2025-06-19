# core/leaves/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.db.models import Q
from django.http import JsonResponse
from datetime import datetime

from django.views.decorators.csrf import csrf_exempt

from ..models import LeaveType, LeaveRequest, LeaveBalance
from core.leaves.forms.LeavesForm import (
    LeaveTypeForm, LeaveRequestForm, LeaveRequestApprovalForm,
    LeaveBalanceForm, LeaveRequestFilterForm
)


# ==================== LEAVE TYPE VIEWS ====================

class LeaveTypeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Vista para listar tipos de licencia"""
    model = LeaveType
    template_name = 'components/parameters/leaves/leave_type/list.html'
    context_object_name = 'leave_types'
    permission_required = 'leaves.view_leavetype'
    paginate_by = 20

    def get_queryset(self):
        queryset = LeaveType.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(code__icontains=search)
            )
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context


class LeaveTypeDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Vista para ver detalles de un tipo de licencia"""
    model = LeaveType
    template_name = 'components/parameters/leaves/leave_type/detail.html'
    context_object_name = 'leave_type'
    permission_required = 'leaves.view_leavetype'


class LeaveTypeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para crear un nuevo tipo de licencia"""
    model = LeaveType
    form_class = LeaveTypeForm
    template_name = 'components/parameters/leaves/leave_type/form.html'
    permission_required = 'leaves.add_leavetype'
    success_url = reverse_lazy('leaves:leave_type_list')

    def form_valid(self, form):
        messages.success(self.request, 'Tipo de licencia creado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Tipo de Licencia'
        context['button_text'] = 'Crear'
        return context


class LeaveTypeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para actualizar un tipo de licencia"""
    model = LeaveType
    form_class = LeaveTypeForm
    template_name = 'components/parameters/leaves/leave_type/form.html'
    permission_required = 'leaves.change_leavetype'
    success_url = reverse_lazy('leaves:leave_type_list')

    def form_valid(self, form):
        messages.success(self.request, 'Tipo de licencia actualizado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Tipo de Licencia: {self.object.name}'
        context['button_text'] = 'Actualizar'
        return context


class LeaveTypeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista para eliminar un tipo de licencia"""
    model = LeaveType
    template_name = 'components/parameters/leaves/leave_type/delete.html'
    permission_required = 'leaves.delete_leavetype'
    success_url = reverse_lazy('leaves:leave_type_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Tipo de licencia eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)


# ==================== LEAVE REQUEST VIEWS ====================

class LeaveRequestListView(LoginRequiredMixin, ListView):
    """Vista para listar solicitudes de licencia"""
    model = LeaveRequest
    template_name = 'components/parameters/leaves/leave_request/list.html'
    context_object_name = 'leave_requests'
    paginate_by = 20

    def get_queryset(self):
        queryset = LeaveRequest.objects.select_related(
            'employee', 'leave_type', 'approved_by'
        )
        
        # Filtrar por empleado si no es supervisor
        if not self.request.user.has_perm('leaves.view_all_leaverequest'):
            try:
                from employees.models import Employee
                employee = Employee.objects.get(user=self.request.user)
                queryset = queryset.filter(employee=employee)
            except Employee.DoesNotExist:
                queryset = queryset.none()
        
        # Aplicar filtros del formulario
        form = LeaveRequestFilterForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get('employee'):
                queryset = queryset.filter(employee=form.cleaned_data['employee'])
            if form.cleaned_data.get('leave_type'):
                queryset = queryset.filter(leave_type=form.cleaned_data['leave_type'])
            if form.cleaned_data.get('status'):
                queryset = queryset.filter(status=form.cleaned_data['status'])
            if form.cleaned_data.get('start_date'):
                queryset = queryset.filter(start_date__gte=form.cleaned_data['start_date'])
            if form.cleaned_data.get('end_date'):
                queryset = queryset.filter(end_date__lte=form.cleaned_data['end_date'])
        
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = LeaveRequestFilterForm(self.request.GET)
        return context


class LeaveRequestDetailView(LoginRequiredMixin, DetailView):
    """Vista para ver detalles de una solicitud de licencia"""
    model = LeaveRequest
    template_name = 'components/parameters/leaves/leave_request/detail.html'
    context_object_name = 'leave_request'

    def get_queryset(self):
        queryset = LeaveRequest.objects.select_related(
            'employee', 'leave_type', 'approved_by'
        )
        
        # Solo mostrar propias solicitudes si no es supervisor
        if not self.request.user.has_perm('leaves.view_all_leaverequest'):
            try:
                from employees.models import Employee
                employee = Employee.objects.get(user=self.request.user)
                queryset = queryset.filter(employee=employee)
            except Employee.DoesNotExist:
                queryset = queryset.none()
        
        return queryset


class LeaveRequestCreateView(LoginRequiredMixin, CreateView):
    """Vista para crear una nueva solicitud de licencia"""
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'components/parameters/leaves/leave_request/form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Solicitud de licencia creada exitosamente.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('leaves:leave_request_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Solicitud de Licencia'
        context['button_text'] = 'Crear Solicitud'
        return context


class LeaveRequestUpdateView(LoginRequiredMixin, UpdateView):
    """Vista para actualizar una solicitud de licencia"""
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'components/parameters/leaves/leave_request/form.html'

    def get_queryset(self):
        queryset = LeaveRequest.objects.all()
        
        # Solo permitir editar propias solicitudes pendientes
        if not self.request.user.has_perm('leaves.change_all_leaverequest'):
            try:
                from employees.models import Employee
                employee = Employee.objects.get(user=self.request.user)
                queryset = queryset.filter(employee=employee, status='pending')
            except Employee.DoesNotExist:
                queryset = queryset.none()
        
        return queryset

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Solicitud de licencia actualizada exitosamente.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('leaves:leave_request_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Solicitud: {self.object.leave_type.name}'
        context['button_text'] = 'Actualizar'
        return context


class LeaveRequestDeleteView(LoginRequiredMixin, DeleteView):
    """Vista para eliminar una solicitud de licencia"""
    model = LeaveRequest
    template_name = 'components/parameters/leaves/leave_request/delete.html'
    success_url = reverse_lazy('leaves:leave_request_list')

    def get_queryset(self):
        queryset = LeaveRequest.objects.all()
        
        # Solo permitir eliminar propias solicitudes pendientes
        if not self.request.user.has_perm('leaves.delete_all_leaverequest'):
            try:
                from employees.models import Employee
                employee = Employee.objects.get(user=self.request.user)
                queryset = queryset.filter(employee=employee, status='pending')
            except Employee.DoesNotExist:
                queryset = queryset.none()
        
        return queryset

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Solicitud de licencia eliminada exitosamente.')
        return super().delete(request, *args, **kwargs)


class LeaveRequestApprovalView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para aprobar/rechazar solicitudes de licencia"""
    model = LeaveRequest
    form_class = LeaveRequestApprovalForm
    template_name = 'components/parameters/leaves/leave_request/approval.html'
    permission_required = 'leaves.approve_leaverequest'

    def get_queryset(self):
        return LeaveRequest.objects.filter(status='pending')

    def form_valid(self, form):
        # Establecer quien aprobó y cuándo
        form.instance.approved_by = self.request.user.employee
        form.instance.approved_date = datetime.now()
        
        # Actualizar balance si se aprueba
        if form.cleaned_data['status'] == 'approved':
            self.update_leave_balance()
        
        messages.success(
            self.request, 
            f'Solicitud {form.cleaned_data["status"]} exitosamente.'
        )
        return super().form_valid(form)

    def update_leave_balance(self):
        """Actualizar el balance de licencias del empleado"""
        try:
            balance = LeaveBalance.objects.get(
                employee=self.object.employee,
                leave_type=self.object.leave_type,
                year=self.object.start_date.year
            )
            balance.used_days += self.object.days_requested
            balance.remaining_days = (
                balance.allocated_days + balance.carried_forward - balance.used_days
            )
            balance.save()
        except LeaveBalance.DoesNotExist:
            # Crear balance si no existe
            LeaveBalance.objects.create(
                employee=self.object.employee,
                leave_type=self.object.leave_type,
                year=self.object.start_date.year,
                allocated_days=self.object.leave_type.days_allowed,
                used_days=self.object.days_requested,
                remaining_days=self.object.leave_type.days_allowed - self.object.days_requested
            )

    def get_success_url(self):
        return reverse('leaves:leave_request_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Aprobar/Rechazar: {self.object.leave_type.name}'
        return context


# ==================== LEAVE BALANCE VIEWS ====================

class LeaveBalanceListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Vista para listar balances de licencias"""
    model = LeaveBalance
    template_name = 'components/parameters/leaves/leave_balance/list.html'
    context_object_name = 'leave_balances'
    permission_required = 'leaves.view_leavebalance'
    paginate_by = 20

    def get_queryset(self):
        queryset = LeaveBalance.objects.select_related(
            'employee', 'leave_type'
        )
        
        # Filtros
        year = self.request.GET.get('year')
        employee = self.request.GET.get('employee')
        leave_type = self.request.GET.get('leave_type')
        
        if year:
            queryset = queryset.filter(year=year)
        if employee:
            queryset = queryset.filter(employee_id=employee)
        if leave_type:
            queryset = queryset.filter(leave_type_id=leave_type)
        
        return queryset.order_by('-year', 'employee__employee_number')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_year'] = datetime.now().year
        context['years'] = range(2020, 2031)
        return context


class LeaveBalanceDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Vista para ver detalles de un balance de licencia"""
    model = LeaveBalance
    template_name = 'components/parameters/leaves/leave_balance/detail.html'
    context_object_name = 'leave_balance'
    permission_required = 'leaves.view_leavebalance'


class LeaveBalanceCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para crear un nuevo balance de licencia"""
    model = LeaveBalance
    form_class = LeaveBalanceForm
    template_name = 'components/parameters/leaves/leave_balance/form.html'
    permission_required = 'leaves.add_leavebalance'
    success_url = reverse_lazy('leaves:leave_balance_list')

    def form_valid(self, form):
        messages.success(self.request, 'Balance de licencia creado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crear Balance de Licencia'
        context['button_text'] = 'Crear'
        return context


class LeaveBalanceUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para actualizar un balance de licencia"""
    model = LeaveBalance
    form_class = LeaveBalanceForm
    template_name = 'components/parameters/leaves/leave_balance/form.html'
    permission_required = 'leaves.change_leavebalance'
    success_url = reverse_lazy('leaves:leave_balance_list')

    def form_valid(self, form):
        messages.success(self.request, 'Balance de licencia actualizado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Balance: {self.object.employee.full_name}'
        context['button_text'] = 'Actualizar'
        return context


class LeaveBalanceDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista para eliminar un balance de licencia"""
    model = LeaveBalance
    template_name = 'components/parameters/leaves/leave_balance/delete.html'
    permission_required = 'leaves.delete_leavebalance'
    success_url = reverse_lazy('leaves:leave_balance_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Balance de licencia eliminado exitosamente.')
        return super().delete(request, *args, **kwargs)


# ==================== AJAX VIEWS ====================

def get_employee_balance(request):
    """Vista AJAX para obtener el balance de un empleado"""
    if request.is_ajax():
        employee_id = request.GET.get('employee_id')
        leave_type_id = request.GET.get('leave_type_id')
        year = request.GET.get('year', datetime.now().year)
        
        try:
            balance = LeaveBalance.objects.get(
                employee_id=employee_id,
                leave_type_id=leave_type_id,
                year=year
            )
            return JsonResponse({
                'success': True,
                'remaining_days': balance.remaining_days,
                'allocated_days': balance.allocated_days,
                'used_days': balance.used_days
            })
        except LeaveBalance.DoesNotExist:
            try:
                leave_type = LeaveType.objects.get(id=leave_type_id)
                return JsonResponse({
                    'success': True,
                    'remaining_days': leave_type.days_allowed,
                    'allocated_days': leave_type.days_allowed,
                    'used_days': 0
                })
            except LeaveType.DoesNotExist:
                return JsonResponse({'success': False})
    
    return JsonResponse({'success': False})


def calculate_leave_days(request):
    """Vista AJAX para calcular días de licencia"""
    if request.is_ajax():
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date and end_date:
            try:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                if start <= end:
                    days = (end - start).days + 1
                    return JsonResponse({
                        'success': True,
                        'days': days
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'La fecha de inicio debe ser anterior a la fecha de fin'
                    })
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Formato de fecha inválido'
                })
    
    return JsonResponse({'success': False})



@login_required
@permission_required('leaves.change_leavetype')
@require_POST
def leave_type_toggle_status(request, pk):
    """
    Vista AJAX para cambiar el estado activo/inactivo de un tipo de licencia
    """
    try:
        leave_type = get_object_or_404(LeaveType, pk=pk)
        
        # Cambiar el estado
        leave_type.is_active = not leave_type.is_active
        leave_type.save()
        
        return JsonResponse({
            'success': True,
            'is_active': leave_type.is_active,
            'message': f'Tipo de licencia {"activado" if leave_type.is_active else "desactivado"} exitosamente.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al cambiar el estado: {str(e)}'
        }, status=400)