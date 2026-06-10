import logging
from typing import List, Optional, Dict, Any
from django.core.cache import cache
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

User = get_user_model()


class NotificationService:
    """
    Servicio centralizado para enviar notificaciones.
    Maneja la lógica de decidir entre WebSocket y Push Notifications.
    """

    @staticmethod
    def is_user_online(user_id: int) -> bool:
        """
        Verifica si el usuario está conectado al WebSocket.
        
        Args:
            user_id (int): ID del usuario
            
        Returns:
            bool: True si está online, False si está offline
        """
        print(f"[NotificationService] Verificando si el usuario {user_id} está online...")
        logger.info(f"[NotificationService] Verificando estado online para user_id: {user_id}")
        # --- DEBUGGING: Listar claves en caché ---
        try:
            # Esto funciona con el backend de redis, pero puede fallar con otros.
            all_keys = cache.keys('user_online_*')
            print(f"[NotificationService-DEBUG] Claves en caché ('user_online_*'): {all_keys}")
            logger.info(f"[NotificationService-DEBUG] Claves en caché ('user_online_*'): {all_keys}")
        except Exception as e:
            print(f"[NotificationService-DEBUG] No se pudieron listar las claves de la caché: {e}")
            logger.warning(f"[NotificationService-DEBUG] No se pudieron listar las claves de la caché: {e}")
        # --- FIN DEBUGGING ---
        cache_key = f"user_online_{user_id}"
        is_online = cache.get(cache_key) is not None
        print(f"[NotificationService] Usuario {user_id} está online: {is_online}")
        logger.info(f"[NotificationService] Resultado de is_user_online para {user_id}: {is_online}")
        return is_online

    @staticmethod
    def send_notification(
        user_id: int,
        notification_type: str,
        notification_data: Dict[str, Any],
        fcm_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Envía una notificación al usuario.
        
        Flujo:
        1. Si el usuario está online (WebSocket conectado) → Enviar por WebSocket
        2. Si está offline → Enviar Push Notification a FCM
        
        Args:
            user_id (int): ID del usuario destinatario
            notification_type (str): Tipo de notificación (like, follow, comment, etc)
            notification_data (dict): Datos de la notificación para WebSocket
            fcm_payload (dict): Payload para Firebase (si es None, se genera automáticamente)
            
        Returns:
            dict: {
                'success': bool,
                'method': 'websocket' | 'fcm' | 'none',
                'message': str,
                'fcm_response': dict (si aplica)
            }
        """
        print(f"\n--- INICIO send_notification para user_id: {user_id} ---")
        logger.info(f"Iniciando send_notification para user_id: {user_id}")
        print(f"Parámetros recibidos: user_id={user_id}, notification_type='{notification_type}', notification_data={notification_data}, fcm_payload={fcm_payload}")
        logger.info(f"Parámetros: user_id={user_id}, type={notification_type}, data={notification_data}")

        # Verificar si el usuario existe
        try:
            print(f"[send_notification] Buscando usuario con id: {user_id}")
            user = User.objects.get(id=user_id)
            print(f"[send_notification] Usuario encontrado: {user.username}")
            logger.info(f"Usuario {user_id} encontrado en la base de datos.")
        except User.DoesNotExist:
            print(f"[send_notification] ERROR: Usuario {user_id} no encontrado.")
            logger.error(f"Usuario {user_id} no encontrado al intentar enviar notificación.")
            return {
                'success': False,
                'method': 'none',
                'message': f'Usuario {user_id} no encontrado'
            }

        print(f"[send_notification] Preguntando si el usuario {user_id} está conectado al WebSocket...")
        # Estrategia A: Verificar si el usuario está online
        if NotificationService.is_user_online(user_id):
            print(f"[send_notification] IF-CHECK: El usuario {user_id} ESTÁ online. Intentando enviar por WebSocket.")
            logger.info(f"Usuario {user_id} está online. Se intentará enviar por WebSocket.")
            # Enviar por WebSocket (rápido, sin usar batería del teléfono)
            from .consumers import send_notification_via_websocket
            try:
                print(f"[send_notification] Entrando en la función 'send_notification_via_websocket' para user_id: {user_id}")
                send_notification_via_websocket(user_id, notification_type, notification_data)
                print(f"[send_notification] Éxito al enviar por WebSocket a user_id: {user_id}")
                logger.info(f"Notificación enviada por WebSocket a {user_id} con éxito.")
                return {
                    'success': True,
                    'method': 'websocket',
                    'message': f'Notificación {notification_type} enviada por WebSocket'
                }
            except Exception as e:
                print(f"[send_notification] ERROR al enviar por WebSocket: {str(e)}. Se intentará con FCM.")
                logger.error(f"Error al enviar por WebSocket: {str(e)}")
                # Continuar con FCM como fallback
        
        print(f"[send_notification] IF-CHECK: El usuario {user_id} está OFFLINE. Se enviará Push Notification (FCM).")
        logger.info(f"Usuario {user_id} está offline. Se procederá con FCM.")
        # Si no está online, enviar Push Notification a FCM
        if fcm_payload is None:
            print("[send_notification] fcm_payload es None. Construyendo payload por defecto...")
            logger.info("fcm_payload es None, construyendo payload por defecto.")
            fcm_payload = NotificationService._build_default_fcm_payload(
                notification_type,
                notification_data
            )

        print(f"[send_notification] Llamando a 'send_push_notification' para user_id: {user_id}")
        result = NotificationService.send_push_notification(user_id, fcm_payload)
        result['method'] = 'fcm'
        return result

    @staticmethod
    def send_push_notification(
        user_id: int,
        fcm_payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Envía una Push Notification a través de Firebase Cloud Messaging.
        
        Args:
            user_id (int): ID del usuario
            fcm_payload (dict): Payload con 'title', 'body', 'data', etc.
            
        Returns:
            dict: {
                'success': bool,
                'message': str,
                'fcm_response': dict o None,
                'errors': list
            }
        """
        print(f"\n--- INICIO send_push_notification para user_id: {user_id} ---")
        logger.info(f"Iniciando send_push_notification para user_id: {user_id}")
        print(f"Parámetros recibidos: user_id={user_id}, fcm_payload={fcm_payload}")
        logger.info(f"Payload FCM para {user_id}: {fcm_payload}")
        from .firebase_init import ensure_firebase_initialized

        firebase_ok, firebase_error = ensure_firebase_initialized()
        if not firebase_ok:
            return {
                'success': False,
                'message': firebase_error,
                'fcm_response': None,
                'errors': [firebase_error],
            }

        from firebase_admin import messaging

        # Obtener los dispositivos activos del usuario
        print(f"[send_push_notification] Buscando dispositivos activos para el usuario {user_id}")
        from .models import UserDevice
        devices = UserDevice.objects.filter(
            account_id=user_id,
            is_active=True
        )

        print(f"[send_push_notification] Se encontraron {devices.count()} dispositivos activos para el usuario {user_id}")
        logger.info(f"Se encontraron {devices.count()} dispositivos activos para el usuario {user_id}")

        if not devices.exists():
            return {
                'success': False,
                'message': f'No hay dispositivos registrados para el usuario {user_id}',
                'fcm_response': None,
                'errors': ['sin_dispositivos']
            }

        # Extraer tokens FCM
        fcm_tokens = [device.registration_token for device in devices]
        print(f"[send_push_notification] Tokens FCM a usar: {fcm_tokens}")
        logger.info(f"Tokens FCM para {user_id}: {fcm_tokens}")

        try:
            print("[send_push_notification] Creando mensaje multicast de FCM...")
            logger.info("Creando mensaje multicast de FCM...")
            # Crear mensaje multicast (para múltiples dispositivos)
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=fcm_payload.get('title', 'Notificación'),
                    body=fcm_payload.get('body', ''),
                ),
                data=fcm_payload.get('data', {}),
                tokens=fcm_tokens,
            )

            print("[send_push_notification] Enviando mensaje a Firebase...")
            logger.info("Enviando mensaje multicast a Firebase...")
            response = messaging.send_each_for_multicast(message)

            success_count = response.success_count
            failure_count = response.failure_count
            print(f"[send_push_notification] Respuesta de FCM: {success_count} exitosos, {failure_count} fallidos.")
            logger.info(f"Respuesta de FCM para {user_id}: {success_count} exitosos, {failure_count} fallidos.")

            if failure_count:
                logger.warning(f"FCM: {failure_count} fallos de {len(fcm_tokens)} intentos")
                failed_tokens = [
                    fcm_tokens[idx]
                    for idx, send_response in enumerate(response.responses)
                    if not send_response.success
                ]
                UserDevice.objects.filter(
                    registration_token__in=failed_tokens,
                    account_id=user_id
                ).update(is_active=False)

            return {
                'success': failure_count == 0,
                'message': f'Push enviada a {success_count}/{len(fcm_tokens)} dispositivos',
                'fcm_response': {
                    'successful': success_count,
                    'failed': failure_count,
                },
                'errors': []
            }

        except Exception as e:
            print(f"[send_push_notification] ERROR al enviar Push Notification: {str(e)}")
            logger.error(f"Error al enviar Push Notification: {str(e)}")
            return {
                'success': False,
                'message': f'Error al enviar Push Notification: {str(e)}',
                'fcm_response': None,
                'errors': [str(e)]
            }

    @staticmethod
    def _build_default_fcm_payload(
        notification_type: str,
        notification_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Construye un payload FCM por defecto según el tipo de notificación.
        
        Args:
            notification_type (str): Tipo de notificación
            notification_data (dict): Datos contextuales
            
        Returns:
            dict: Payload para Firebase
        """
        print(f"\n--- INICIO _build_default_fcm_payload para tipo: '{notification_type}' ---")
        logger.info(f"Construyendo payload FCM por defecto para el tipo: {notification_type}")
        print(f"Datos de notificación recibidos: {notification_data}")

        payloads = {
            'like': {
                'title': f"{notification_data.get('actor_name', 'Usuario')} te dio un like",
                'body': notification_data.get('post_title', 'Tu post'),
                'data': {
                    'type': 'like',
                    'actor_id': str(notification_data.get('actor_id', '')),
                    'post_id': str(notification_data.get('post_id', '')),
                    'action': 'open_post',
                }
            },
            'follow': {
                'title': f"{notification_data.get('actor_name', 'Usuario')} te sigue",
                'body': 'Nueva conexión',
                'data': {
                    'type': 'follow',
                    'actor_id': str(notification_data.get('actor_id', '')),
                    'action': 'open_profile',
                }
            },
            'comment': {
                'title': f"{notification_data.get('actor_name', 'Usuario')} comentó tu post",
                'body': notification_data.get('comment_body', 'Nuevo comentario')[:100],
                'data': {
                    'type': 'comment',
                    'actor_id': str(notification_data.get('actor_id', '')),
                    'post_id': str(notification_data.get('post_id', '')),
                    'comment_id': str(notification_data.get('comment_id', '')),
                    'action': 'open_post',
                }
            },
            'message': {
                'title': notification_data.get('sender_name', 'Nuevo mensaje'),
                'body': (
                    notification_data.get('message', {}).get('content', 'Tienes un mensaje nuevo')[:100]
                ),
                'data': {
                    'type': 'message',
                    'event': 'new_message',
                    'conversation_id': str(notification_data.get('conversation_id', '')),
                    'message_id': str(notification_data.get('message_id', '')),
                    'sender_id': str(notification_data.get('sender_id', '')),
                    'action': 'open_chat',
                },
            },
        }

        default_payload = {
            'title': 'Nueva notificación',
            'body': notification_data.get('message', 'Tienes una nueva notificación'),
            'data': {
                'type': notification_type,
            }
        }

        result_payload = payloads.get(notification_type, default_payload)
        print(f"[_build_default_fcm_payload] Payload construido: {result_payload}")
        logger.info(f"Payload FCM construido para '{notification_type}': {result_payload}")
        return result_payload

    @staticmethod
    def get_user_devices(user_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene todos los dispositivos de un usuario.
        
        Args:
            user_id (int): ID del usuario
            
        Returns:
            list: Lista de dispositivos con su información
        """
        from .models import UserDevice
        
        devices = UserDevice.objects.filter(account_id=user_id)
        return [
            {
                'id': str(device.id),
                'device_id': device.device_id,
                'device_type': device.device_type,
                'is_active': device.is_active,
                'created_at': device.created_at.isoformat(),
            }
            for device in devices
        ]

    @staticmethod
    def deactivate_device(user_id: int, device_id: str) -> bool:
        """
        Desactiva un dispositivo de un usuario.
        
        Args:
            user_id (int): ID del usuario
            device_id (str): ID del dispositivo
            
        Returns:
            bool: True si se desactivó, False si no se encontró
        """
        from .models import UserDevice
        
        device = UserDevice.objects.filter(
            account_id=user_id,
            id=device_id
        ).first()

        if device:
            device.is_active = False
            device.save()
            return True

        return False
