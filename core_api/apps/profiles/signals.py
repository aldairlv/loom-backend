from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Profile
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Profile
# from .services import process_image

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_profile(sender, instance, created, **kwargs):
    if created:
        # Aquí garantizamos que el slug sea igual al username
        # y marcamos este perfil como el predeterminado
        Profile.objects.create(
            user=instance,
            display_name=instance.username
        )

"""
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def update_profile_slug(sender, instance, created, **kwargs):
    if not created:
        instance.profiles.filter(is_default=True).update(slug=instance.username)

@receiver(post_save, sender=Profile)
def handle_profile_images(sender, instance, **kwargs):
    # Procesar Avatar
    if instance.avatar:
        process_image(instance.avatar.path, size=(300, 300))
    
    # Procesar Banner
    if instance.banner:
        process_image(instance.banner.path, size=(1200, 400))
""" # This was likely the cause of the SyntaxError