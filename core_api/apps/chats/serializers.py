from rest_framework import serializers

from .models import Conversation, Message, Participant
from .services import ChatService


class ChatParticipantSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    username = serializers.CharField()
    display_name = serializers.CharField()
    avatar_url = serializers.CharField(allow_null=True)


class MessageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    conversation_id = serializers.UUIDField()
    sender_id = serializers.UUIDField(allow_null=True)
    sender_name = serializers.CharField()
    sender_avatar = serializers.CharField(allow_null=True)
    type = serializers.CharField()
    content = serializers.CharField()
    media_url = serializers.CharField()
    is_deleted = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class ConversationSerializer(serializers.ModelSerializer):
    participants = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    display_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'type', 'name', 'display_name', 'display_avatar',
            'participants', 'last_message', 'unread_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_participants(self, obj):
        request = self.context.get('request')
        items = []
        for user in obj.participants.all():
            profile = getattr(user, 'profile', None)
            avatar_url = None
            if profile:
                avatar_url = profile.get_avatar_url
                if request:
                    avatar_url = request.build_absolute_uri(avatar_url)
            items.append({
                'user_id': str(user.id),
                'username': user.username,
                'display_name': profile.display_name if profile else user.username,
                'avatar_url': avatar_url,
            })
        return items

    def get_last_message(self, obj):
        last = obj.messages.filter(is_deleted=False).order_by('-created_at').first()
        if not last:
            return None
        return ChatService.serialize_message(last)

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        try:
            return ChatService.get_unread_count(obj.id, request.user)
        except Participant.DoesNotExist:
            return 0

    def get_display_name(self, obj):
        request = self.context.get('request')
        if obj.type == Conversation.GROUP:
            return obj.name or 'Grupo'
        if not request or not request.user.is_authenticated:
            return obj.name
        other = ChatService.get_other_participant(obj, request.user)
        if other and hasattr(other, 'profile'):
            return other.profile.display_name or other.username
        return obj.name or 'Chat'

    def get_display_avatar(self, obj):
        request = self.context.get('request')
        if obj.type == Conversation.GROUP:
            return None
        if not request or not request.user.is_authenticated:
            return None
        other = ChatService.get_other_participant(obj, request.user)
        if other and hasattr(other, 'profile'):
            url = other.profile.get_avatar_url
            return request.build_absolute_uri(url) if request else url
        return None


class CreateDirectConversationSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(help_text='ID del usuario con quien iniciar el chat')


class CreateGroupConversationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128)
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text='IDs de usuarios a incluir (sin contarte a ti)',
    )


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(required=False, allow_blank=True, default='')
    type = serializers.ChoiceField(choices=Message.TYPE_CHOICES, default=Message.TEXT)
    media_url = serializers.URLField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        msg_type = attrs.get('type', Message.TEXT)
        content = attrs.get('content', '')
        media_url = attrs.get('media_url', '')
        if msg_type == Message.TEXT and not content.strip():
            raise serializers.ValidationError({'content': 'El contenido es obligatorio para mensajes de texto.'})
        if msg_type in (Message.IMAGE, Message.FILE) and not media_url:
            raise serializers.ValidationError({'media_url': 'media_url es obligatorio para mensajes con archivo.'})
        return attrs
