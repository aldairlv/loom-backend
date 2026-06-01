from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile
from posts.tasks import initialize_user_in_recommendation_service_task


@receiver(post_save, sender=get_user_model())
def create_profile_for_new_user(sender, instance, created, **kwargs):
    """Create a Profile automatically when a new User is created."""
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={
                'display_name': instance.username or instance.email,
            }
        )


@receiver(post_save, sender=Profile)
def initialize_user_in_recommendation_service(sender, instance, created, **kwargs):
    """
    Cuando se crea un nuevo perfil (Profile), se lanza una tarea asíncrona
    para inicializar sus vectores de interés en el servicio de recomendación.
    """
    if created:
        # transaction.on_commit asegura que la tarea solo se encole
        # DESPUÉS de que la transacción de la base de datos que creó el perfil
        # se haya confirmado exitosamente.
        # Esto previene el "race condition" donde la tarea podría ejecutarse
        # antes de que el perfil exista en la BD.
        transaction.on_commit(lambda: initialize_user_in_recommendation_service_task.apply_async(args=[instance.id]))