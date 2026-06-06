from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import Like, PostComment, EventComment, Bookmark, PendingInteraction


# ==================== LIKE SERVICES ====================

def get_like_queryset():
    return Like.objects.select_related('profile', 'post')


def get_likes_for_post(post):
    return Like.objects.filter(post=post).select_related('profile', 'post')


def get_likes_for_profile(profile):
    return Like.objects.filter(profile=profile).select_related('profile', 'post')


def create_like(profile, post):
    like, created = Like.objects.get_or_create(profile=profile, post=post)
    # Registrar interacción pendiente para procesamiento en batch
    if created:
        try:
            PendingInteraction.objects.create(
                profile=profile,
                content_id=str(post.id),
                content_type='post',
                action='like'
            )
        except Exception:
            # No queremos que falle la creación del like por un fallo secundario
            pass
        # Crear notificación para el autor del post
        try:
            # Importar localmente para evitar ciclos de import
            from django.contrib.contenttypes.models import ContentType
            from notifications.models import Notification

            recipient = getattr(post, 'author', None)
            # No crear notificación si el autor es el mismo que hizo el like
            if recipient and recipient != profile:
                Notification.objects.create(
                    recipient=recipient,
                    event_type=Notification.EventType.LIKE,
                    content_type=ContentType.objects.get_for_model(Like),
                    object_id=like.id,
                )
        except Exception:
            # No bloquear la creación del like por fallos en notificaciones
            pass
    return like, created


def delete_like(like):
    like.delete()


# ==================== POST COMMENT SERVICES ====================

def get_post_comments_queryset():
    return PostComment.objects.select_related('profile', 'post', 'parent', 'root').prefetch_related('replies')


def get_post_comments_for_post(post, include_deleted=False):
    queryset = PostComment.objects.filter(post=post).select_related('profile', 'post', 'parent', 'root')
    if not include_deleted:
        queryset = queryset.filter(is_deleted=False)
    return queryset.order_by('created_at')


def get_post_comment_thread(root_comment):
    """Obtiene todos los comentarios de un hilo (mismo root_id)"""
    return PostComment.objects.filter(root=root_comment, is_deleted=False).select_related(
        'profile', 'post', 'parent', 'root'
    ).order_by('created_at')


def get_root_post_comments_for_post(post):
    """Obtiene solo los comentarios raíz (primer nivel) de un post.

    Si un comentario raíz está eliminado, aún se incluye si tiene respuestas visibles.
    Esto evita que el recuento de comentarios sea mayor que los comentarios mostrados
    cuando solo quedan respuestas a un comentario raíz eliminado.
    """
    return PostComment.objects.filter(
        post=post,
        parent__isnull=True
    ).select_related('profile', 'post').prefetch_related('replies').filter(
        Q(is_deleted=False) | Q(replies__is_deleted=False)
    ).distinct()


def create_post_comment(profile, post, text, parent=None):
    """Crea un comentario en un post, asignando automáticamente root y depth"""
    with transaction.atomic():
        comment = PostComment.objects.create(
            profile=profile,
            post=post,
            text=text,
            parent=parent
        )
        # Crear notificación para el autor del post (si no es el mismo que comenta)
        try:
            from django.contrib.contenttypes.models import ContentType
            from notifications.models import Notification

            recipient = getattr(post, 'author', None)
            if recipient and recipient != profile:
                Notification.objects.create(
                    recipient=recipient,
                    event_type=Notification.EventType.COMMENT,
                    content_type=ContentType.objects.get_for_model(PostComment),
                    object_id=comment.id,
                )
        except Exception:
            pass

        return comment


def update_post_comment(comment, text):
    """Actualiza el texto de un comentario en post"""
    comment.text = text
    comment.save()
    return comment


def delete_post_comment(comment, soft_delete=True):
    """Borra un comentario en post (lógico por defecto, físico si soft_delete=False)"""
    if soft_delete:
        comment.is_deleted = True
        comment.save()
    else:
        comment.delete()


# ==================== EVENT COMMENT SERVICES ====================

def get_event_comments_queryset():
    return EventComment.objects.select_related('profile', 'event', 'parent', 'root').prefetch_related('replies')


def get_event_comments_for_event(event, include_deleted=False):
    queryset = EventComment.objects.filter(event=event).select_related('profile', 'event', 'parent', 'root')
    if not include_deleted:
        queryset = queryset.filter(is_deleted=False)
    return queryset.order_by('created_at')


def get_event_comment_thread(root_comment):
    """Obtiene todos los comentarios de un hilo (mismo root_id)"""
    return EventComment.objects.filter(root=root_comment, is_deleted=False).select_related(
        'profile', 'event', 'parent', 'root'
    ).order_by('created_at')


def get_root_event_comments_for_event(event):
    """Obtiene solo los comentarios raíz (primer nivel) de un evento.

    Si un comentario raíz está eliminado, aún se incluye si tiene respuestas visibles.
    Esto evita que el recuento de comentarios sea mayor que los comentarios mostrados
    cuando solo quedan respuestas a un comentario raíz eliminado.
    """
    return EventComment.objects.filter(
        event=event,
        parent__isnull=True
    ).select_related('profile', 'event').prefetch_related('replies').filter(
        Q(is_deleted=False) | Q(replies__is_deleted=False)
    ).distinct()


def create_event_comment(profile, event, text, parent=None):
    """Crea un comentario en un evento, asignando automáticamente root y depth"""
    with transaction.atomic():
        comment = EventComment.objects.create(
            profile=profile,
            event=event,
            text=text,
            parent=parent
        )
        # Crear notificación para el creador del evento (si no es el mismo que comenta)
        try:
            from django.contrib.contenttypes.models import ContentType
            from notifications.models import Notification

            recipient = getattr(event, 'creator', None)
            if recipient and recipient != profile:
                Notification.objects.create(
                    recipient=recipient,
                    event_type=Notification.EventType.COMMENT,
                    content_type=ContentType.objects.get_for_model(EventComment),
                    object_id=comment.id,
                )
        except Exception:
            pass

        return comment


def update_event_comment(comment, text):
    """Actualiza el texto de un comentario en evento"""
    comment.text = text
    comment.save()
    return comment


def delete_event_comment(comment, soft_delete=True):
    """Borra un comentario en evento (lógico por defecto, físico si soft_delete=False)"""
    if soft_delete:
        comment.is_deleted = True
        comment.save()
    else:
        comment.delete()


# ==================== BOOKMARK SERVICES ====================

def get_bookmark_queryset():
    return Bookmark.objects.select_related('profile', 'event')


def get_bookmarks_for_event(event):
    return Bookmark.objects.filter(event=event).select_related('profile', 'event')


def get_bookmarks_for_profile(profile):
    return Bookmark.objects.filter(profile=profile).select_related('profile', 'event')


def create_bookmark(profile, event):
    return Bookmark.objects.get_or_create(profile=profile, event=event)


def delete_bookmark(bookmark):
    bookmark.delete()
