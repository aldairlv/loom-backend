import uuid

from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Notification(models.Model):
    class EventType(models.TextChoices):
        LIKE = 'LIKE', 'Like'
        COMMENT = 'COMMENT', 'Comment'
        FOLLOW = 'FOLLOW', 'Follow'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        'profiles.Profile',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    event_type = models.CharField(max_length=16, choices=EventType.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    target_object = GenericForeignKey('content_type', 'object_id')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f'Notification {self.id} for {self.recipient_id}'


class UserDevice(models.Model):
    DEVICE_TYPES = (
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='devices'
    )
    device_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="ID único del hardware"
    )
    registration_token = models.TextField(
        unique=True,
        help_text="Token de Firebase/APNS"
    )
    device_type = models.CharField(
        max_length=10,
        choices=DEVICE_TYPES,
        default='android'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Device'
        verbose_name_plural = 'User Devices'
        indexes = [
            models.Index(fields=['account', 'is_active']),
        ]

    def __str__(self):
        return f"{self.account.username} - {self.device_type} ({self.device_id[:8]})"
