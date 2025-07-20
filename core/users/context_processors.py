# core/users/context_processors.py
from .models import Company

def company_context(request):
    """
    Context processor para hacer disponible la información de la empresa
    activa en todos los templates.
    """
    active_company = Company.get_active_company()
    
    return {
        'company_name': active_company.name if active_company else None,
        'company_ruc': active_company.ruc if active_company else None,
        'company_email': active_company.email if active_company else None,
        'company_phone': active_company.phone if active_company else None,
        'company_website': active_company.website if active_company else None,
        'company_address': active_company.get_full_address() if active_company else None,
        'active_company': active_company,
    }