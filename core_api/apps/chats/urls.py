from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListView,
    GroupConversationCreateView,
    MarkReadView,
    MessageDeleteView,
    MessageListView,
    UnreadCountView,
)

urlpatterns = [
    path('conversations/', ConversationListView.as_view(), name='chat-conversation-list'),
    path('conversations/group/', GroupConversationCreateView.as_view(), name='chat-group-create'),
    path('conversations/<uuid:conversation_id>/', ConversationDetailView.as_view(), name='chat-conversation-detail'),
    path('conversations/<uuid:conversation_id>/messages/', MessageListView.as_view(), name='chat-message-list'),
    path('conversations/<uuid:conversation_id>/read/', MarkReadView.as_view(), name='chat-mark-read'),
    path('conversations/<uuid:conversation_id>/unread/', UnreadCountView.as_view(), name='chat-unread-count'),
    path('messages/<uuid:message_id>/', MessageDeleteView.as_view(), name='chat-message-delete'),
]
