from rest_framework import serializers
from django.db.models import Avg
from profiles.serializers import ProfileSerializer
from drf_spectacular.utils import extend_schema_field
from assets.serializers import MediaSerializer
from profiles.models import Profile
from .models import Event, EventAttendance


class EventCreatorSerializer(serializers.ModelSerializer):
    """
    A simplified serializer for the event creator, matching the requested format.
    """
    avatar_url = serializers.SerializerMethodField() # get_avatar_url
    is_followed = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['id', 'display_name', 'avatar_url', 'bio', 'is_followed']

    @extend_schema_field(serializers.URLField)
    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if request and obj.get_avatar_url:
            return request.build_absolute_uri(obj.get_avatar_url)
        return None

    @extend_schema_field(serializers.BooleanField)
    def get_is_followed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        try:
            current_profile = request.user.profile
        except Profile.DoesNotExist:
            return False

        return current_profile.following_relationships.filter(to_profile=obj).exists()


class EventAttendeeSampleSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField() # get_avatar_url
    is_followed = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['id', 'display_name', 'avatar_url', 'bio', 'is_followed']

    @extend_schema_field(serializers.URLField)
    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if request and obj.get_avatar_url:
            return request.build_absolute_uri(obj.get_avatar_url)
        return None

    @extend_schema_field(serializers.BooleanField)
    def get_is_followed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False

        try:
            current_profile = request.user.profile
        except Profile.DoesNotExist:
            return False

        return current_profile.following_relationships.filter(to_profile=obj).exists()


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
    user_rsvp_status = serializers.SerializerMethodField()
    access_details = serializers.SerializerMethodField()
    attendees_sample = serializers.SerializerMethodField()
    # We need to prefetch attendees to implement friends_attending logic
    friends_attending = serializers.SerializerMethodField()
    # Campo para mostrar la distancia al evento
    distance = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'type', 'timestamp', 'tags', 'creator', 'event_data', 'user_rsvp_status', 'access_details', 'attendees_sample', 'friends_attending', 'distance']

    @extend_schema_field(serializers.IntegerField)
    def get_timestamp(self, obj: Event) -> int:
        return int(obj.created_at.timestamp())

    @extend_schema_field(serializers.DictField)
    def get_event_data(self, obj: Event) -> dict:
        # Here we construct the nested 'event_data' object
        request = self.context.get('request')
        user_rsvp_status = 'not_going'
        if request and request.user.is_authenticated:
            try:
                user_profile = request.user.profile
                if obj.attendees.filter(pk=user_profile.pk).exists():
                    user_rsvp_status = 'going'
            except Profile.DoesNotExist:
                pass

        rating_summary = obj.rating_summary

        thumbnail_url = None
        if obj.thumbnail and obj.thumbnail.url:
            if request:
                thumbnail_url = request.build_absolute_uri(obj.thumbnail.url)
            else:
                thumbnail_url = obj.thumbnail.url

        return {
            "title": obj.title,
            "description": obj.description,
            "thumbnail_url": thumbnail_url,
            "assets": MediaSerializer(obj.assets, many=True, context=self.context).data,
            "start_time": obj.start_time,
            "end_time": obj.end_time,
            "timezone": obj.timezone,
            "location": EventLocationSerializer(obj).data,
            "rsvp_count": obj.rsvp_count,
            "max_attendees": obj.max_attendees,
            "is_online": obj.is_online,
            "is_public": obj.is_public,
            "is_cancelled": obj.is_cancelled,
            "status": obj.status,
            "category": obj.category,
            "requirements": obj.requirements or [],
            "requires_qr_checkin": obj.requires_qr_checkin,
            "payment_details": {
                "requires_payment": obj.requires_payment,
                "price": float(obj.price_amount) if obj.price_amount is not None else None,
                "currency": obj.price_currency,
                "payment_methods_allowed": obj.payment_methods_allowed or [],
                "stripe_price_id": obj.stripe_price_id,
            },
            "contact_channels": {
                "support_email": obj.support_email,
                "support_url": obj.support_url,
                "website_url": obj.website_url,
                "whatsapp_url": obj.whatsapp_url,
                "telegram_url": obj.telegram_url,
                "discord_url": obj.discord_url,
                "zoom_url": obj.zoom_url,
            },
            "rating_summary": rating_summary,
        }

    @extend_schema_field(serializers.CharField)
    def get_user_rsvp_status(self, obj: Event) -> str:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 'not_going'

        try:
            user_profile = request.user.profile
        except Profile.DoesNotExist:
            return 'not_going'

        return 'going' if obj.attendees.filter(pk=user_profile.pk).exists() else 'not_going'

    @extend_schema_field(serializers.DictField)
    def get_access_details(self, obj: Event) -> dict | None:
        if self.get_user_rsvp_status(obj) != 'going':
            return None

        secure_token = None
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                # Find the specific attendance record for the user and event
                attendance_record = EventAttendance.objects.get(event=obj, attendee=request.user.profile)
                secure_token = attendance_record.secure_attendance_token
            except (Profile.DoesNotExist, EventAttendance.DoesNotExist):
                pass

        return {
            "meeting_instructions": obj.meeting_instructions,
            "live_stream_url": obj.live_stream_url,
            "secure_attendance_token": secure_token,
        }

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_attendees_sample(self, obj: Event) -> list:
        request = self.context.get('request')
        following_ids = []
        if request and request.user.is_authenticated:
            try:
                current_profile = request.user.profile
                following_ids = list(current_profile.following_relationships.values_list('to_profile_id', flat=True))
            except Profile.DoesNotExist:
                following_ids = []

        attendees = obj.attendees.all()[:3]
        return EventAttendeeSampleSerializer(attendees, many=True, context=self.context).data

    @extend_schema_field(FriendsAttendingSerializer(many=True))
    def get_friends_attending(self, obj: Event) -> list:
        """
        Calcula y devuelve una lista de amigos (seguimiento mutuo) del usuario actual
        que también asisten a este evento.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []

        try:
            user_profile = request.user.profile
        except Profile.DoesNotExist:
            return []

        # 1. Obtiene los IDs de los perfiles que el usuario actual sigue.
        following_ids = user_profile.following_relationships.values_list('to_profile_id', flat=True)
        
        # 2. Obtiene los IDs de los perfiles que siguen al usuario actual (sus seguidores).
        follower_ids = user_profile.follower_relationships.values_list('from_profile_id', flat=True)

        # 3. Filtra los asistentes al evento para encontrar aquellos que están en ambas listas (amigos).
        friends_attending = obj.attendees.filter(id__in=following_ids).filter(id__in=follower_ids)
        
        return FriendsAttendingSerializer(friends_attending, many=True, context=self.context).data

    @extend_schema_field(serializers.FloatField)
    def get_distance(self, obj: Event) -> float | None:
        """
        Devuelve la distancia al evento si se ha calculado.
        El valor viene en metros desde la base de datos, lo convertimos a km.
        """
        # El campo 'distance' es anotado en el queryset por EventService.filter_events
        if hasattr(obj, 'distance') and obj.distance is not None:
            meters = obj.distance.m
            return float(meters) / 1000
        return None