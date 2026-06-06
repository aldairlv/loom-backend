"""
INTEGRATION EXAMPLE: Cómo usar WebSockets + Push Notifications en tu código

Este archivo muestra ejemplos concretos de cómo integrar la arquitectura
híbrida WebSocket + Push Notifications en tus vistas y servicios.

==========================================
CASO 1: Cuando un usuario da "Like" a un post
==========================================
"""

# En interactions/views.py o interactions/serializers.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Like
from posts.models import Post
from notifications.tasks import send_like_notification


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_like(request, post_id):
    """
    Cuando un usuario da like a un post, disparamos una notificación.
    """
    user = request.user
    post = Post.objects.get(id=post_id)
    
    # Verificar si ya existe el like
    like, created = Like.objects.get_or_create(
        profile=user.profile,
        post=post
    )
    
    if created:
        # Disparar notificación en SEGUNDO PLANO con Celery
        # El usuario que dio like es "actor_id"
        # El dueño del post es "recipient_id"
        send_like_notification.delay(
            actor_id=user.id,
            recipient_id=post.author.id,  # Ajusta según tu modelo
            post_id=str(post.id)
        )
    
    return Response({
        'status': 'success',
        'like_id': str(like.id),
        'created': created
    })


"""
==========================================
CASO 2: Cuando un usuario comienza a seguir otro
==========================================
"""

from relationships.tasks import send_follow_notification


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_follow(request, user_id):
    """
    Cuando un usuario sigue a otro, disparamos una notificación.
    """
    user = request.user
    following = User.objects.get(id=user_id)
    
    relationship, created = Relationship.objects.get_or_create(
        follower=user,
        following=following
    )
    
    if created:
        send_follow_notification.delay(
            actor_id=user.id,
            recipient_id=user_id
        )
    
    return Response({
        'status': 'success',
        'following': created
    })


"""
==========================================
CASO 3: Cuando un usuario comenta
==========================================
"""

from posts.tasks import send_comment_notification


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_comment(request, post_id):
    """
    Cuando un usuario comenta en un post, notificamos al dueño del post.
    """
    user = request.user
    post = Post.objects.get(id=post_id)
    content = request.data.get('content')
    
    comment = PostComment.objects.create(
        post=post,
        author=user.profile,
        content=content
    )
    
    # Solo notificar si el comentario es del autor del post
    if user.id != post.author.id:
        send_comment_notification.delay(
            actor_id=user.id,
            recipient_id=post.author.id,
            post_id=str(post.id),
            comment_id=str(comment.id)
        )
    
    return Response({
        'status': 'success',
        'comment_id': str(comment.id)
    })


"""
==========================================
CASO 4: Cómo usar el servicio manualmente
==========================================
"""

from notifications.services import NotificationService
from notifications.consumers import send_notification_via_websocket

# Opción A: Usar el servicio (recomendado)
# Esto automáticamente verifica WebSocket y usa FCM como fallback
result = NotificationService.send_notification(
    user_id=recipient_id,
    notification_type='like',
    notification_data={
        'actor_id': actor_id,
        'actor_name': 'Juan Pérez',
        'post_id': str(post_id),
        'post_title': 'Mi primer post',
    }
)

# result['success'] = True/False
# result['method'] = 'websocket' / 'fcm'

# Opción B: Verificar manualmente si está online
if NotificationService.is_user_online(recipient_id):
    # Usuario está viendo la app - enviar por WebSocket
    send_notification_via_websocket(
        recipient_id,
        'like',
        {'actor_id': actor_id, ...}
    )
else:
    # Usuario no está viendo - enviar Push a FCM
    NotificationService.send_push_notification(
        recipient_id,
        fcm_payload={
            'title': 'Te dieron un like',
            'body': 'Tu post recibió un like',
            'data': {'action': 'open_post', 'post_id': str(post_id)}
        }
    )


"""
==========================================
CASO 5: Cliente en tiempo real (WebSocket)
==========================================
Código de ejemplo para el cliente mobile (Kotlin/Jetpack Compose):

// En tu Activity o Composable:

private fun connectWebSocket() {
    val token = getAuthToken()  // Tu token JWT
    val wsUrl = "wss://tu-dominio.com/ws/notifications/?token=$token"
    
    val client = OkHttpClient()
    val request = Request.Builder()
        .url(wsUrl)
        .addHeader("Authorization", "Bearer $token")
        .build()
    
    webSocket = client.newWebSocket(request, object : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            Log.d("WebSocket", "Conectado a notificaciones en tiempo real")
            // Enviar heartbeat cada 30 segundos
            sendPing()
        }
        
        override fun onMessage(webSocket: WebSocket, text: String) {
            val notification = JSONObject(text)
            val type = notification.getString("type")
            
            when (type) {
                "like" -> {
                    val data = notification.getJSONObject("data")
                    // Actualizar UI instantáneamente
                    updateLikeCount(data)
                }
                "pong" -> {
                    // Respuesta del servidor a nuestro ping
                }
            }
        }
        
        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            Log.d("WebSocket", "Desconectado de notificaciones")
        }
        
        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            Log.e("WebSocket", "Error: ${t.message}")
            reconnect()
        }
    })
}

private fun sendPing() {
    webSocket?.send(JSONObject().apply {
        put("type", "ping")
    }.toString())
}
"""


"""
==========================================
CASO 6: Registrar dispositivo FCM
==========================================
Endpoint: POST /api/v1/notifications/devices/

Request:
{
    "device_id": "ABC123XYZ",  // ID único del dispositivo
    "registration_token": "dXXXXXXXXXXXXXXXXXXX",  // Token de Firebase
    "device_type": "android",  // android, ios, web
    "is_active": true
}

Response:
{
    "message": "Device registrado y activo",
    "device": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "device_id": "ABC123XYZ",
        "registration_token": "dXXXXXXXXXXXXXXXXXXX",
        "device_type": "android",
        "is_active": true,
        "created_at": "2026-06-05T10:30:00Z",
        "updated_at": "2026-06-05T10:30:00Z"
    },
    "created": true
}

Desactivar dispositivo:
{
    "device_id": "ABC123XYZ",
    "is_active": false
}
"""
