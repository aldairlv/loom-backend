import uuid
from django.db import models
from django.conf import settings
from django.templatetags.static import static # Keep this for avatar/banner
from django.contrib.gis.db import models as gis_models
from posts.models import Tag


class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField( # This is now a true OneToOne relationship
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='profile' # Accedes así: user.profile
    )
    display_name = models.CharField(max_length=100)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    banner = models.ImageField(upload_to='banners/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    timezone = models.CharField(max_length=64, default='UTC')
    
    last_posted_at = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora del último post creado por este perfil.")
    is_default = models.BooleanField(default=False)
    
    # Campo para la última localización conocida del usuario.
    # srid=4326 es el sistema de coordenadas estándar para Lat/Lon (WGS84)
    location = gis_models.PointField(
        srid=4326,
        spatial_index=True,
        null=True,
        blank=True,
        help_text="Última localización conocida del perfil en formato (Longitud, Latitud) usando WGS84."
    )
    
    can_be_followed = models.BooleanField(default=True)
    
    # --- CAMPO AÑADIDO ---
    followed_tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='followers',
        help_text="Tags que este perfil sigue."
    )
    def __str__(self):
        return f"{self.display_name} ({self.user.username})"

    @property
    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        # Esta ruta apunta a tu carpeta static/images/
        return static('images/default_avatar.png')

    @property
    def get_banner_url(self):
        if self.banner and hasattr(self.banner, 'url'):
            return self.banner.url
        return static('images/default_banner.png')
    
    def get_friends_queryset(self):
        """Devuelve el QuerySet ejecutable de los perfiles que son amigos mutuos"""
        return self.following.filter(following=self)