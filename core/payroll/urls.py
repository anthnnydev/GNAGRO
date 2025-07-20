# core/payroll/urls.py
from django.urls import path, include
from core.payroll.views import (
    payroll_views, 
    period_views,
    report_views,
    rubro_views,
    adelanto_views
)
from core.payroll.views.payroll_views import (
    payroll_list, payroll_form, payroll_detail, payroll_process_adelantos, payroll_mark_paid
)
from core.payroll.views.api import (
    rubro_info, employee_adelantos, period_employees, employee_info,
    calculate_payroll_preview
)
from core.payroll.views.rubro_views import (
    rubro_list, rubro_form, tipo_rubro_list, tipo_rubro_form
)
from core.payroll.views.period_views import (
    period_list, period_form, period_detail, period_generate_payrolls,
    period_close, period_reopen
)
from core.payroll.views.adelanto_views import (
    adelanto_list, adelanto_form
)
from core.payroll.views.report_views import (
    payroll_reports, export_payroll_csv
)

app_name = 'payroll'

urlpatterns = [
    # Dashboard de nómina
    path('admin/nomina-dashboard/', payroll_reports, name='nomina_dashboard'),
    
    # Nóminas
    path('admin/nominas/', payroll_list, name='payroll_list'),
    path('admin/nominas/crear/', payroll_form, name='payroll_create'),
    path('admin/nominas/<int:pk>/', payroll_detail, name='payroll_detail'),
    path('admin/nominas/<int:pk>/editar/', payroll_form, name='payroll_edit'),
    path('admin/nominas/<int:pk>/procesar-adelantos/', payroll_process_adelantos, name='payroll_process_adelantos'),
    path('admin/nominas/<int:payroll_pk>/seleccionar-rubro/', payroll_views.payroll_select_rubro, name='payroll_select_rubro'),
    path('admin/nominas/<int:payroll_pk>/remove-rubro/<int:rubro_pk>/', payroll_views.payroll_remove_rubro, name='payroll_remove_rubro'),
    path('payroll/<int:pk>/mark-paid/', payroll_views.payroll_mark_paid, name='payroll_mark_paid'),
    
    # Procesamiento masivo de pagos
    path('payroll/bulk-mark-paid/',
         payroll_views.payroll_bulk_mark_paid,
         name='payroll_bulk_mark_paid'),
    
    # Rubros
    path('admin/rubros/', rubro_list, name='rubro_list'),
    path('admin/rubros/crear/', rubro_form, name='rubro_create'),
    path('admin/rubros/<int:pk>/editar/', rubro_form, name='rubro_edit'),
    path('admin/rubros/<int:pk>/toggle-status/', rubro_views.rubro_toggle_status, name='rubro_toggle_status'),
    
    # URLs de Tipos de Rubro
    path('admin/rubros/tipos/', rubro_views.tipo_rubro_list, name='tipo_rubro_list'),
    path('admin/rubros/tipos/crear/', rubro_views.tipo_rubro_form, name='tipo_rubro_form'),
    path('admin/rubros/tipos/<int:pk>/editar/', rubro_views.tipo_rubro_form, name='tipo_rubro_form'),
    
    # URLs de Períodos
    path('admin/periodos/', period_views.period_list, name='period_list'),
    path('admin/periodos/crear/', period_views.period_form, name='period_form'),
    path('admin/periodos/<int:pk>/editar/', period_views.period_form, name='period_form'),
    path('admin/periodos/<int:pk>/', period_views.period_detail, name='period_detail'),
    path('admin/periodos/<int:pk>/generar-nominas/', period_views.period_generate_payrolls, name='period_generate_payrolls'),
    path('admin/periodos/<int:pk>/cerrar/', period_views.period_close, name='period_close'),
    path('admin/periodos/<int:pk>/reabrir/', period_views.period_reopen, name='period_reopen'),
    path('admin/periods/<int:pk>/mark-all-paid/', period_views.period_mark_all_paid, name='period_mark_all_paid'),

    
    # Adelantos
    path('admin/adelantos/', adelanto_list, name='adelanto_list'),
    path('admin/adelantos/crear/', adelanto_form, name='adelanto_create'),
    path('admin/adelantos/<int:pk>/editar/', adelanto_form, name='adelanto_edit'),
    
    # Reportes y Exportación
    path('admin/reportes/', payroll_reports, name='reports'),
    path('admin/exportar/csv/', export_payroll_csv, name='export_csv'),
    
    # API endpoints
    path('admin/api/rubros/<int:rubro_id>/info/', rubro_info, name='api_rubro_info'),
    path('admin/api/empleados/<int:employee_id>/adelantos/', employee_adelantos, name='api_employee_adelantos'),
    path('admin/api/empleados/<int:employee_id>/info/', employee_info, name='api_employee_info'),
    path('admin/api/periodos/<int:period_id>/empleados/', period_employees, name='api_period_employees'),
    path('admin/api/calcular-nomina-preview/', calculate_payroll_preview, name='api_calculate_payroll_preview'),
    path('admin/api/rubros/<int:rubro_id>/', payroll_views.get_rubro_info, name='api_get_rubro_info'),
]