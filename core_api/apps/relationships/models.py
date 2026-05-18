import uuid
from django.db import models
from profiles.models import Profile

# Create your models here.
class Follow(models.Model):
    """Tabla intermedia para gestionar los follows"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # El que realiza la acción de seguir
    from_profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='following_relationships'
    )

    # El que es seguido
    to_profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='follower_relationships'
    )

    created_at = models.DateTimeField(auto_now_add=True) # ¿Cuándo empezó a seguirle?

    class Meta:
        # Evita que un usuario siga al mismo perfil más de una vez
        unique_together = ('from_profile', 'to_profile')

    def __str__(self):
        return f"{self.from_profile.display_name} sigue a {self.to_profile.display_name}"