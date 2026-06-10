from celery import shared_task

from events.models import Event, EventStatus
from posts.models import Post, PostStatus
from profiles.models import Profile

from .documents import EventDocument, PostDocument, UserDocument


def _delete_document(document_cls, instance):
    document_cls().delete(instance, ignore=404)


@shared_task(bind=True, max_retries=3, ignore_result=True)
def index_post_task(self, post_id):
    try:
        post = (
            Post.objects.select_related('author__user')
            .prefetch_related('contents__media', 'tags')
            .get(id=post_id)
        )
    except Post.DoesNotExist:
        return f'Post {post_id} no existe.'

    if post.is_deleted or post.status != PostStatus.PUBLISHED:
        _delete_document(PostDocument, post)
        return f'Post {post_id} eliminado del índice.'

    PostDocument().update(post)
    return f'Post {post_id} indexado.'


@shared_task(bind=True, max_retries=3, ignore_result=True)
def index_event_task(self, event_id):
    try:
        event = (
            Event.objects.select_related('creator__user', 'thumbnail')
            .prefetch_related('tags')
            .get(id=event_id)
        )
    except Event.DoesNotExist:
        return f'Event {event_id} no existe.'

    if (
        event.is_cancelled
        or not event.is_public
        or event.status != EventStatus.PUBLISHED
    ):
        _delete_document(EventDocument, event)
        return f'Event {event_id} eliminado del índice.'

    EventDocument().update(event)
    return f'Event {event_id} indexado.'


@shared_task(bind=True, max_retries=3, ignore_result=True)
def index_user_task(self, profile_id):
    try:
        profile = Profile.objects.select_related('user').get(id=profile_id)
    except Profile.DoesNotExist:
        return f'Profile {profile_id} no existe.'

    if not profile.user.is_active:
        _delete_document(UserDocument, profile)
        return f'Profile {profile_id} eliminado del índice.'

    UserDocument().update(profile)
    return f'Profile {profile_id} indexado.'
