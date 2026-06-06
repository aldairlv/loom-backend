import uuid
from django.db import connection, models
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

class PostStatus(models.TextChoices):
    DRAFT = 'draft', 'Borrador'
    PUBLISHED = 'published', 'Publicado'
    ARCHIVED = 'archived', 'Archivado'

class ContentType(models.TextChoices):
    TEXT = 'text', 'Text'
    IMAGE = 'image', 'Image'
    VIDEO = 'video', 'Video'
    AUDIO = 'audio', 'Audio'



class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True) # Ej: "art"
    
    # Si quieres meterle estilos o tipos (trending) aquí, puedes hacerlo
    # Pero si el estilo cambia dinámicamente, mejor manejarlo en el serializador.
    is_trending = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name
class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    author = models.ForeignKey(
        'profiles.Profile', 
        on_delete=models.CASCADE, 
        related_name='posts'
    )

    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='replies'
    )
    
    root = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='thread_posts'
    )
    
    status = models.CharField(
        max_length=20, 
        choices=PostStatus.choices, 
        default=PostStatus.PUBLISHED
    )
    tags = models.ManyToManyField(Tag, related_name='posts', blank=True)

    layout = models.JSONField(default=list, blank=True)
    show_trailing = models.BooleanField(default=True)
    trail_ids = ArrayField(models.UUIDField(), default=list, blank=True)
    
    is_deleted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True) # Nunca cambia
    updated_at = models.DateTimeField(auto_now=True)     # Cambia siempre que guardas
    published_at = models.DateTimeField(null=True, blank=True) # Solo cuando cambia a 'published'

    def _build_trail_ids(self):
        if not self.parent_id:
            return []

        if connection.vendor != 'postgresql':
            # Fallback a Python en entornos que no usen PostgreSQL.
            ancestors = []
            current = self.parent
            while current:
                ancestors.append(current)
                if not current.show_trailing:
                    break
                current = current.parent

            if self.root_id is not None:
                ancestors = [a for a in ancestors if a.id != self.root_id]

            return [post.id for post in reversed(ancestors)]

        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH RECURSIVE ancestors AS (
                    SELECT id, parent_id, show_trailing, 0 AS level
                    FROM posts_post
                    WHERE id = %s
                  UNION ALL
                    SELECT p.id, p.parent_id, p.show_trailing, a.level + 1
                    FROM posts_post p
                    JOIN ancestors a ON p.id = a.parent_id
                    WHERE a.show_trailing = TRUE
                )
                SELECT id
                FROM ancestors
                WHERE (%s IS NULL OR id != %s)
                ORDER BY level DESC
                """,
                [self.parent_id, self.root_id, self.root_id],
            )
            return [row[0] for row in cursor.fetchall()]

    def save(self, *args, **kwargs):
        # Lógica para la fecha de publicación
        if self.status == 'published' and self.published_at is None:
            self.published_at = timezone.now()

        # La lista de IDs del trail se guarda en el modelo al crear/actualizar el post.
        self.trail_ids = self._build_trail_ids() if self.parent_id else []
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Post de {self.author.display_name} ({self.id})"

    class Meta:
        ordering = ['-created_at']


class PostContent(models.Model):
    post = models.ForeignKey(Post, related_name='contents', on_delete=models.CASCADE)
    type = models.CharField(max_length=50, choices=ContentType.choices)
    order = models.PositiveIntegerField(default=0) # Para mantener el orden (ej: texto, foto, texto)
    
    # Datos opcionales (Solo uno de estos estará lleno según el 'type')
    text = models.TextField(blank=True, null=True)
    media = models.ForeignKey('assets.Media', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['order'] # Esto garantiza que siempre salgan en el orden correcto
