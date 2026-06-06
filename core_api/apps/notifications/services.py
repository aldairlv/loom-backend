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
        cache_key = f"user_online_{user_id}"
        return cache.get(cache_key) is not None

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
        # Verificar si el usuario existe
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return {
                'success': False,
                'method': 'none',
                'message': f'Usuario {user_id} no encontrado'
            }

        # Estrategia A: Verificar si el usuario está online
        if NotificationService.is_user_online(user_id):
            # Enviar por WebSocket (rápido, sin usar batería del teléfono)
            from .consumers import send_notification_via_websocket
            try:
                send_notification_via_websocket(user_id, notification_type, notification_data)
                return {
                    'success': True,
                    'method': 'websocket',
                    'message': f'Notificación {notification_type} enviada por WebSocket'
                }
            except Exception as e:
                logger.error(f"Error al enviar por WebSocket: {str(e)}")
                # Continuar con FCM como fallback
        
        # Si no está online, enviar Push Notification a FCM
        if fcm_payload is None:
            fcm_payload = NotificationService._build_default_fcm_payload(
                notification_type,
                notification_data
            )

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
        try:
            import firebase_admin
            from firebase_admin import messaging
        except ImportError:
            return {
                'success': False,
                'message': 'Firebase Admin SDK no está instalado',
                'fcm_response': None,
                'errors': ['firebase-admin no instalado']
            }

        # Obtener los dispositivos activos del usuario
        from .models import UserDevice
        devices = UserDevice.objects.filter(
            account_id=user_id,
            is_active=True
        )

        if not devices.exists():
            return {
                'success': False,
                'message': f'No hay dispositivos registrados para el usuario {user_id}',
                'fcm_response': None,
                'errors': ['sin_dispositivos']
            }

        # Extraer tokens FCM
        fcm_tokens = [device.registration_token for device in devices]

        try:
            # Crear mensaje multicast (para múltiples dispositivos)
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=fcm_payload.get('title', 'Notificación'),
                    body=fcm_payload.get('body', ''),
                ),
                data=fcm_payload.get('data', {}),
                tokens=fcm_tokens,
            )

            # Enviar a Firebase
            response = messaging.send_multicast(message)

            # Procesar respuestas
            successful = response.successful
            failed = response.failed

            if failed:
                logger.warning(f"FCM: {len(failed)} fallos de {len(fcm_tokens)} intentos")
                # Marcar dispositivos fallidos como inactivos
                failed_tokens = [fcm_tokens[idx] for idx, _ in enumerate(failed)]
                UserDevice.objects.filter(
                    registration_token__in=[failed_tokens],
                    account_id=user_id
                ).update(is_active=False)

            return {
                'success': len(failed) == 0,
                'message': f'Push enviada a {len(successful)}/{len(fcm_tokens)} dispositivos',
                'fcm_response': {
                    'successful': len(successful),
                    'failed': len(failed),
                },
                'errors': []
            }

        except Exception as e:
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
        }

        return payloads.get(notification_type, {
            'title': 'Nueva notificación',
            'body': notification_data.get('message', 'Tienes una nueva notificación'),
            'data': {
                'type': notification_type,
            }
        })

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
