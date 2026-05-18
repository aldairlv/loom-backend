import uuid
from django.db import models
from django.utils import timezone


class BaseComment(models.Model):
    """
    Clase abstracta que contiene toda la lógica de hilos.
    No crea tabla en la base de datos.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    profile = models.ForeignKey(
        'profiles.Profile',
        on_delete=models.CASCADE,
        related_name='%(class)s_comments'  # Crea un related_name único para cada subclase
    )
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies'
    )
    root = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='thread_comments'
    )
    depth = models.PositiveIntegerField(default=0, db_index=True)
    text = models.TextField(max_length=1000)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True  # ¡ESTO ES LO MÁS IMPORTANTE!
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['created_at']),
        ]

    def save(self, *args, **kwargs):
        # La lógica de árbol funciona igual para cualquier heredero
        if self.parent:
            self.root = self.parent.root if self.parent.root else self.parent
            self.depth = self.parent.depth + 1
        else:
            self.root = None
            self.depth = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Comentario de {self.profile.display_name}"


class PostComment(BaseComment):
    """
    Comentarios en posts.
    """
    post = models.ForeignKey(
        'posts.Post', on_delete=models.CASCADE, related_name='comments'
    )

    class Meta:
        indexes = [
            models.Index(fields=['post', 'created_at']),
        ]

    def __str__(self):
        return f"Comentario de {self.profile.display_name} en post {self.post.id}"


class EventComment(BaseComment):
    """
    Comentarios en eventos.
    """
    event = models.ForeignKey(
        'events.Event', on_delete=models.CASCADE, related_name='comments'
    )

    class Meta:
        indexes = [
            models.Index(fields=['event', 'created_at']),
        ]

    def __str__(self):
        return f"Comentario de {self.profile.display_name} en evento {self.event.title}"


class Like(models.Model):
    """
    Representa un 'like' de un perfil a una publicación.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    profile = models.ForeignKey(
        'profiles.Profile',
        on_delete=models.CASCADE,
        related_name='likes'
    )
    post = models.ForeignKey(
        'posts.Post',
        on_delete=models.CASCADE,
        related_name='likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Un perfil solo puede dar 'like' una vez a una publicación.
        unique_together = ('profile', 'post')
        ordering = ['-created_at']


class Bookmark(models.Model):
    """
    Representa un 'bookmark' de un perfil a un evento.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    profile = models.ForeignKey(
        'profiles.Profile',
        on_delete=models.CASCADE,
        related_name='bookmarks'
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='bookmarks'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Un perfil solo puede bookmark un evento una vez.
        unique_together = ('profile', 'event')
        ordering = ['-created_at']