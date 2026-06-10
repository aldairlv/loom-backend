from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Max
from django.utils import timezone

from .models import Conversation, Message, Participant
from .tasks import notify_chat_participants

User = get_user_model()

PAGE_SIZE = 50


class ChatService:

    @staticmethod
    def user_is_participant(conversation_id, user) -> bool:
        return Participant.objects.filter(
            conversation_id=conversation_id,
            user=user,
        ).exists()

    @staticmethod
    def get_or_create_direct_conversation(user_a, user_b) -> Conversation:
        if user_a.id == user_b.id:
            raise ValidationError('No puedes iniciar un chat contigo mismo.')

        conv = (
            Conversation.objects
            .filter(type=Conversation.DIRECT, participants=user_a)
            .filter(participants=user_b)
            .annotate(participant_count=Count('participants'))
            .filter(participant_count=2)
            .first()
        )

        if not conv:
            conv = Conversation.objects.create(type=Conversation.DIRECT)
            Participant.objects.bulk_create([
                Participant(conversation=conv, user=user_a),
                Participant(conversation=conv, user=user_b),
            ])
        return conv

    @staticmethod
    def create_group_conversation(creator, name, participant_ids) -> Conversation:
        participant_ids = set(participant_ids)
        participant_ids.add(str(creator.id))

        users = list(User.objects.filter(id__in=participant_ids))
        if len(users) < 2:
            raise ValidationError('Un grupo necesita al menos 2 participantes.')

        conv = Conversation.objects.create(type=Conversation.GROUP, name=name)
        Participant.objects.bulk_create([
            Participant(conversation=conv, user=user) for user in users
        ])
        return conv

    @staticmethod
    def get_user_conversations(user):
        return (
            Conversation.objects
            .filter(participants=user)
            .prefetch_related(
                'participants__user__profile',
                'messages',
            )
            .annotate(
                last_message_at=Max('messages__created_at'),
            )
            .order_by('-updated_at')
        )

    @staticmethod
    def create_message(
        conversation_id,
        sender,
        content='',
        msg_type=Message.TEXT,
        media_url='',
        *,
        notify=True,
    ) -> dict:
        if not ChatService.user_is_participant(conversation_id, sender):
            raise PermissionDenied('No eres participante de esta conversación.')

        msg = Message.objects.create(
            conversation_id=conversation_id,
            sender=sender,
            type=msg_type,
            content=content,
            media_url=media_url,
        )
        Conversation.objects.filter(id=conversation_id).update(updated_at=timezone.now())

        payload = ChatService.serialize_message(msg)
        ChatService.broadcast_message(conversation_id, payload)

        if notify:
            notify_chat_participants.delay(
                conversation_id=str(conversation_id),
                message_id=str(msg.id),
                sender_id=str(sender.id),
            )

        return payload

    @staticmethod
    def broadcast_message(conversation_id, message: dict):
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            f'chat_{conversation_id}',
            {'type': 'chat_message', 'message': message},
        )

    @staticmethod
    def serialize_message(msg: Message) -> dict:
        sender = msg.sender
        sender_name = sender.username
        sender_avatar = None
        if sender and hasattr(sender, 'profile'):
            sender_name = sender.profile.display_name or sender.username
            if sender.profile.avatar:
                sender_avatar = sender.profile.avatar.url

        return {
            'id': str(msg.id),
            'conversation_id': str(msg.conversation_id),
            'sender_id': str(sender.id) if sender else None,
            'sender_name': sender_name,
            'sender_avatar': sender_avatar,
            'type': msg.type,
            'content': msg.content,
            'media_url': msg.media_url,
            'is_deleted': msg.is_deleted,
            'created_at': msg.created_at.isoformat(),
        }

    @staticmethod
    def mark_read(conversation_id, user):
        if not ChatService.user_is_participant(conversation_id, user):
            raise PermissionDenied('No eres participante de esta conversación.')
        Participant.objects.filter(
            conversation_id=conversation_id,
            user=user,
        ).update(last_read_at=timezone.now())

    @staticmethod
    def get_unread_count(conversation_id, user) -> int:
        participant = Participant.objects.get(conversation_id=conversation_id, user=user)
        qs = Message.objects.filter(
            conversation_id=conversation_id,
            is_deleted=False,
        ).exclude(sender=user)
        if participant.last_read_at:
            qs = qs.filter(created_at__gt=participant.last_read_at)
        return qs.count()

    @staticmethod
    def get_messages(conversation_id, user, before_id=None, limit=PAGE_SIZE):
        if not ChatService.user_is_participant(conversation_id, user):
            raise PermissionDenied('No eres participante de esta conversación.')

        qs = Message.objects.filter(
            conversation_id=conversation_id,
            is_deleted=False,
        ).select_related('sender__profile').order_by('-created_at')

        if before_id:
            pivot = Message.objects.get(id=before_id, conversation_id=conversation_id)
            qs = qs.filter(created_at__lt=pivot.created_at)

        messages = list(qs[:limit])
        messages.reverse()
        return [ChatService.serialize_message(m) for m in messages]

    @staticmethod
    def soft_delete_message(message_id, user):
        msg = Message.objects.select_related('conversation').get(id=message_id)
        if msg.sender_id != user.id:
            raise PermissionDenied('Solo puedes eliminar tus propios mensajes.')
        msg.is_deleted = True
        msg.content = ''
        msg.media_url = ''
        msg.save(update_fields=['is_deleted', 'content', 'media_url'])
        return msg

    @staticmethod
    def get_other_participant(conversation: Conversation, user):
        if conversation.type != Conversation.DIRECT:
            return None
        return (
            conversation.participants
            .exclude(id=user.id)
            .select_related('profile')
            .first()
        )
