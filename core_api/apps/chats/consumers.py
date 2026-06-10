import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache

from notifications.consumers import make_json_safe
from .services import ChatService
from .tasks import chat_active_cache_key

logger = logging.getLogger(__name__)

CHAT_ACTIVE_CACHE_TIMEOUT = 3600


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.group_name = f'chat_{self.conversation_id}'

        if not await self._is_participant():
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self._set_chat_active(True)

    async def disconnect(self, close_code):
        if getattr(self, 'group_name', None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if self.user.is_authenticated:
            await self._set_chat_active(False)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = data.get('action')

        if action == 'send_message':
            await database_sync_to_async(ChatService.create_message)(
                conversation_id=self.conversation_id,
                sender=self.user,
                content=data.get('content', ''),
                msg_type=data.get('type', 'text'),
                media_url=data.get('media_url', ''),
                notify=True,
            )

        elif action == 'mark_read':
            await database_sync_to_async(ChatService.mark_read)(
                conversation_id=self.conversation_id,
                user=self.user,
            )
            await self.send(text_data=json.dumps({
                'event': 'read_ack',
                'conversation_id': str(self.conversation_id),
            }))

        elif action == 'typing':
            await self.channel_layer.group_send(self.group_name, {
                'type': 'typing_event',
                'user_id': str(self.user.id),
                'is_typing': data.get('is_typing', False),
            })

        elif action == 'ping':
            await self._set_chat_active(True)
            await self.send(text_data=json.dumps({'event': 'pong'}))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'event': 'new_message',
            'message': make_json_safe(event['message']),
        }))

    async def typing_event(self, event):
        if str(self.user.id) != event['user_id']:
            await self.send(text_data=json.dumps({
                'event': 'typing',
                'user_id': event['user_id'],
                'is_typing': event['is_typing'],
            }))

    @database_sync_to_async
    def _is_participant(self):
        return ChatService.user_is_participant(self.conversation_id, self.user)

    async def _set_chat_active(self, active: bool):
        key = chat_active_cache_key(self.user.id, self.conversation_id)
        if active:
            await database_sync_to_async(cache.set)(
                key, True, timeout=CHAT_ACTIVE_CACHE_TIMEOUT,
            )
        else:
            await database_sync_to_async(cache.delete)(key)
