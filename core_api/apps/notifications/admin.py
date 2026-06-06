from django.contrib import admin

from .models import Notification, UserDevice


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient', 'event_type', 'is_read', 'created_at']
    list_filter = ['event_type', 'is_read', 'created_at']
    search_fields = ['recipient__profile__user__username']
    readonly_fields = ['id', 'created_at']


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ['id', 'account', 'device_type', 'device_id', 'is_active', 'created_at']
    list_filter = ['device_type', 'is_active', 'created_at']
    search_fields = ['account__username', 'device_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
