from django import template
from ..models import TipoRubro

register = template.Library()

@register.simple_tag
def get_tipos_rubro():
    """Obtiene todos los tipos de rubro activos"""
    return TipoRubro.objects.filter(is_active=True).order_by('tipo', 'nombre')

@register.filter
def get_tipo_display(value):
    """Obtiene el display del tipo"""
    try:
        return value.get_tipo_display()
    except:
        return value