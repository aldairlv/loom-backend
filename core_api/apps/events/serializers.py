from rest_framework import serializers
from .models import Event, EventStatus
from posts.fields import TagRelatedField # Reusing TagRelatedField from posts app
from profiles.models import Profile # For creator validation
from posts.models import Tag
from assets.models import Media
from assets.serializers import MediaSerializer
from django.contrib.gis.geos import Point

class EventSerializer(serializers.ModelSerializer):
    creator = serializers.PrimaryKeyRelatedField(read_only=True) # Set by view
    tags = TagRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        slug_field='name',
        required=False
    )
    # Read-only field for the creator's display name
    creator_display_name = serializers.CharField(source='creator.display_name', read_only=True)
    
    assets = MediaSerializer(many=True, read_only=True)
    asset_ids = serializers.PrimaryKeyRelatedField(
        queryset=Media.objects.all(),
        source='assets',
        many=True,
        write_only=True,
        required=False
    )

    # Campos para manejar la geolocalización sin exponer el PointField directamente.
    # Para la entrada (write), aceptamos lat/lon.
    latitude = serializers.FloatField(write_only=True, required=False)
    longitude = serializers.FloatField(write_only=True, required=False)

    # Para la salida (read), los calculamos desde el campo 'location'.
    # Usamos SerializerMethodField para la lectura.
    read_latitude = serializers.SerializerMethodField(method_name='get_latitude')
    read_longitude = serializers.SerializerMethodField(method_name='get_longitude')

    class Meta:
        model = Event
        fields = [
            'id', 'creator', 'creator_display_name', 'title', 'slug', 'description',
            'start_time', 'end_time', 'location_name', 'location_address', 'assets', 'asset_ids',
            'latitude', 'longitude', 'read_latitude', 'read_longitude',
            'max_attendees', 'is_online', 'is_public',
            'is_cancelled', 'status',  'tags',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'creator', 'creator_display_name', 'is_cancelled',
                            'created_at', 'updated_at' ]
        extra_kwargs = {
            'slug': {'required': False, 'allow_blank': True}
        }

    def get_latitude(self, obj: Event) -> float | None:
        """Devuelve la latitud desde el campo PointField."""
        if obj.location:
            return obj.location.y
        return None

    def get_longitude(self, obj: Event) -> float | None:
        """Devuelve la longitud desde el campo PointField."""
        if obj.location:
            return obj.location.x
        return None

    def validate(self, data: dict) -> dict:
        """
        Custom validation for start_time and end_time.
        """
        start_time = data.get('start_time', getattr(self.instance, 'start_time', None))
        end_time = data.get('end_time', getattr(self.instance, 'end_time', None))

        if start_time and end_time and end_time < start_time:
            raise serializers.ValidationError("End time cannot be before start time.")
        
        # Validar y construir el punto geográfico
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        if latitude is not None and longitude is not None:
            data['location'] = Point(longitude, latitude, srid=4326)
        elif (latitude is not None) != (longitude is not None): # XOR
            raise serializers.ValidationError("Debe proporcionar tanto latitud como longitud, o ninguna.")

        # If event is online, location_address can be a URL, otherwise it should be a physical address.
        is_online = data.get('is_online', getattr(self.instance, 'is_online', False))
        location_address = data.get('location_address', getattr(self.instance, 'location_address', None))

        if is_online and location_address and not (location_address.startswith('http://') or location_address.startswith('https://')):
            # This is a soft check, could be more robust with URLField validation if needed
            # For now, just a warning or a specific error if it's critical.
            pass # Allow non-URL for online events, e.g., "Zoom Link provided after registration"
        
        if not is_online and not location_address:
            # For physical events, location_address should ideally be provided.
            # This can be a warning or a hard error depending on business rules.
            # For now, let's make it a warning, as location_name might suffice.
            pass

        return data

    def create(self, validated_data: dict) -> Event:
        # Handle tags separately as they are ManyToMany
        tags_data = validated_data.pop('tags', [])
        assets_data = validated_data.pop('assets', [])
        # Remove lat/lon as they are already processed into 'location'
        validated_data.pop('latitude', None)
        validated_data.pop('longitude', None)

        event = Event.objects.create(**validated_data)
        event.tags.set(tags_data)
        event.assets.set(assets_data)
        return event

    def update(self, instance: Event, validated_data: dict) -> Event:
        tags_data = validated_data.pop('tags', None)
        assets_data = validated_data.pop('assets', None)
        # Remove lat/lon as they are already processed into 'location'
        validated_data.pop('latitude', None)
        validated_data.pop('longitude', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags_data is not None: # Only update if tags were provided in the payload
            instance.tags.set(tags_data)
        if assets_data is not None:
            instance.assets.set(assets_data)
        return instance