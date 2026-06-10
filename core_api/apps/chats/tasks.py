import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.cache import cache

from notifications.services import NotificationService

logger = logging.getLogger(__name__)

User = get_user_model()

CHAT_ACTIVE_CACHE_PREFIX = 'chat_active_'


def chat_active_cache_key(user_id, conversation_id) -> str:
    return f'{CHAT_ACTIVE_CACHE_PREFIX}{user_id}_{conversation_id}'


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    time_limit=120,
)
def notify_chat_participants(self, conversation_id, message_id, sender_id):
    """
    Notifica a participantes que no están viendo la conversación en tiempo real.
    Usuarios conectados al WebSocket del chat reciben el mensaje por group_send.
    """
    from .models import Message, Participant
    from .services import ChatService

    try:
        message = Message.objects.select_related('sender__profile').get(id=message_id)
        sender = message.sender
        participants = Participant.objects.filter(
            conversation_id=conversation_id,
        ).exclude(user_id=sender_id).select_related('user__profile')

        message_data = ChatService.serialize_message(message)
        preview = message.content[:100] if message.content else f'Nuevo {message.type}'

        for participant in participants:
            user_id = participant.user_id

            if cache.get(chat_active_cache_key(user_id, conversation_id)):
                continue

            sender_name = sender.username
            if hasattr(sender, 'profile') and sender.profile.display_name:
                sender_name = sender.profile.display_name

            notification_data = {
                'event': 'new_message',
                'conversation_id': str(conversation_id),
                'message_id': str(message_id),
                'message': message_data,
                'sender_id': str(sender_id),
                'sender_name': sender_name,
            }

            fcm_payload = {
                'title': sender_name,
                'body': preview,
                'data': {
                    'type': 'message',
                    'event': 'new_message',
                    'conversation_id': str(conversation_id),
                    'message_id': str(message_id),
                    'sender_id': str(sender_id),
                    'action': 'open_chat',
                },
            }

            NotificationService.send_notification(
                user_id=user_id,
                notification_type='message',
                notification_data=notification_data,
                fcm_payload=fcm_payload,
            )

    except Exception as exc:
        logger.exception('Error en notify_chat_participants: %s', exc)
        raise self.retry(exc=exc)
