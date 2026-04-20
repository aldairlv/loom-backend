from django.db import models
from django.core.validators import MaxLengthValidator
from blogs.models import Blog

class ContentBlockType(models.TextChoices):
    TEXT = 'text', 'Text'
    IMAGE = 'image', 'Image'
    VIDEO = 'video', 'Video'
    AUDIO = 'audio', 'Audio'

class Post(models.Model):
    id = models.BigIntegerField(
        primary_key=True,
    )
    blog = models.ForeignKey(
        Blog,
        on_delete=models.CASCADE,
        related_name='posts',
    )
    timestamp = models.BigIntegerField()
    layout = models.JSONField(
        default=list,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
    likes_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Likes"
    )
    reposts_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Reposts"
    )
    comments_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Comments"
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['blog', '-timestamp']),
        ]

    def __str__(self):
        return f"Post {self.id} by {self.blog}"
    
    @property
    def notes_count(self):
        return self.likes_count + self.reposts_count + self.comments_count

class ContentBlock(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='content_blocks',
    )
    
    type = models.CharField(
        max_length=10,
        choices=ContentBlockType.choices,
    )
    
    order = models.PositiveIntegerField(
        default=0,
    )

    class Meta:
        ordering = ['post', 'order']
        indexes = [
            models.Index(fields=['post', 'order']),
        ]

    def __str__(self):
        return f"{self.type} block in Post {self.post_id}"

class TextBlock(ContentBlock):
    text = models.TextField()
    
    class Meta:
        verbose_name = "Text Block"
        verbose_name_plural = "Text Blocks"

    def __str__(self):
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"Text: {preview}"

class ImageBlock(ContentBlock):
    media = models.JSONField(
    )