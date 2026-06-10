import uuid

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    DIRECT = 'direct'
    GROUP = 'group'
    TYPE_CHOICES = [
        (DIRECT, 'Direct'),
        (GROUP, 'Group'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=DIRECT)
    name = models.CharField(max_length=128, blank=True)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='Participant',
        related_name='conversations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name or f'{self.type} ({self.id})'


class Participant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='participant_set',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_participations',
    )
    last_read_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('conversation', 'user')

    def __str__(self):
        return f'{self.user_id} in {self.conversation_id}'


class Message(models.Model):
    TEXT = 'text'
    IMAGE = 'image'
    FILE = 'file'
    TYPE_CHOICES = [
        (TEXT, 'Text'),
        (IMAGE, 'Image'),
        (FILE, 'File'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages',
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TEXT)
    content = models.TextField(blank=True)
    media_url = models.URLField(blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.type} message in {self.conversation_id}'
