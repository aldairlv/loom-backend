"""
PASOS DE INTEGRACIÓN EN INTERACTIONS Y RELATIONSHIPS

Este archivo te guía paso a paso para integrar las notificaciones en tus aplicaciones
de Likes, Follows y Comments.
"""

# ================================================================
# PASO 1: Actualizar interactions/tasks.py
# ================================================================

# Agrega esto en interactions/tasks.py

from celery import shared_task
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_interaction_notification(self, interaction_type, actor_id, recipient_id, 
                                   post_id=None, comment_id=None):
    """
    Tarea unificada para enviar notificaciones de interacciones.
    
    Args:
        interaction_type: 'like', 'comment'
        actor_id: Usuario que interactuó
        recipient_id: Usuario que recibe la notificación
        post_id: ID del post (para likes y comments)
        comment_id: ID del comentario (para comments)
    """
    from notifications.services import NotificationService
    
    try:
        actor = User.objects.get(id=actor_id)
        recipient = User.objects.get(id=recipient_id)
        
        if actor_id == recipient_id:
            return {'status': 'skipped', 'reason': 'self_interaction'}
        
        # Preparar datos según tipo de interacción
        notification_data = {
            'actor_id': actor_id,
            'actor_name': actor.get_full_name() or actor.username,
            'actor_avatar': getattr(actor.profile, 'avatar', None),
        }
        
        if interaction_type == 'like' and post_id:
            notification_data['post_id'] = str(post_id)
            
        if interaction_type == 'comment' and post_id and comment_id:
            notification_data['post_id'] = str(post_id)
            notification_data['comment_id'] = str(comment_id)
        
        # Enviar notificación (WebSocket o FCM)
        result = NotificationService.send_notification(
            user_id=recipient_id,
            notification_type=interaction_type,
            notification_data=notification_data,
        )
        
        return result
        
    except User.DoesNotExist:
        logger.error(f"User not found: actor={actor_id} or recipient={recipient_id}")
        return {'status': 'error', 'reason': 'user_not_found'}
    except Exception as e:
        logger.error(f"Error in send_interaction_notification: {str(e)}")
        raise self.retry(exc=e)


# ================================================================
# PASO 2: Actualizar interactions/views.py o serializers.py
# ================================================================

# En la vista que crea un Like:

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Like
from .tasks import send_interaction_notification
from posts.models import Post


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_like_view(request):
    """
    Cuando un usuario da like a un post.
    """
    post_id = request.data.get('post_id')
    user = request.user
    
    try:
        post = Post.objects.get(id=post_id)
        like, created = Like.objects.get_or_create(
            profile=user.profile,
            post=post
        )
        
        if created:
            # Disparar notificación en Celery
            send_interaction_notification.delay(
                interaction_type='like',
                actor_id=user.id,
                recipient_id=post.author.id,  # Ajusta según tu modelo
                post_id=str(post.id)
            )
        
        return Response({
            'status': 'success',
            'like_id': str(like.id),
            'created': created
        })
        
    except Post.DoesNotExist:
        return Response({
            'error': 'Post not found'
        }, status=404)


# ================================================================
# PASO 3: Actualizar relationships/tasks.py
# ================================================================

# Agrega esto en relationships/tasks.py

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_new_follow(self, follower_id, following_id):
    """
    Notifica cuando un usuario sigue a otro.
    """
    from notifications.services import NotificationService
    
    try:
        follower = User.objects.get(id=follower_id)
        
        if follower_id == following_id:
            return {'status': 'skipped'}
        
        notification_data = {
            'actor_id': follower_id,
            'actor_name': follower.get_full_name() or follower.username,
            'actor_avatar': getattr(follower.profile, 'avatar', None),
        }
        
        result = NotificationService.send_notification(
            user_id=following_id,
            notification_type='follow',
            notification_data=notification_data,
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in notify_new_follow: {str(e)}")
        raise self.retry(exc=e)


# ================================================================
# PASO 4: Actualizar relationships/views.py
# ================================================================

# En la vista que crea un Follow:

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_follow_view(request):
    """
    Cuando un usuario sigue a otro.
    """
    following_id = request.data.get('user_id')
    user = request.user
    
    try:
        following_user = User.objects.get(id=following_id)
        
        relationship, created = Relationship.objects.get_or_create(
            follower=user,
            following=following_user
        )
        
        if created:
            from relationships.tasks import notify_new_follow
            notify_new_follow.delay(
                follower_id=user.id,
                following_id=following_id
            )
        
        return Response({
            'status': 'success',
            'following': created
        })
        
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=404)


# ================================================================
# PASO 5: Actualizar posts/views.py (para comentarios)
# ================================================================

# En la vista que crea un comentario:

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_comment_view(request):
    """
    Cuando un usuario comenta en un post.
    """
    post_id = request.data.get('post_id')
    content = request.data.get('content')
    user = request.user
    
    try:
        post = Post.objects.get(id=post_id)
        
        comment = PostComment.objects.create(
            post=post,
            author=user.profile,
            content=content
        )
        
        # Solo notificar si no es el dueño del post
        if user.id != post.author.id:
            from interactions.tasks import send_interaction_notification
            send_interaction_notification.delay(
                interaction_type='comment',
                actor_id=user.id,
                recipient_id=post.author.id,
                post_id=str(post.id),
                comment_id=str(comment.id)
            )
        
        return Response({
            'status': 'success',
            'comment_id': str(comment.id)
        })
        
    except Post.DoesNotExist:
        return Response({
            'error': 'Post not found'
        }, status=404)


# ================================================================
# PASO 6: Verificar que task.py existe en interactions
# ================================================================

# Si interactions/tasks.py no existe, créalo:
# interactions/tasks.py ya debe tener:
# - process_pending_interactions (verifica en CELERY_BEAT_SCHEDULE)


# ================================================================
# PASO 7: Crear migrations
# ================================================================

# En terminal, ejecuta:
# python manage.py makemigrations
# python manage.py migrate

# Nota: El modelo UserDevice ya está migrado, así que no hay nuevas migraciones


# ================================================================
# PASO 8: Prueba Local
# ================================================================

"""
Terminal 1: Django
    python manage.py runserver

Terminal 2: Celery Worker
    celery -A loom worker -l info --without-gossip --without-mingle --without-heartbeat

Terminal 3: Celery Beat (Scheduler)
    celery -A loom beat -l info

Terminal 4: Redis (si no usas Docker)
    redis-server

Terminal 5: Websocket Test (opcional)
    wscat -c "ws://localhost:8000/ws/notifications/?token=YOUR_JWT"


Luego en otra terminal (Django shell):
    python manage.py shell
    
    from notifications.tasks import send_like_notification
    send_like_notification.delay(actor_id=1, recipient_id=2, post_id="550e8400-e29b-41d4-a716-446655440000")
    
    # Ver en WebSocket terminal la notificación en tiempo real
"""


# ================================================================
# PASO 9: Estructura de directorios recomendada
# ================================================================

"""
core_api/
├── apps/
│   ├── interactions/
│   │   ├── tasks.py         ← Contiene send_interaction_notification
│   │   ├── views.py         ← Llama send_interaction_notification.delay()
│   │   └── ...
│   ├── relationships/
│   │   ├── tasks.py         ← Contiene notify_new_follow
│   │   ├── views.py         ← Llama notify_new_follow.delay()
│   │   └── ...
│   ├── posts/
│   │   ├── views.py         ← Llama send_interaction_notification.delay()
│   │   └── ...
│   ├── notifications/
│   │   ├── consumers.py      ← WebSocket Consumer (NUEVO)
│   │   ├── routing.py        ← WebSocket Routing (NUEVO)
│   │   ├── services.py       ← Lógica de notificaciones
│   │   ├── tasks.py          ← Tareas de Celery
│   │   ├── models.py         ← UserDevice, Notification
│   │   ├── views.py          ← RegisterDeviceView
│   │   ├── urls.py           ← Endpoints REST
│   │   ├── serializers.py    ← Serializadores
│   │   └── ...
│   └── ...
├── loom/
│   ├── asgi.py               ← ACTUALIZADO para WebSocket
│   ├── settings.py           ← ACTUALIZADO para Channels + Firebase
│   ├── celery.py             ← Sin cambios
│   ├── urls.py               ← Sin cambios
│   └── ...
├── requirements.txt          ← firebase-admin, channels-redis
└── WEBSOCKET_PUSHNOTIFICATIONS_README.md
"""
