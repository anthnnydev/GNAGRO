from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
from django.utils import timezone
from ..models import Payroll, PayrollPeriod, PayrollRubro
from datetime import datetime, timedelta
import csv


@login_required
def payroll_reports(request):
    """Dashboard de reportes de nómina"""
    # Estadísticas generales
    total_employees_with_payroll = Payroll.objects.values('employee').distinct().count()
    total_periods = PayrollPeriod.objects.count()
    paid_payrolls = Payroll.objects.filter(is_paid=True)
    total_paid = sum(payroll.net_pay for payroll in paid_payrolls)
    pending_payments = Payroll.objects.filter(is_paid=False).count()
    
    # Últimos períodos
    recent_periods = PayrollPeriod.objects.order_by('-created_at')[:5]
    
    # Rubros más utilizados
    top_rubros = PayrollRubro.objects.values(
        'rubro__nombre', 'rubro__tipo_rubro__tipo'
    ).annotate(
        total_aplicaciones=Count('id'),
        total_monto=Sum('monto')
    ).order_by('-total_aplicaciones')[:10]
    
    context = {
        'total_employees_with_payroll': total_employees_with_payroll,
        'total_periods': total_periods,
        'total_paid': total_paid,
        'pending_payments': pending_payments,
        'recent_periods': recent_periods,
        'top_rubros': top_rubros,
    }
    
    return render(request, 'pages/admin/reports/dashboard.html', context)


@login_required
def export_payroll_csv(request):
    """Exportar nóminas a CSV"""
    period_id = request.GET.get('period')
    
    payrolls = Payroll.objects.select_related('employee', 'period').all()
    
    if period_id:
        payrolls = payrolls.filter(period_id=period_id)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="nominas.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Empleado', 'Período', 'Salario Base', 'Horas Extra', 
        'Bonificaciones', 'Comisiones', 'Pago Bruto', 
        'Total Deducciones', 'Pago Neto', 'Pagado', 'Fecha Pago'
    ])
    
    for payroll in payrolls:
        writer.writerow([
            payroll.employee.user.get_full_name(),
            payroll.period.name,
            payroll.base_salary,
            payroll.overtime_hours,
            payroll.overtime_pay,
            payroll.gross_pay,
            payroll.total_deductions,
            payroll.net_pay,
            'Sí' if payroll.is_paid else 'No',
            payroll.payment_date or ''
        ])
    
    return response