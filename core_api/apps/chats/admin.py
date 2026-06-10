from django.contrib import admin

from .models import Conversation, Message, Participant


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'type', 'content', 'created_at')
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'name', 'updated_at', 'created_at')
    list_filter = ('type',)
    inlines = [ParticipantInline, MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'type', 'is_deleted', 'created_at')
    list_filter = ('type', 'is_deleted')
