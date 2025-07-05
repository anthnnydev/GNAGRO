# Crear archivo: core/external_payments/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal
import json

from .models import ExternalWorker, ExternalPayment, ServiceType, ExternalPaymentDocument
from .forms import ExternalWorkerForm, ExternalPaymentForm, ServiceTypeForm


class ExternalWorkerListView(LoginRequiredMixin, ListView):
    """Lista de trabajadores externos"""
    model = ExternalWorker
    template_name = 'pages/admin/external_payments/workers/list.html'
    context_object_name = 'workers'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = ExternalWorker.objects.all().order_by('-created_at')
        
        # Filtros
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search) |
                Q(identification_number__icontains=search) |
                Q(ruc_number__icontains=search)
            )
        
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        has_ruc = self.request.GET.get('has_ruc')
        if has_ruc == 'yes':
            queryset = queryset.filter(has_ruc=True)
        elif has_ruc == 'no':
            queryset = queryset.filter(has_ruc=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_workers'] = ExternalWorker.objects.count()
        context['active_workers'] = ExternalWorker.objects.filter(is_active=True).count()
        context['workers_with_ruc'] = ExternalWorker.objects.filter(has_ruc=True).count()
        
        # Filtros actuales
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'status': self.request.GET.get('status', ''),
            'has_ruc': self.request.GET.get('has_ruc', ''),
        }
        
        return context


class ExternalWorkerCreateView(LoginRequiredMixin, CreateView):
    """Crear trabajador externo"""
    model = ExternalWorker
    form_class = ExternalWorkerForm
    template_name = 'pages/admin/external_payments/workers/form.html'
    success_url = reverse_lazy('external_payments:worker_list')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Trabajador externo {form.instance.full_name} registrado correctamente.')
        return super().form_valid(form)


class ExternalWorkerUpdateView(LoginRequiredMixin, UpdateView):
    """Actualizar trabajador externo"""
    model = ExternalWorker
    form_class = ExternalWorkerForm
    template_name = 'pages/admin/external_payments/workers/form.html'
    
    def get_success_url(self):
        return reverse_lazy('external_payments:worker_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f'Trabajador externo {form.instance.full_name} actualizado correctamente.')
        return super().form_valid(form)


class ExternalWorkerDetailView(LoginRequiredMixin, DetailView):
    """Detalle de trabajador externo"""
    model = ExternalWorker
    template_name = 'pages/admin/external_payments/workers/detail.html'
    context_object_name = 'worker'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pagos del trabajador
        payments = self.object.external_payments.all().order_by('-created_at')
        context['payments'] = payments[:10]  # Últimos 10
        context['total_payments'] = payments.count()
        context['total_amount'] = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        context['pending_payments'] = payments.filter(status='pending').count()
        
        # Estadísticas por año
        current_year = timezone.now().year
        context['current_year_total'] = payments.filter(
            payment_date__year=current_year
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        return context


# ==================== PAGOS EXTERNOS ====================

class ExternalPaymentListView(LoginRequiredMixin, ListView):
    """Lista de pagos externos"""
    model = ExternalPayment
    template_name = 'pages/admin/external_payments/payments/list.html'
    context_object_name = 'payments'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = ExternalPayment.objects.select_related(
            'external_worker', 'service_type'
        ).order_by('-created_at')
        
        # Filtros
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(external_worker__full_name__icontains=search) |
                Q(work_description__icontains=search) |
                Q(invoice_number__icontains=search)
            )
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        service_type = self.request.GET.get('service_type')
        if service_type:
            queryset = queryset.filter(service_type_id=service_type)
        
        worker = self.request.GET.get('worker')
        if worker:
            queryset = queryset.filter(external_worker_id=worker)
        
        # Filtro por fechas
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(start_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(end_date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Para filtros
        context['service_types'] = ServiceType.objects.filter(is_active=True)
        context['workers'] = ExternalWorker.objects.filter(is_active=True).order_by('full_name')
        
        # Estadísticas
        all_payments = ExternalPayment.objects.all()
        context['total_payments'] = all_payments.count()
        context['pending_payments'] = all_payments.filter(status='pending').count()
        context['paid_payments'] = all_payments.filter(status='paid').count()
        context['total_amount'] = all_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        context['pending_amount'] = all_payments.filter(status='pending').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Filtros actuales
        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'status': self.request.GET.get('status', ''),
            'service_type': self.request.GET.get('service_type', ''),
            'worker': self.request.GET.get('worker', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
        }
        
        return context


class ExternalPaymentCreateView(LoginRequiredMixin, CreateView):
    """Crear pago externo"""
    model = ExternalPayment
    form_class = ExternalPaymentForm
    template_name = 'pages/admin/external_payments/payments/form.html'
    success_url = reverse_lazy('external_payments:payment_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Si se especifica un trabajador en la URL
        worker_id = self.request.GET.get('worker')
        if worker_id:
            try:
                worker = ExternalWorker.objects.get(id=worker_id)
                context['preselected_worker'] = worker
            except ExternalWorker.DoesNotExist:
                pass
        
        return context
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # Calcular retención automática si aplica
        if form.instance.requires_tax_withholding and not form.instance.tax_withheld:
            form.instance.tax_withheld = form.instance.calculate_tax_withholding()
        
        messages.success(
            self.request, 
            f'Pago por servicio externo registrado: {form.instance.external_worker.full_name} - ${form.instance.amount}'
        )
        return super().form_valid(form)


class ExternalPaymentUpdateView(LoginRequiredMixin, UpdateView):
    """Actualizar pago externo"""
    model = ExternalPayment
    form_class = ExternalPaymentForm
    template_name = 'pages/admin/external_payments/payments/form.html'
    
    def get_success_url(self):
        return reverse_lazy('external_payments:payment_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Pago por servicio externo actualizado correctamente.')
        return super().form_valid(form)


class ExternalPaymentDetailView(LoginRequiredMixin, DetailView):
    """Detalle de pago externo"""
    model = ExternalPayment
    template_name = 'pages/admin/external_payments/payments/detail.html'
    context_object_name = 'payment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['documents'] = self.object.documents.all()
        
        # Otros pagos del mismo trabajador
        context['other_payments'] = self.object.external_worker.external_payments.exclude(
            id=self.object.id
        ).order_by('-created_at')[:5]
        
        return context


# ==================== TIPOS DE SERVICIOS ====================

class ServiceTypeListView(LoginRequiredMixin, ListView):
    """Lista de tipos de servicios"""
    model = ServiceType
    template_name = 'pages/admin/external_payments/services/list.html'
    context_object_name = 'service_types'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas de uso
        for service_type in context['service_types']:
            service_type.payments_count = service_type.payments.count()
            service_type.total_amount = service_type.payments.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
        
        return context


class ServiceTypeCreateView(LoginRequiredMixin, CreateView):
    """Crear tipo de servicio"""
    model = ServiceType
    form_class = ServiceTypeForm
    template_name = 'pages/admin/external_payments/services/form.html'
    success_url = reverse_lazy('external_payments:service_type_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Tipo de servicio {form.instance.name} creado correctamente.')
        return super().form_valid(form)


# ==================== VISTAS AUXILIARES ====================

@login_required
def mark_payment_as_paid(request, pk):
    """Marcar pago como realizado"""
    payment = get_object_or_404(ExternalPayment, pk=pk)
    
    if request.method == 'POST':
        payment_date = request.POST.get('payment_date') or timezone.now().date()
        payment_method = request.POST.get('payment_method', 'cash')
        
        payment.mark_as_paid(payment_date, payment_method)
        
        messages.success(
            request,
            f'Pago a {payment.external_worker.full_name} marcado como realizado (${payment.amount})'
        )
    
    return redirect('external_payments:payment_detail', pk=pk)


@login_required
def bulk_mark_payments_paid(request):
    """Marcar múltiples pagos como realizados"""
    if request.method == 'POST':
        payment_ids = request.POST.getlist('payment_ids')
        payment_method = request.POST.get('payment_method', 'cash')
        payment_date = request.POST.get('payment_date') or timezone.now().date()
        
        updated_count = 0
        
        for payment_id in payment_ids:
            try:
                payment = ExternalPayment.objects.get(id=payment_id, status='pending')
                payment.mark_as_paid(payment_date, payment_method)
                updated_count += 1
            except ExternalPayment.DoesNotExist:
                continue
        
        messages.success(request, f'Se marcaron {updated_count} pagos como realizados.')
    
    return redirect('external_payments:payment_list')


@login_required
def external_payment_stats_api(request):
    """API para estadísticas de pagos externos"""
    from datetime import date, timedelta
    
    # Estadísticas por mes (últimos 12 meses)
    monthly_stats = []
    for i in range(12):
        month_date = date.today().replace(day=1) - timedelta(days=30*i)
        month_payments = ExternalPayment.objects.filter(
            payment_date__year=month_date.year,
            payment_date__month=month_date.month,
            status='paid'
        )
        
        monthly_stats.append({
            'month': month_date.strftime('%Y-%m'),
            'month_name': month_date.strftime('%B %Y'),
            'count': month_payments.count(),
            'total_amount': float(month_payments.aggregate(total=Sum('amount'))['total'] or 0)
        })
    
    # Top trabajadores
    top_workers = ExternalWorker.objects.annotate(
        total_amount=Sum('external_payments__amount'),
        payments_count=Count('external_payments')
    ).filter(
        total_amount__gt=0
    ).order_by('-total_amount')[:10]
    
    top_workers_data = [
        {
            'name': worker.full_name,
            'total_amount': float(worker.total_amount or 0),
            'payments_count': worker.payments_count
        }
        for worker in top_workers
    ]
    
    # Top servicios
    top_services = ServiceType.objects.annotate(
        total_amount=Sum('payments__amount'),
        payments_count=Count('payments')
    ).filter(
        total_amount__gt=0
    ).order_by('-total_amount')[:10]
    
    top_services_data = [
        {
            'name': service.name,
            'total_amount': float(service.total_amount or 0),
            'payments_count': service.payments_count
        }
        for service in top_services
    ]
    
    return JsonResponse({
        'monthly_stats': monthly_stats,
        'top_workers': top_workers_data,
        'top_services': top_services_data
    })


@login_required
def worker_ajax_search(request):
    """Búsqueda AJAX de trabajadores externos"""
    query = request.GET.get('q', '')
    workers = []
    
    if len(query) >= 2:
        worker_list = ExternalWorker.objects.filter(
            Q(full_name__icontains=query) |
            Q(identification_number__icontains=query) |
            Q(ruc_number__icontains=query)
        ).filter(is_active=True)[:10]
        
        workers = [{
            'id': worker.id,
            'text': f"{worker.full_name} ({worker.identification_number})",
            'full_name': worker.full_name,
            'identification': worker.identification_number,
            'has_ruc': worker.has_ruc,
            'ruc_number': worker.ruc_number,
            'can_issue_invoice': worker.can_issue_invoice
        } for worker in worker_list]
    
    return JsonResponse({'results': workers})


@login_required
def service_rate_api(request, service_id):
    """API para obtener tarifa por defecto de un servicio"""
    try:
        service = ServiceType.objects.get(id=service_id)
        return JsonResponse({
            'success': True,
            'default_rate': float(service.default_rate or 0),
            'default_unit': service.default_unit,
            'requires_invoice': service.requires_invoice
        })
    except ServiceType.DoesNotExist:
        return JsonResponse({'success': False})


@login_required
def export_external_payments_csv(request):
    """Exportar pagos externos a CSV"""
    import csv
    from django.http import HttpResponse
    
    # Aplicar filtros de la lista
    queryset = ExternalPaymentListView().get_queryset()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="pagos_externos.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Trabajador',
        'Identificación',
        'Tipo de Servicio',
        'Descripción',
        'Fecha Inicio',
        'Fecha Fin',
        'Cantidad',
        'Unidad',
        'Tarifa',
        'Monto Total',
        'Estado',
        'Fecha Pago',
        'Método Pago',
        'Factura',
        'Retención'
    ])
    
    for payment in queryset:
        writer.writerow([
            payment.external_worker.full_name,
            payment.external_worker.identification_number,
            payment.service_type.name,
            payment.work_description,
            payment.start_date,
            payment.end_date,
            payment.quantity,
            payment.unit,
            payment.unit_rate,
            payment.amount,
            payment.get_status_display(),
            payment.payment_date,
            payment.get_payment_method_display(),
            payment.invoice_number,
            payment.tax_withheld
        ])
    
    return response


@login_required
def dashboard_external_payments(request):
    """Dashboard principal de pagos externos"""
    from datetime import date, timedelta
    
    # Estadísticas generales
    total_workers = ExternalWorker.objects.filter(is_active=True).count()
    total_payments = ExternalPayment.objects.count()
    pending_payments = ExternalPayment.objects.filter(status='pending').count()
    total_amount_year = ExternalPayment.objects.filter(
        payment_date__year=date.today().year,
        status='paid'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Pagos pendientes por trabajador
    pending_by_worker = ExternalPayment.objects.filter(
        status='pending'
    ).values(
        'external_worker__full_name',
        'external_worker__id'
    ).annotate(
        count=Count('id'),
        total_amount=Sum('amount')
    ).order_by('-total_amount')[:10]
    
    # Pagos recientes
    recent_payments = ExternalPayment.objects.select_related(
        'external_worker', 'service_type'
    ).order_by('-created_at')[:10]
    
    # Servicios más utilizados
    top_services = ServiceType.objects.annotate(
        payments_count=Count('payments'),
        total_amount=Sum('payments__amount')
    ).filter(payments_count__gt=0).order_by('-payments_count')[:5]
    
    context = {
        'total_workers': total_workers,
        'total_payments': total_payments,
        'pending_payments': pending_payments,
        'total_amount_year': total_amount_year,
        'pending_by_worker': pending_by_worker,
        'recent_payments': recent_payments,
        'top_services': top_services,
    }
    
    return render(request, 'pages/admin/external_payments/dashboard.html', context)


# ==================== REPORTES ====================

@login_required
def external_payments_report(request):
    """Reporte detallado de pagos externos"""
    from datetime import date, timedelta
    
    # Parámetros del reporte
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    worker_id = request.GET.get('worker')
    service_type_id = request.GET.get('service_type')
    
    # Si no hay fechas, usar último mes
    if not start_date or not end_date:
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
    else:
        start_date = date.fromisoformat(start_date)
        end_date = date.fromisoformat(end_date)
    
    # Filtrar pagos
    payments = ExternalPayment.objects.filter(
        payment_date__range=[start_date, end_date]
    ).select_related('external_worker', 'service_type')
    
    if worker_id:
        payments = payments.filter(external_worker_id=worker_id)
    
    if service_type_id:
        payments = payments.filter(service_type_id=service_type_id)
    
    # Resumen
    total_payments = payments.count()
    total_amount = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_tax_withheld = payments.aggregate(total=Sum('tax_withheld'))['total'] or Decimal('0.00')
    
    # Agrupaciones
    by_worker = payments.values(
        'external_worker__full_name',
        'external_worker__identification_number'
    ).annotate(
        count=Count('id'),
        total_amount=Sum('amount'),
        total_tax=Sum('tax_withheld')
    ).order_by('-total_amount')
    
    by_service = payments.values(
        'service_type__name'
    ).annotate(
        count=Count('id'),
        total_amount=Sum('amount')
    ).order_by('-total_amount')
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'payments': payments,
        'total_payments': total_payments,
        'total_amount': total_amount,
        'total_tax_withheld': total_tax_withheld,
        'by_worker': by_worker,
        'by_service': by_service,
        'workers': ExternalWorker.objects.filter(is_active=True).order_by('full_name'),
        'service_types': ServiceType.objects.filter(is_active=True).order_by('name'),
        'selected_worker': worker_id,
        'selected_service_type': service_type_id,
    }
    
    return render(request, 'pages/admin/external_payments/reports.html', context)


@login_required
def generate_payment_receipt(request, pk):
    """Generar recibo de pago"""
    payment = get_object_or_404(ExternalPayment, pk=pk)
    
    if payment.status != 'paid':
        messages.error(request, 'Solo se pueden generar recibos para pagos realizados.')
        return redirect('external_payments:payment_detail', pk=pk)
    
    context = {
        'payment': payment,
        'company_name': 'Su Empresa',  # Configurar según su empresa
        'company_address': 'Dirección de su empresa',
        'company_phone': 'Teléfono de su empresa',
    }
    
    return render(request, 'pages/admin/external_payments/receipt.html', context)


# ==================== VALIDACIONES ====================

@login_required
def validate_identification(request):
    """Validar número de identificación para evitar duplicados"""
    identification = request.GET.get('identification')
    worker_id = request.GET.get('worker_id')  # Para edición
    
    if not identification:
        return JsonResponse({'valid': True})
    
    exists = ExternalWorker.objects.filter(
        identification_number=identification
    )
    
    if worker_id:
        exists = exists.exclude(id=worker_id)
    
    return JsonResponse({
        'valid': not exists.exists(),
        'message': 'Este número de identificación ya está registrado.' if exists.exists() else ''
    })


@login_required
def calculate_tax_withholding_api(request):
    """API para calcular retención automática"""
    amount = request.GET.get('amount')
    has_ruc = request.GET.get('has_ruc') == 'true'
    
    try:
        amount = Decimal(amount)
        
        # Lógica de retención (ejemplo para Ecuador)
        if amount > Decimal('300.00') and not has_ruc:
            # 2% para personas naturales sin RUC
            tax_withheld = (amount * Decimal('2.00')) / 100
            should_withhold = True
        else:
            tax_withheld = Decimal('0.00')
            should_withhold = False
        
        return JsonResponse({
            'should_withhold': should_withhold,
            'tax_withheld': float(tax_withheld),
            'net_payment': float(amount - tax_withheld),
            'message': f'Retención del 2% aplicada (${tax_withheld:.2f})' if should_withhold else 'No requiere retención'
        })
    
    except:
        return JsonResponse({'error': 'Monto inválido'})


# ==================== GESTIÓN DE DOCUMENTOS ====================

@login_required
def upload_payment_document(request, payment_pk):
    """Subir documento para un pago"""
    payment = get_object_or_404(ExternalPayment, pk=payment_pk)
    
    if request.method == 'POST':
        document_type = request.POST.get('document_type')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        file = request.FILES.get('file')
        
        if file and document_type and name:
            ExternalPaymentDocument.objects.create(
                external_payment=payment,
                document_type=document_type,
                name=name,
                file=file,
                description=description
            )
            messages.success(request, 'Documento subido correctamente.')
        else:
            messages.error(request, 'Todos los campos son requeridos.')
    
    return redirect('external_payments:payment_detail', pk=payment_pk)