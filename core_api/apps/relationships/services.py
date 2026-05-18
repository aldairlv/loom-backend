from django.core.exceptions import ObjectDoesNotExist
from .models import Follow
from profiles.models import Profile


def get_follow_queryset():
    """Devuelve el queryset base para las relaciones de seguimiento."""
    return Follow.objects.select_related('from_profile', 'to_profile')


def follow_profile(from_profile: Profile, to_profile: Profile):
    """
    Crea una relación de seguimiento. Devuelve la instancia de Follow y un booleano 'created'.
    """
    if from_profile == to_profile:
        raise ValueError("Un perfil no puede seguirse a sí mismo.")
    
    follow, created = Follow.objects.get_or_create(
        from_profile=from_profile,
        to_profile=to_profile
    )
    return follow, created


def unfollow_profile(from_profile: Profile, to_profile: Profile):
    """
    Elimina una relación de seguimiento. Devuelve el número de objetos eliminados (1 o 0).
    """
    try:
        follow_instance = Follow.objects.get(
            from_profile=from_profile,
            to_profile=to_profile
        )
        follow_instance.delete()
        return 1
    except ObjectDoesNotExist:
        return 0