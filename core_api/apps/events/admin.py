from django.contrib import admin
from .models import Event, EventStatus

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'creator', 'start_time', 'end_time', 'status',
        'is_online', 'is_public', 'is_cancelled', 'created_at'
    )
    list_filter = ('status', 'is_online', 'is_public', 'is_cancelled', 'created_at', 'updated_at')
    search_fields = ('title', 'description', 'location_name', 'location_address', 'creator__display_name')
    raw_id_fields = ('creator',) # Use raw_id_fields for ForeignKey to Profile
    filter_horizontal = ('tags',) # For ManyToManyField

    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'creator', 'tags')
        }),
        ('Time & Status', {
            'fields': ('start_time', 'end_time', 'status', 'is_cancelled')
        }),
        ('Location', {
            'fields': ('is_online', 'location_name', 'location_address', 'location')
        }),
        ('Visibility & Capacity', {
            'fields': ('is_public', 'max_attendees')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ('created_at', 'updated_at')
