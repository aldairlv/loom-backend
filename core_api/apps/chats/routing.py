from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r'^(?:v1/)?/?ws/chat/(?P<conversation_id>[^/]+)/?$',
        consumers.ChatConsumer.as_asgi(),
    ),
]
