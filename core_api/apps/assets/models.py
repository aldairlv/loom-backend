import uuid

from django.db import models

# Create your models here.
class MediaType(models.TextChoices):
    IMAGE_JPEG = 'image/jpeg', 'JPEG Image'
    IMAGE_PNG = 'image/png', 'PNG Image'
    VIDEO_MP4 = 'video/mp4', 'MP4 Video'
    VIDEO_WEBM = 'video/webm', 'WebM Video'
    AUDIO_MP3 = 'audio/mpeg', 'MP3 Audio'

# Models
class Media(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField()
    type = models.CharField(
        max_length=50, 
        choices=MediaType.choices
    )
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()