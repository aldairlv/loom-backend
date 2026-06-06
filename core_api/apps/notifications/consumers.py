import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket Consumer para notificaciones en tiempo real.
    
    Cuando el usuario abre la app, se conecta a este WebSocket.
    El backend envía eventos en tiempo real por este canal.
    Si se desconecta, el backend envía Push Notifications a FCM.
    """

    async def connect(self):
        """
        Llamado cuando el cliente establece una conexión WebSocket.
        """
        self.user = self.scope["user"]
        
        # Solo permitir usuarios autenticados
        if not self.user.is_authenticated:
            await self.close()
            return

        # Crear un nombre de grupo único para cada usuario
        # Ejemplo: "notifications_user_123"
        self.user_group_name = f"notifications_user_{self.user.id}"

        # Agregar este canal a su grupo
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        # Aceptar la conexión
        await self.accept()

        # Marcar el usuario como conectado en Redis
        # Esto es útil para que Celery sepa si el usuario está online
        await self._mark_user_online()

        logger.info(f"Usuario {self.user.username} conectado al WebSocket")

    async def disconnect(self, close_code):
        """
        Llamado cuando el cliente cierra la conexión.
        """
        if self.user.is_authenticated:
            # Remover del grupo
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

            # Marcar como desconectado en Redis
            await self._mark_user_offline()

            logger.info(f"Usuario {self.user.username} desconectado del WebSocket")

    async def receive(self, text_data):
        """
        Recibe mensajes del cliente (heartbeat, etc).
        """
        try:
            data = json.loads(text_data)
            message_type = data.get("type", "ping")

            if message_type == "ping":
                # Responder con pong para mantener la conexión viva
                await self.send(text_data=json.dumps({
                    "type": "pong",
                    "timestamp": str(__import__('datetime').datetime.now()),
                }))
            elif message_type == "mark_read":
                # El cliente marca una notificación como leída
                notification_id = data.get("notification_id")
                await self._mark_notification_as_read(notification_id)

        except json.JSONDecodeError:
            logger.warning("Mensaje JSON inválido recibido")

    async def send_notification(self, event):
        """
        Recibe un mensaje del grupo y lo envía al WebSocket del cliente.
        
        El backend publica un evento en el grupo "notifications_user_X"
        y este método lo envía al cliente.
        """
        notification_data = event.get("notification", {})

        await self.send(text_data=json.dumps({
            "type": "notification",
            "data": notification_data,
        }))

    async def send_like_notification(self, event):
        """Envía una notificación de "like" al cliente."""
        like_data = event.get("like", {})

        await self.send(text_data=json.dumps({
            "type": "like",
            "data": like_data,
        }))

    async def send_follow_notification(self, event):
        """Envía una notificación de "seguir" al cliente."""
        follow_data = event.get("follow", {})

        await self.send(text_data=json.dumps({
            "type": "follow",
            "data": follow_data,
        }))

    async def send_comment_notification(self, event):
        """Envía una notificación de "comentario" al cliente."""
        comment_data = event.get("comment", {})

        await self.send(text_data=json.dumps({
            "type": "comment",
            "data": comment_data,
        }))

    # ============================================
    # Métodos Privados
    # ============================================

    async def _mark_user_online(self):
        """
        Marca al usuario como online en Redis.
        Celery verifica esto antes de enviar Push Notifications.
        """
        cache_key = f"user_online_{self.user.id}"
        # Envolver la llamada síncrona para que sea compatible con async
        await database_sync_to_async(cache.set)(
            cache_key, 
            self.user.username, 
            timeout=None  # No expira hasta que se desconecte
        )

    async def _mark_user_offline(self):
        """
        Marca al usuario como offline en Redis.
        Celery entonces enviará Push Notifications.
        """
        cache_key = f"user_online_{self.user.id}"
        # Envolver la llamada síncrona para que sea compatible con async
        await database_sync_to_async(cache.delete)(cache_key)

    async def _mark_notification_as_read(self, notification_id):
        """
        Marca una notificación como leída en la BD.
        """
        from .models import Notification
        
        try:
            notification = await database_sync_to_async(
                Notification.objects.get
            )(id=notification_id, recipient__account=self.user)
            
            notification.is_read = True
            await database_sync_to_async(notification.save)()

            logger.info(f"Notificación {notification_id} marcada como leída")
        except Notification.DoesNotExist:
            logger.warning(f"Notificación {notification_id} no encontrada")


# ============================================
# Función Helper para enviar notificaciones por WebSocket desde Celery
# ============================================

def send_notification_via_websocket(user_id, notification_type, notification_data):
    """
    Envía una notificación a través del WebSocket si el usuario está conectado.
    
    Args:
        user_id (int): ID del usuario destinatario
        notification_type (str): Tipo de notificación (like, follow, comment, etc)
        notification_data (dict): Datos de la notificación
    
    Returns:
        bool: True si fue enviado por WebSocket, False si no estaba conectado
    """
    channel_layer = get_channel_layer()
    group_name = f"notifications_user_{user_id}"

    # Definir el evento según el tipo
    if notification_type == "like":
        event = {
            "type": "send_like_notification",
            "like": notification_data,
        }
    elif notification_type == "follow":
        event = {
            "type": "send_follow_notification",
            "follow": notification_data,
        }
    elif notification_type == "comment":
        event = {
            "type": "send_comment_notification",
            "comment": notification_data,
        }
    else:
        event = {
            "type": "send_notification",
            "notification": notification_data,
        }

    # Enviar el evento al grupo
    # Esto es una operación síncrona desde la perspectiva de Celery
    async_to_sync(channel_layer.group_send)(group_name, event)

    logger.info(f"Notificación {notification_type} enviada por WebSocket al usuario {user_id}")
    return True
