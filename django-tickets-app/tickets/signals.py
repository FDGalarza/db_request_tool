from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, Solicitud, HistorialEstado

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Crear perfil de usuario automáticamente"""
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(pre_save, sender=Solicitud)
def track_status_changes(sender, instance, **kwargs):
    """Rastrear cambios de estado automáticamente"""
    if instance.pk:  # Solo para actualizaciones, no para creaciones
        try:
            old_instance = Solicitud.objects.get(pk=instance.pk)
            if old_instance.estado != instance.estado:
                # El cambio de estado se manejará en las vistas para incluir el usuario
                pass
        except Solicitud.DoesNotExist:
            pass
