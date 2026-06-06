import json
import logging
import uuid
from datetime import date, datetime
from decimal import Decimal
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

USER_ONLINE_CACHE_TIMEOUT = 86400  # 24h; se renueva con cada ping


def make_json_safe(value):
    """Convierte UUID, datetime, FileField, etc. a tipos serializables en JSON/msgpack."""
    if isinstance(value, dict):
        return {key: make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [make_json_safe(item) for item in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, 'url'):
        return value.url
    return value


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
        print(f"\n--- [NotificationConsumer] Iniciando método connect() ---")
        logger.info("[NotificationConsumer] Se ha iniciado una nueva solicitud de conexión WebSocket.")

        self.user = self.scope["user"]
        print(f"--- [NotificationConsumer] Usuario extraído del scope: ID={getattr(self.user, 'id', 'N/A')}, Username={getattr(self.user, 'username', 'Anonymous')} ---")
        logger.info(f"[NotificationConsumer] Usuario en scope: {self.user}")
        
        # Solo permitir usuarios autenticados
        print(f"--- [NotificationConsumer] Verificando si el usuario está autenticado... ---")
        if not self.user.is_authenticated:
            print(f"--- [NotificationConsumer] Usuario NO autenticado. Cerrando conexión. ---")
            logger.warning(f"[NotificationConsumer] Conexión rechazada para usuario no autenticado.")
            await self.close()
            return

        print(f"--- [NotificationConsumer] Usuario AUTENTICADO. Procediendo con la conexión. ---")
        # Crear un nombre de grupo único para cada usuario
        # Ejemplo: "notifications_user_123"
        self.user_group_name = f"notifications_user_{self.user.id}"
        print(f"--- [NotificationConsumer] Nombre de grupo generado: {self.user_group_name} ---")
        logger.info(f"[NotificationConsumer] El usuario {self.user.username} se unirá al grupo {self.user_group_name}.")

        # Agregar este canal a su grupo
        print(f"--- [NotificationConsumer] Añadiendo canal '{self.channel_name}' al grupo... ---")
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        # Aceptar la conexión
        print(f"--- [NotificationConsumer] Aceptando la conexión WebSocket. ---")
        await self.accept()
        print(f"--- [NotificationConsumer] Conexión ACEPTADA. ---")

        # Marcar el usuario como conectado en Redis
        # Esto es útil para que Celery sepa si el usuario está online
        print(f"--- [NotificationConsumer] Marcando al usuario como ONLINE en Redis... ---")
        await self._mark_user_online()

        print(f"--- [NotificationConsumer] ✅ Conexión completada para el usuario {self.user.username} (ID: {self.user.id}) ---")
        logger.info(f"[NotificationConsumer] Usuario {self.user.username} (ID: {self.user.id}) conectado y suscrito al canal.")

    async def disconnect(self, close_code):
        """
        Llamado cuando el cliente cierra la conexión.
        """
        print(f"\n--- [NotificationConsumer] Iniciando método disconnect() con close_code: {close_code} ---")
        logger.info(f"[NotificationConsumer] Usuario {getattr(self.user, 'username', 'N/A')} se está desconectando (código: {close_code}).")
        if self.user.is_authenticated:
            # Remover del grupo
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )

            # Marcar como desconectado en Redis
            await self._mark_user_offline()

            print(f"--- [NotificationConsumer] 🔴 Usuario {self.user.username} desconectado. ---")
            logger.info(f"[NotificationConsumer] Usuario {self.user.username} desconectado y desuscrito del canal.")

    async def receive(self, text_data):
        """
        Recibe mensajes del cliente (heartbeat, etc).
        """
        print(f"\n--- [NotificationConsumer] Recibido mensaje del cliente: {text_data} ---")
        logger.info(f"[NotificationConsumer] Mensaje recibido de {self.user.username}: {text_data}")
        try:
            data = json.loads(text_data)
            message_type = data.get("type", "ping")

            print(f"--- [NotificationConsumer] Mensaje parseado. Tipo: '{message_type}' ---")
            logger.debug(f"[NotificationConsumer] Tipo de mensaje: {message_type}")

            if message_type == "ping":
                await self._mark_user_online()
                await self.send(text_data=json.dumps({
                    "type": "pong",
                    "timestamp": str(__import__('datetime').datetime.now()),
                }))
            elif message_type == "mark_read":
                # El cliente marca una notificación como leída
                notification_id = data.get("notification_id")
                await self._mark_notification_as_read(notification_id)

        except json.JSONDecodeError:
            print(f"--- [NotificationConsumer] ERROR: Mensaje JSON inválido. ---")
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
            "data": make_json_safe(notification_data),
        }))

    async def send_like_notification(self, event):
        """Envía una notificación de "like" al cliente."""
        like_data = event.get("like", {})

        await self.send(text_data=json.dumps({
            "type": "like",
            "data": make_json_safe(like_data),
        }))

    async def send_follow_notification(self, event):
        """Envía una notificación de "seguir" al cliente."""
        follow_data = event.get("follow", {})

        await self.send(text_data=json.dumps({
            "type": "follow",
            "data": make_json_safe(follow_data),
        }))

    async def send_comment_notification(self, event):
        """Envía una notificación de "comentario" al cliente."""
        comment_data = event.get("comment", {})

        await self.send(text_data=json.dumps({
            "type": "comment",
            "data": make_json_safe(comment_data),
        }))

    # ============================================
    # Métodos Privados
    # ============================================

    async def _mark_user_online(self):
        """
        Marca al usuario como online en Redis.
        Celery verifica esto antes de enviar Push Notifications.
        """
        print(f"--- [NotificationConsumer._mark_user_online] Marcando usuario {self.user.id} como online. ---")
        cache_key = f"user_online_{self.user.id}"
        print(f"--- [NotificationConsumer._mark_user_online] Clave de cache: '{cache_key}' ---")
        # Envolver la llamada síncrona para que sea compatible con async
        await database_sync_to_async(cache.set)(
            cache_key,
            self.user.username,
            timeout=USER_ONLINE_CACHE_TIMEOUT,
        )
        logger.info(f"[NotificationConsumer] Usuario {self.user.id} marcado como ONLINE en Redis (key: {cache_key}).")

    async def _mark_user_offline(self):
        """
        Marca al usuario como offline en Redis.
        Celery entonces enviará Push Notifications.
        """
        print(f"--- [NotificationConsumer._mark_user_offline] Marcando usuario {self.user.id} como offline. ---")
        cache_key = f"user_online_{self.user.id}"
        print(f"--- [NotificationConsumer._mark_user_offline] Eliminando clave de cache: '{cache_key}' ---")
        # Envolver la llamada síncrona para que sea compatible con async
        await database_sync_to_async(cache.delete)(cache_key)
        logger.info(f"[NotificationConsumer] Usuario {self.user.id} marcado como OFFLINE en Redis (key: {cache_key} eliminada).")

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
    safe_data = make_json_safe(notification_data)

    # Definir el evento según el tipo
    if notification_type == "like":
        event = {
            "type": "send_like_notification",
            "like": safe_data,
        }
    elif notification_type == "follow":
        event = {
            "type": "send_follow_notification",
            "follow": safe_data,
        }
    elif notification_type == "comment":
        event = {
            "type": "send_comment_notification",
            "comment": safe_data,
        }
    else:
        event = {
            "type": "send_notification",
            "notification": safe_data,
        }

    # Enviar el evento al grupo
    # Esto es una operación síncrona desde la perspectiva de Celery
    async_to_sync(channel_layer.group_send)(group_name, event)

    logger.info(f"Notificación {notification_type} enviada por WebSocket al usuario {user_id}")
    return True
