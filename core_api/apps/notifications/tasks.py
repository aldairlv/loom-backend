import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from .models import Notification
from .services import NotificationService

logger = logging.getLogger(__name__)

User = get_user_model()


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # Reintentar en 60 segundos
    time_limit=300,  # 5 minutos max
)
def send_like_notification(self, actor_id, recipient_id, post_id):
    """
    Envía una notificación de "like" al usuario.
    
    Flujo:
    1. Registra la notificación en BD
    2. Verifica si el usuario está online (WebSocket)
    3. Si está online → Enviar por WebSocket
    4. Si está offline → Enviar Push Notification a FCM
    
    Args:
        actor_id (int): ID del usuario que dio el like
        recipient_id (int): ID del usuario que recibe la notificación
        post_id (str/UUID): ID del post que fue likeado
    """
    print(f"\n--- [WORKER] INICIO TAREA send_like_notification ---")
    logger.info(f"[WORKER] Iniciando tarea send_like_notification.")
    print(f"[WORKER] Parámetros recibidos: actor_id={actor_id}, recipient_id={recipient_id}, post_id={post_id}")
    logger.info(f"[WORKER] Parámetros: actor_id={actor_id}, recipient_id={recipient_id}, post_id={post_id}")
    try:
        print(f"[WORKER] Buscando actor (id={actor_id}) y recipient (id={recipient_id}) en la base de datos.")
        # Obtener los usuarios
        actor = User.objects.get(id=actor_id)
        recipient = User.objects.get(id=recipient_id)
        print(f"[WORKER] Usuarios encontrados: actor='{actor.username}', recipient='{recipient.username}'")

        # No enviar notificación si el usuario se da like a sí mismo
        print(f"[WORKER] IF-CHECK: Verificando si actor_id ({actor_id}) == recipient_id ({recipient_id})")
        if actor_id == recipient_id:
            print(f"[WORKER] Condición CUMPLIDA. El usuario se dio like a sí mismo. Finalizando tarea.")
            logger.info(f"Usuario {actor_id} se dio like a sí mismo - sin notificación")
            return

        print(f"[WORKER] Condición NO CUMPLIDA. Procediendo a registrar la notificación en la BD.")
        # Registrar la notificación en BD
        from posts.models import Post
        print(f"[WORKER] Buscando post con id={post_id}")
        post = Post.objects.get(id=post_id)
        content_type = ContentType.objects.get_for_model(Post)

        print(f"[WORKER] Ejecutando Notification.objects.get_or_create para el like.")
        notification, created = Notification.objects.get_or_create(
            recipient=recipient.profile,
            event_type=Notification.EventType.LIKE,
            content_type=content_type,
            object_id=post_id,
        )
        print(f"[WORKER] Resultado de get_or_create: Notificación {'creada' if created else 'ya existente'}. ID: {notification.id}")
        logger.info(f"[WORKER] Notificación de like (id={notification.id}) {'creada' if created else 'obtenida'} para recipient {recipient_id}.")

        # Preparar datos para la notificación
        print(f"[WORKER] Preparando el diccionario 'notification_data' para enviar al servicio.")
        notification_data = {
            'actor_id': str(actor_id),
            'actor_name': actor.profile.display_name if hasattr(actor, 'profile') and actor.profile.display_name else actor.username,
            'actor_avatar': actor.profile.avatar.url if hasattr(actor, 'profile') and actor.profile.avatar else None,
            'post_id': str(post_id),
            'post_title': post.title[:50] if hasattr(post, 'title') else 'Tu post',
            'notification_id': str(notification.id),
        }
        print(f"[WORKER] 'notification_data' preparado: {notification_data}")

        # Enviar la notificación (WebSocket o FCM)
        print(f"[WORKER] Llamando a NotificationService.send_notification con user_id={recipient_id}, type='like'")
        result = NotificationService.send_notification(
            user_id=recipient_id,
            notification_type='like',
            notification_data=notification_data,
        )

        print(f"[WORKER] Resultado del servicio de notificación: {result}")
        logger.info(
            f"Notificación de like enviada a {recipient.username} "
            f"por método: {result.get('method', 'unknown')}"
        )

        return result

    except User.DoesNotExist as e:
        print(f"[WORKER] ERROR: Usuario no encontrado. {str(e)}")
        logger.error(f"Usuario no encontrado: {str(e)}")
        return {'error': 'usuario_no_encontrado'}
    except Exception as e:
        print(f"[WORKER] ERROR INESPERADO en la tarea: {str(e)}. Reintentando...")
        logger.error(f"Error en send_like_notification: {str(e)}")
        # Reintentar en caso de error
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,
)
def send_follow_notification(self, actor_id, recipient_id):
    """
    Envía una notificación de "seguir" al usuario.
    
    Args:
        actor_id (int): ID del usuario que sigue
        recipient_id (int): ID del usuario que recibe la notificación
    """
    try:
        actor = User.objects.get(id=actor_id)
        recipient = User.objects.get(id=recipient_id)

        if actor_id == recipient_id:
            logger.info(f"Usuario {actor_id} se siguió a sí mismo - sin notificación")
            return

        # Registrar la notificación en BD
        from relationships.models import Relationship
        relationship = Relationship.objects.get(follower_id=actor_id, following_id=recipient_id)
        content_type = ContentType.objects.get_for_model(Relationship)

        notification, created = Notification.objects.get_or_create(
            recipient=recipient.profile,
            event_type=Notification.EventType.FOLLOW,
            content_type=content_type,
            object_id=relationship.id,
        )

        notification_data = {
            'actor_id': str(actor_id),
            'actor_name': actor.get_full_name() or actor.username,
            'actor_avatar': actor.profile.avatar.url if hasattr(actor, 'profile') and actor.profile.avatar else None,
            'notification_id': str(notification.id),
        }

        result = NotificationService.send_notification(
            user_id=recipient_id,
            notification_type='follow',
            notification_data=notification_data,
        )

        logger.info(
            f"Notificación de follow enviada a {recipient.username} "
            f"por método: {result.get('method', 'unknown')}"
        )

        return result

    except Exception as e:
        logger.error(f"Error en send_follow_notification: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,
)
def send_comment_notification(self, actor_id, recipient_id, post_id, comment_id):
    """
    Envía una notificación de "comentario" al usuario.
    
    Args:
        actor_id (int): ID del usuario que comenta
        recipient_id (int): ID del usuario que recibe la notificación
        post_id (str/UUID): ID del post
        comment_id (str/UUID): ID del comentario
    """
    try:
        actor = User.objects.get(id=actor_id)
        recipient = User.objects.get(id=recipient_id)

        if actor_id == recipient_id:
            logger.info(f"Usuario {actor_id} comentó su propio post - sin notificación")
            return

        # Obtener el comentario
        from posts.models import Comment
        comment = Comment.objects.get(id=comment_id)
        content_type = ContentType.objects.get_for_model(Comment)

        notification, created = Notification.objects.get_or_create(
            recipient=recipient.profile,
            event_type=Notification.EventType.COMMENT,
            content_type=content_type,
            object_id=comment_id,
        )

        notification_data = {
            'actor_id': str(actor_id),
            'actor_name': actor.get_full_name() or actor.username,
            'actor_avatar': actor.profile.avatar.url if hasattr(actor, 'profile') and actor.profile.avatar else None,
            'post_id': str(post_id),
            'comment_id': str(comment_id),
            'comment_body': comment.content[:100] if hasattr(comment, 'content') else 'Nuevo comentario',
            'notification_id': str(notification.id),
        }

        result = NotificationService.send_notification(
            user_id=recipient_id,
            notification_type='comment',
            notification_data=notification_data,
        )

        logger.info(
            f"Notificación de comentario enviada a {recipient.username} "
            f"por método: {result.get('method', 'unknown')}"
        )

        return result

    except Exception as e:
        logger.error(f"Error en send_comment_notification: {str(e)}")
        raise self.retry(exc=e)


@shared_task
def process_pending_interactions():
    """
    Tarea periódica (cada 5 minutos) para procesar interacciones pendientes.
    
    Útil si necesitas procesar en batch notificaciones que se acumularon.
    """
    logger.info("Procesando interacciones pendientes...")
    # Aquí puedes agregar lógica adicional si lo necesitas
    return {'status': 'completed'}


# ============================================
# Tareas para Gestión de Dispositivos
# ============================================

@shared_task
def cleanup_inactive_devices():
    """
    Tarea periódica para limpiar dispositivos inactivos.
    
    Puede ejecutarse diariamente para marcar dispositivos como inactivos
    si no han sido usados en X días.
    """
    from datetime import timedelta
    from django.utils import timezone
    from .models import UserDevice

    cutoff_date = timezone.now() - timedelta(days=30)

    inactive_devices = UserDevice.objects.filter(
        updated_at__lt=cutoff_date,
        is_active=True
    )

    count = inactive_devices.update(is_active=False)
    logger.info(f"Se desactivaron {count} dispositivos inactivos")

    return {'inactive_devices_count': count}


@shared_task
def validate_fcm_tokens():
    """
    Tarea para validar y limpiar tokens FCM inválidos.
    
    Puede ejecutarse periódicamente para marcar como inactivos
    los dispositivos cuyos tokens de Firebase han expirado.
    """
    logger.info("Validando tokens FCM...")
    # Esta tarea es más compleja y requiere interacción con Firebase
    # Por ahora, solo registramos que se ejecutó
    return {'status': 'validation_started'}
