from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation, Message
from .serializers import (
    ConversationSerializer,
    CreateDirectConversationSerializer,
    CreateGroupConversationSerializer,
    MessageSerializer,
    SendMessageSerializer,
)
from .services import ChatService

User = get_user_model()


class ChatResponseMixin:
    def chat_response(self, request, key, data, status_code=status.HTTP_200_OK):
        return Response({
            'meta': {
                'status': status_code,
                'msg': 'OK',
                'xRoomUserId': str(request.user.id),
            },
            'response': {key: data},
        }, status=status_code)


@extend_schema(
    tags=['Chats'],
    summary='Listar conversaciones',
    description='Devuelve las conversaciones del usuario autenticado con último mensaje y contador de no leídos.',
)
class ConversationListView(ChatResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        convs = ChatService.get_user_conversations(request.user)
        serializer = ConversationSerializer(convs, many=True, context={'request': request})
        elements = serializer.data
        for item in elements:
            item['objectType'] = 'conversation'
            item['id'] = str(item['id'])
        return self.chat_response(request, 'conversations', {
            'elements': elements,
            'queryParams': {'cursor': None},
        })

    @extend_schema(request=CreateDirectConversationSerializer, responses={201: ConversationSerializer})
    def post(self, request):
        serializer = CreateDirectConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        other = get_object_or_404(User, id=serializer.validated_data['user_id'])
        conv = ChatService.get_or_create_direct_conversation(request.user, other)
        data = ConversationSerializer(conv, context={'request': request}).data
        data['id'] = str(data['id'])
        return self.chat_response(request, 'conversation', data, status.HTTP_201_CREATED)


@extend_schema(
    tags=['Chats'],
    summary='Crear conversación grupal',
    request=CreateGroupConversationSerializer,
    responses={201: ConversationSerializer},
)
class GroupConversationCreateView(ChatResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateGroupConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conv = ChatService.create_group_conversation(
            creator=request.user,
            name=serializer.validated_data['name'],
            participant_ids=[str(uid) for uid in serializer.validated_data['participant_ids']],
        )
        conv = ChatService.get_user_conversations(request.user).get(id=conv.id)
        data = ConversationSerializer(conv, context={'request': request}).data
        data['id'] = str(data['id'])
        return self.chat_response(request, 'conversation', data, status.HTTP_201_CREATED)


@extend_schema(
    tags=['Chats'],
    summary='Detalle de conversación',
    responses={200: ConversationSerializer},
)
class ConversationDetailView(ChatResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        conv = get_object_or_404(
            ChatService.get_user_conversations(request.user),
            id=conversation_id,
        )
        data = ConversationSerializer(conv, context={'request': request}).data
        data['id'] = str(data['id'])
        return self.chat_response(request, 'conversation', data)


@extend_schema(
    tags=['Chats'],
    summary='Historial de mensajes',
    parameters=[
        OpenApiParameter(
            name='before',
            description='UUID del mensaje; devuelve mensajes anteriores a ese mensaje',
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name='limit',
            description='Cantidad máxima de mensajes (default 50)',
            required=False,
            type=int,
        ),
    ],
    responses={200: MessageSerializer(many=True)},
)
class MessageListView(ChatResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        before_id = request.query_params.get('before')
        limit = int(request.query_params.get('limit', 50))
        messages = ChatService.get_messages(
            conversation_id=conversation_id,
            user=request.user,
            before_id=before_id,
            limit=min(limit, 100),
        )
        return self.chat_response(request, 'messages', {
            'elements': messages,
            'queryParams': {'before': before_id},
        })

    @extend_schema(request=SendMessageSerializer, responses={201: MessageSerializer})
    def post(self, request, conversation_id):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = ChatService.create_message(
            conversation_id=conversation_id,
            sender=request.user,
            content=serializer.validated_data.get('content', ''),
            msg_type=serializer.validated_data.get('type', Message.TEXT),
            media_url=serializer.validated_data.get('media_url', ''),
        )
        return self.chat_response(request, 'message', message, status.HTTP_201_CREATED)


@extend_schema(
    tags=['Chats'],
    summary='Marcar conversación como leída',
)
class MarkReadView(ChatResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        ChatService.mark_read(conversation_id, request.user)
        return self.chat_response(request, 'read', {
            'conversation_id': str(conversation_id),
            'read_at': request.data.get('read_at'),
        })


@extend_schema(
    tags=['Chats'],
    summary='Contador de mensajes no leídos',
)
class UnreadCountView(ChatResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        count = ChatService.get_unread_count(conversation_id, request.user)
        return self.chat_response(request, 'unread', {
            'conversation_id': str(conversation_id),
            'count': count,
        })


@extend_schema(
    tags=['Chats'],
    summary='Eliminar mensaje (soft delete)',
)
class MessageDeleteView(ChatResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, message_id):
        ChatService.soft_delete_message(message_id, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
