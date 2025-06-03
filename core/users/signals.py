from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import UserProfile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Crear o actualizar automáticamente un UserProfile cuando se crea/actualiza un User
    """
    # Usar get_or_create para evitar duplicados
    profile, created_profile = UserProfile.objects.get_or_create(user=instance)
    
    # Si el perfil ya existía, guardarlo para actualizar timestamps
    if not created_profile:
        profile.save()