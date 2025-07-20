# core/users/views/empresa.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.views.decorators.http import require_http_methods

from ..models import Company
from ..forms import CompanyForm


@login_required
def company_list(request):
    """
    Vista para listar todas las empresas
    """
    companies = Company.objects.all().order_by('-created_at')
    context = {
        'companies': companies,
        'title': 'Lista de Empresas'
    }
    return render(request, 'components/parameters/company/list.html', context)


@login_required
def company_detail(request, company_id):
    """
    Vista para mostrar detalles de una empresa
    """
    company = get_object_or_404(Company, id=company_id)
    context = {
        'company': company,
        'title': f'Empresa - {company.name}'
    }
    return render(request, 'components/parameters/company/detail.html', context)


@login_required
def company_create(request):
    """
    Vista para crear una nueva empresa
    """
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    company = form.save()
                    messages.success(
                        request,
                        f'Empresa "{company.name}" creada exitosamente.'
                    )
                    return redirect('users:company_detail', company_id=company.id)
            except Exception as e:
                messages.error(
                    request,
                    f'Error al crear la empresa: {str(e)}'
                )
        else:
            messages.error(
                request,
                'Por favor, corrija los errores en el formulario.'
            )
    else:
        form = CompanyForm()
    
    context = {
        'form': form,
        'title': 'Crear Nueva Empresa',
        'action': 'Crear'
    }
    return render(request, 'components/parameters/company/form.html', context)


@login_required
def company_edit(request, company_id):
    """
    Vista para editar una empresa existente
    """
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            try:
                with transaction.atomic():
                    company = form.save()
                    messages.success(
                        request,
                        f'Empresa "{company.name}" actualizada exitosamente.'
                    )
                    return redirect('users:company_detail', company_id=company.id)
            except Exception as e:
                messages.error(
                    request,
                    f'Error al actualizar la empresa: {str(e)}'
                )
        else:
            messages.error(
                request,
                'Por favor, corrija los errores en el formulario.'
            )
    else:
        form = CompanyForm(instance=company)
    
    context = {
        'form': form,
        'company': company,
        'title': f'Editar Empresa - {company.name}',
        'action': 'Actualizar'
    }
    return render(request, 'components/parameters/company/form.html', context)


@login_required
@require_http_methods(["POST"])
def company_delete(request, company_id):
    """
    Vista para eliminar una empresa
    """
    company = get_object_or_404(Company, id=company_id)
    
    try:
        # Verificar si es la empresa activa
        if company.is_active:
            messages.error(
                request,
                'No se puede eliminar la empresa activa. Primero desactívela.'
            )
            return redirect('users:company_detail', company_id=company.id)
        
        company_name = company.name
        company.delete()
        messages.success(
            request,
            f'Empresa "{company_name}" eliminada exitosamente.'
        )
        return redirect('users:company_list')
        
    except Exception as e:
        messages.error(
            request,
            f'Error al eliminar la empresa: {str(e)}'
        )
        return redirect('users:company_detail', company_id=company.id)


@login_required
@require_http_methods(["POST"])
def company_activate(request, company_id):
    """
    Vista para activar una empresa (desactivar las demás)
    """
    company = get_object_or_404(Company, id=company_id)
    
    try:
        with transaction.atomic():
            # Desactivar todas las empresas
            Company.objects.update(is_active=False)
            
            # Activar la empresa seleccionada
            company.is_active = True
            company.save()
            
            messages.success(
                request,
                f'Empresa "{company.name}" activada exitosamente.'
            )
            
    except Exception as e:
        messages.error(
            request,
            f'Error al activar la empresa: {str(e)}'
        )
    
    return redirect('users:company_detail', company_id=company.id)


@login_required
def company_settings(request):
    """
    Vista para configurar la empresa activa
    """
    company = Company.get_active_company()
    
    if not company:
        messages.info(
            request,
            'No hay una empresa activa. Por favor, cree una empresa primero.'
        )
        return redirect('users:company_create')
    
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            try:
                with transaction.atomic():
                    company = form.save()
                    messages.success(
                        request,
                        'Configuración de la empresa actualizada exitosamente.'
                    )
                    return redirect('users:company_settings')
            except Exception as e:
                messages.error(
                    request,
                    f'Error al actualizar la configuración: {str(e)}'
                )
        else:
            messages.error(
                request,
                'Por favor, corrija los errores en el formulario.'
            )
    else:
        form = CompanyForm(instance=company)
    
    context = {
        'form': form,
        'company': company,
        'title': 'Configuración de Empresa',
        'action': 'Actualizar Configuración'
    }
    return render(request, 'components/parameters/company/settings.html', context)


# Vista basada en clase para AJAX
@method_decorator(login_required, name='dispatch')
class CompanyAjaxView(View):
    """
    Vista para manejar peticiones AJAX relacionadas con empresas
    """
    
    def get(self, request):
        """
        Obtener información de empresa via AJAX
        """
        company_id = request.GET.get('company_id')
        
        if not company_id:
            return JsonResponse({
                'success': False,
                'message': 'ID de empresa requerido'
            })
        
        try:
            company = Company.objects.get(id=company_id)
            data = {
                'success': True,
                'company': {
                    'id': company.id,
                    'name': company.name,
                    'ruc': company.ruc,
                    'address': company.address,
                    'city': company.city,
                    'province': company.province,
                    'phone': company.phone,
                    'email': company.email,
                    'website': company.website,
                    'is_active': company.is_active,
                }
            }
            return JsonResponse(data)
            
        except Company.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Empresa no encontrada'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })
    
    def post(self, request):
        """
        Actualizar información de empresa via AJAX
        """
        company_id = request.POST.get('company_id')
        action = request.POST.get('action')
        
        if not company_id:
            return JsonResponse({
                'success': False,
                'message': 'ID de empresa requerido'
            })
        
        try:
            company = Company.objects.get(id=company_id)
            
            if action == 'toggle_active':
                # Cambiar estado activo
                if not company.is_active:
                    # Desactivar todas las empresas
                    Company.objects.update(is_active=False)
                    company.is_active = True
                    company.save()
                    message = f'Empresa "{company.name}" activada exitosamente.'
                else:
                    company.is_active = False
                    company.save()
                    message = f'Empresa "{company.name}" desactivada exitosamente.'
                
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'is_active': company.is_active
                })
            
            elif action == 'update_basic_info':
                # Actualizar información básica
                company.name = request.POST.get('name', company.name)
                company.phone = request.POST.get('phone', company.phone)
                company.email = request.POST.get('email', company.email)
                company.address = request.POST.get('address', company.address)
                
                try:
                    company.full_clean()
                    company.save()
                    return JsonResponse({
                        'success': True,
                        'message': 'Información básica actualizada exitosamente.'
                    })
                except ValidationError as e:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error de validación: {str(e)}'
                    })
            
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Acción no válida'
                })
                
        except Company.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Empresa no encontrada'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })


@login_required
def validate_ruc(request):
    """
    Vista para validar RUC via AJAX
    """
    ruc = request.GET.get('ruc', '').strip()
    company_id = request.GET.get('company_id')  # Para edición
    
    if not ruc:
        return JsonResponse({
            'valid': False,
            'message': 'RUC requerido'
        })
    
    # Verificar si ya existe (excepto en edición)
    query = Company.objects.filter(ruc=ruc)
    if company_id:
        query = query.exclude(id=company_id)
    
    if query.exists():
        return JsonResponse({
            'valid': False,
            'message': 'Este RUC ya está registrado'
        })
    
    # Validar formato usando la lógica del formulario
    form = CompanyForm(data={'ruc': ruc})
    if not form.is_valid() and 'ruc' in form.errors:
        return JsonResponse({
            'valid': False,
            'message': form.errors['ruc'][0]
        })
    
    return JsonResponse({
        'valid': True,
        'message': 'RUC válido'
    })


@login_required
def company_dashboard_info(request):
    """
    Vista para obtener información de la empresa para el dashboard
    """
    company = Company.get_active_company()
    
    if not company:
        return JsonResponse({
            'success': False,
            'message': 'No hay empresa activa'
        })
    
    data = {
        'success': True,
        'company': {
            'name': company.name,
            'ruc': company.ruc,
            'address': company.get_full_address(),
            'phone': company.phone,
            'email': company.email,
            'website': company.website,
        }
    }
    
    return JsonResponse(data)