from django.http import QueryDict
from rest_framework import serializers
from .models import Profile
from django.contrib.gis.geos import Point
from drf_spectacular.utils import extend_schema_field

class ProfileSerializer(serializers.ModelSerializer):
    # Use ImageField for write operations, but allow it to be optional.
    avatar = serializers.ImageField(required=False, write_only=True, allow_null=True, allow_empty_file=True)
    banner = serializers.ImageField(required=False, write_only=True, allow_null=True, allow_empty_file=True)

    # Use SerializerMethodField for read operations to return the full URL.
    avatar_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()

    # Explicit fields for location to help drf-spectacular
    latitude = serializers.FloatField(write_only=True, required=False, allow_null=True)
    longitude = serializers.FloatField(write_only=True, required=False, allow_null=True)
    location_coords = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        # We explicitly list fields to control the output.
        # 'avatar' and 'banner' are now write-only.
        # 'avatar_url' and 'banner_url' are read-only.
        fields = [ # Removed slug and is_default
            'id', 'user', 'display_name', 'bio', 'city', 'timezone',
            'can_be_followed',
            'avatar', 'banner', 'avatar_url', 'banner_url',
            'latitude', 'longitude', 'location_coords'
        ]
        read_only_fields = ['id', 'user', 'location_coords']

    @extend_schema_field(serializers.URLField)
    def get_avatar_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.get_avatar_url) if request else obj.get_avatar_url

    @extend_schema_field(serializers.URLField)
    def get_banner_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.get_banner_url) if request else obj.get_banner_url

    @extend_schema_field({'type': 'object', 'properties': {'latitude': {'type': 'number'}, 'longitude': {'type': 'number'}}})
    def get_location_coords(self, obj):
        if obj.location:
            return {"latitude": obj.location.y, "longitude": obj.location.x}
        return None

    def validate(self, attrs):
        latitude = attrs.get('latitude')
        longitude = attrs.get('longitude')

        if (latitude is not None and longitude is None) or (latitude is None and longitude is not None):
            raise serializers.ValidationError("Both latitude and longitude must be provided together.")

        if latitude is not None and longitude is not None:
            attrs['location'] = Point(longitude, latitude, srid=4326)
            del attrs['latitude']
            del attrs['longitude']

        return attrs

    def to_internal_value(self, data):
        # Si la petición es multipart y los campos de imagen no se envían,
        # DRF puede enviar un string vacío. Los eliminamos para evitar errores.
        if isinstance(data, QueryDict):
            data = data.copy()

        avatar = data.get('avatar', None)
        if avatar in ['', None] or (isinstance(avatar, str) and not hasattr(avatar, 'read')):
            data.pop('avatar', None)

        banner = data.get('banner', None)
        if banner in ['', None] or (isinstance(banner, str) and not hasattr(banner, 'read')):
            data.pop('banner', None)

        return super().to_internal_value(data)