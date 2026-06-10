from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from events.models import Event
from posts.models import Post
from profiles.models import Profile

from .tasks import index_event_task, index_post_task, index_user_task

User = get_user_model()


def _enqueue(task, object_id):
    transaction.on_commit(lambda: task.apply_async(args=[object_id], ignore_result=True))


@receiver(post_save, sender=Post)
def on_post_save(sender, instance, **kwargs):
    _enqueue(index_post_task, instance.id)


@receiver(post_delete, sender=Post)
def on_post_delete(sender, instance, **kwargs):
    _enqueue(index_post_task, instance.id)


@receiver(post_save, sender=Event)
def on_event_save(sender, instance, **kwargs):
    _enqueue(index_event_task, instance.id)


@receiver(post_delete, sender=Event)
def on_event_delete(sender, instance, **kwargs):
    _enqueue(index_event_task, instance.id)


@receiver(post_save, sender=Profile)
def on_profile_save(sender, instance, **kwargs):
    _enqueue(index_user_task, instance.id)


@receiver(post_save, sender=User)
def on_user_save(sender, instance, created, **kwargs):
    if created:
        return
    profile = Profile.objects.filter(user=instance).only('id').first()
    if profile:
        _enqueue(index_user_task, profile.id)
