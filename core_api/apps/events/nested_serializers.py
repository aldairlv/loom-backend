from rest_framework import serializers
from profiles.serializers import ProfileSerializer
from drf_spectacular.utils import extend_schema_field
from assets.serializers import MediaSerializer
from profiles.models import Profile
from .models import Event


class EventCreatorSerializer(serializers.ModelSerializer):
    """
    A simplified serializer for the event creator, matching the requested format.
    """
    creator_display_name = serializers.CharField(source='display_name')
    avatar_url = serializers.SerializerMethodField() # get_avatar_url

    class Meta:
        model = Profile
        fields = ['creator_display_name', 'avatar_url']

    @extend_schema_field(serializers.URLField)
    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if request and obj.get_avatar_url:
            return request.build_absolute_uri(obj.get_avatar_url)
        return None


class EventLocationSerializer(serializers.Serializer):
    """
    Serializer for the nested location object.
    """
    location_name = serializers.CharField()
    location_address = serializers.CharField()
    coordinates = serializers.SerializerMethodField()

    def get_coordinates(self, obj):
        if obj.location:
            return {
                "latitude": obj.location.y,
                "longitude": obj.location.x
            }
        return None


class FriendsAttendingSerializer(serializers.ModelSerializer):
    """
    Serializer for friends attending an event.
    """
    avatar_url = serializers.SerializerMethodField() # get_avatar_url

    class Meta:
        model = Profile
        fields = ['id', 'display_name', 'avatar_url']

    @extend_schema_field(serializers.URLField)
    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if request and obj.get_avatar_url:
            return request.build_absolute_uri(obj.get_avatar_url)
        return None


class EventFeedSerializer(serializers.ModelSerializer):
    """
    The main serializer for an event object within the feed.
    """
    type = serializers.CharField(default="event", read_only=True)
    timestamp = serializers.SerializerMethodField()
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    creator = EventCreatorSerializer(read_only=True)
    
    # This field will contain the bulk of the event data
    event_data = serializers.SerializerMethodField()
    # We need to prefetch attendees to implement friends_attending logic
    friends_attending = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'type', 'timestamp', 'tags', 'creator', 'event_data', 'friends_attending']

    @extend_schema_field(serializers.IntegerField)
    def get_timestamp(self, obj: Event) -> int:
        return int(obj.created_at.timestamp())

    @extend_schema_field(serializers.DictField)
    def get_event_data(self, obj: Event) -> dict:
        # Here we construct the nested 'event_data' object
        return {
            "title": obj.title,
            "description": obj.description,
            "assets": MediaSerializer(obj.assets, many=True, context=self.context).data,
            "start_time": obj.start_time,
            "end_time": obj.end_time,
            "location": EventLocationSerializer(obj).data,
            "rsvp_count": obj.rsvp_count,
            "max_attendees": obj.max_attendees,
            "is_online": obj.is_online,
            "is_public": obj.is_public,
            "is_cancelled": obj.is_cancelled,
            "status": obj.status,
        }

    @extend_schema_field(FriendsAttendingSerializer(many=True))
    def get_friends_attending(self, obj: Event) -> list:
        # Placeholder logic: This needs to be implemented based on your "friends" relationship model.
        # For now, it returns an empty list as requested in the example.
        return []