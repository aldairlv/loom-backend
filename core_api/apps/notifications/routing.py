from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # This pattern will match /ws/notifications/, /v1/ws/notifications/, and also tolerate /v1//ws/notifications/
    re_path(r"^(?:v1/)?/?ws/notifications/?$", consumers.NotificationConsumer.as_asgi()),
]