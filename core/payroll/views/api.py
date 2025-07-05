# core/payroll/views/api.py
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from core.employees.models import Employee
from ..models import Rubro, PayrollPeriod, AdelantoQuincena
import json


@login_required
@require_http_methods(["GET"])
def employee_info(request, employee_id):
    """API endpoint para obtener información detallada del empleado"""
    try:
        employee = get_object_or_404(Employee, pk=employee_id)
        
        # Obtener rubros automáticos
        automatic_rubros = Rubro.objects.filter(
            aplicar_automaticamente=True,
            is_active=True
        ).select_related('tipo_rubro')
        
        rubros_data = []
        for rubro in automatic_rubros:
            calculo_display = ""
            if rubro.tipo_calculo == 'fijo':
                calculo_display = f"${rubro.monto_default:.2f}" if rubro.monto_default else "Monto fijo"
            elif rubro.tipo_calculo == 'porcentaje':
                calculo_display = f"{rubro.porcentaje_default}%" if rubro.porcentaje_default else "Porcentaje"
            elif rubro.tipo_calculo == 'porcentaje_bruto':
                calculo_display = f"{rubro.porcentaje_default}% (bruto)" if rubro.porcentaje_default else "% del bruto"
            elif rubro.tipo_calculo == 'horas':
                calculo_display = f"{rubro.horas_default} hrs" if rubro.horas_default else "Por horas"
            
            rubros_data.append({
                'id': rubro.id,
                'nombre': rubro.nombre,
                'tipo': rubro.tipo_rubro.tipo,
                'tipo_display': rubro.tipo_rubro.get_tipo_display(),
                'calculo_display': calculo_display,
                'descripcion': rubro.descripcion
            })
        
        data = {
            'success': True,
            'employee': {
                'id': employee.id,
                'name': employee.user.get_full_name(),
                'employee_number': employee.employee_number,
                'email': employee.user.email,
                'department': employee.department.name if employee.department else None,
                'position': employee.position.title if employee.position else None,
                'salary': float(employee.salary) if hasattr(employee, 'salary') and employee.salary else 0,
                'status': employee.status,
                'status_display': employee.get_status_display(),
                'hourly_rate': float(employee.hourly_rate) if hasattr(employee, 'hourly_rate') and employee.hourly_rate else None,
            },
            'automatic_rubros': rubros_data
        }
        
        return JsonResponse(data)
        
    except Employee.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Empleado no encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def rubro_info(request, rubro_id):
    """API endpoint para obtener información detallada del rubro"""
    try:
        rubro = get_object_or_404(Rubro, pk=rubro_id)
        
        data = {
            'success': True,
            'rubro': {
                'id': rubro.id,
                'nombre': rubro.nombre,
                'codigo': rubro.codigo,
                'descripcion': rubro.descripcion,
                'tipo_calculo': rubro.tipo_calculo,
                'tipo_calculo_display': rubro.get_tipo_calculo_display(),
                'monto_default': float(rubro.monto_default) if rubro.monto_default else None,
                'porcentaje_default': float(rubro.porcentaje_default) if rubro.porcentaje_default else None,
                'horas_default': float(rubro.horas_default) if rubro.horas_default else None,
                'tipo_rubro': {
                    'id': rubro.tipo_rubro.id,
                    'nombre': rubro.tipo_rubro.nombre,
                    'tipo': rubro.tipo_rubro.tipo,
                    'tipo_display': rubro.tipo_rubro.get_tipo_display()
                },
                'aplicar_automaticamente': rubro.aplicar_automaticamente,
                'is_active': rubro.is_active
            }
        }
        
        return JsonResponse(data)
        
    except Rubro.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Rubro no encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def employee_adelantos(request, employee_id):
    """API endpoint para obtener adelantos pendientes del empleado"""
    try:
        employee = get_object_or_404(Employee, pk=employee_id)
        period_id = request.GET.get('period_id')
        
        adelantos_query = AdelantoQuincena.objects.filter(
            employee=employee,
            is_processed=False
        ).order_by('-fecha_adelanto')
        
        if period_id:
            adelantos_query = adelantos_query.filter(periodo_descuento_id=period_id)
        
        adelantos_data = []
        for adelanto in adelantos_query:
            adelantos_data.append({
                'id': adelanto.id,
                'monto': float(adelanto.monto),
                'fecha_adelanto': adelanto.fecha_adelanto.strftime('%d/%m/%Y'),
                'motivo': adelanto.motivo,
                'observaciones': adelanto.observaciones,
                'periodo_descuento': {
                    'id': adelanto.periodo_descuento.id,
                    'name': adelanto.periodo_descuento.name
                } if adelanto.periodo_descuento else None
            })
        
        data = {
            'success': True,
            'employee': {
                'id': employee.id,
                'name': employee.user.get_full_name()
            },
            'adelantos': adelantos_data,
            'total_adelantos': sum(float(a.monto) for a in adelantos_query)
        }
        
        return JsonResponse(data)
        
    except Employee.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Empleado no encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def period_employees(request, period_id):
    """API endpoint para obtener empleados del período"""
    try:
        period = get_object_or_404(PayrollPeriod, pk=period_id)
        
        # Empleados activos
        active_employees = Employee.objects.filter(status='active').select_related(
            'user', 'department', 'position'
        )
        
        # Empleados que ya tienen nómina en este período
        employees_with_payroll = set(
            period.payroll_entries.values_list('employee_id', flat=True)
        )
        
        employees_data = []
        for employee in active_employees:
            has_payroll = employee.id in employees_with_payroll
            
            employees_data.append({
                'id': employee.id,
                'name': employee.user.get_full_name(),
                'employee_number': employee.employee_number,
                'email': employee.user.email,
                'department': employee.department.name if employee.department else None,
                'position': employee.position.title if employee.position else None,
                'salary': float(employee.salary) if hasattr(employee, 'salary') and employee.salary else 0,
                'has_payroll': has_payroll,
                'status': employee.status,
                'status_display': employee.get_status_display()
            })
        
        data = {
            'success': True,
            'period': {
                'id': period.id,
                'name': period.name,
                'start_date': period.start_date.strftime('%d/%m/%Y'),
                'end_date': period.end_date.strftime('%d/%m/%Y'),
                'status': period.status,
                'status_display': period.get_status_display()
            },
            'employees': employees_data,
            'total_employees': len(employees_data),
            'employees_with_payroll': len(employees_with_payroll),
            'employees_pending': len(employees_data) - len(employees_with_payroll)
        }
        
        return JsonResponse(data)
        
    except PayrollPeriod.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Período no encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def calculate_payroll_preview(request):
    """API endpoint para calcular preview de nómina"""
    try:
        data = json.loads(request.body)
        
        employee_id = data.get('employee_id')
        base_salary = float(data.get('base_salary', 0))
        overtime_hours = float(data.get('overtime_hours', 0))
        overtime_rate = float(data.get('overtime_rate', 1.5))
        
        # Calcular pago por horas extra
        overtime_pay = (base_salary / 160) * overtime_hours * overtime_rate
        
        # Pago bruto básico
        gross_pay = base_salary + overtime_pay
        
        # Calcular rubros automáticos si hay empleado
        total_ingresos_rubros = 0
        total_egresos_rubros = 0
        
        if employee_id:
            employee = get_object_or_404(Employee, pk=employee_id)
            automatic_rubros = Rubro.objects.filter(
                aplicar_automaticamente=True,
                is_active=True
            )
            
            for rubro in automatic_rubros:
                monto = 0
                
                if rubro.tipo_calculo == 'fijo':
                    monto = float(rubro.monto_default or 0)
                elif rubro.tipo_calculo == 'porcentaje':
                    monto = (base_salary * float(rubro.porcentaje_default or 0)) / 100
                elif rubro.tipo_calculo == 'porcentaje_bruto':
                    monto = (gross_pay * float(rubro.porcentaje_default or 0)) / 100
                elif rubro.tipo_calculo == 'horas':
                    if hasattr(employee, 'hourly_rate') and employee.hourly_rate:
                        monto = float(employee.hourly_rate) * float(rubro.horas_default or 0)
                
                if rubro.tipo_rubro.tipo == 'ingreso':
                    total_ingresos_rubros += monto
                else:
                    total_egresos_rubros += monto
        
        # Recalcular totales
        final_gross_pay = gross_pay + total_ingresos_rubros
        final_net_pay = final_gross_pay - total_egresos_rubros
        
        response_data = {
            'success': True,
            'calculations': {
                'base_salary': base_salary,
                'overtime_hours': overtime_hours,
                'overtime_pay': overtime_pay,
                'gross_pay': final_gross_pay,
                'total_ingresos_rubros': total_ingresos_rubros,
                'total_egresos_rubros': total_egresos_rubros,
                'net_pay': final_net_pay
            }
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)