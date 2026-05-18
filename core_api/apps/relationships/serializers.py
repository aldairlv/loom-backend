from rest_framework import serializers
from profiles.models import Profile
from .models import Follow
from .services import follow_profile


class FollowerProfileSerializer(serializers.ModelSerializer):
    """Serializer simplificado para mostrar en listas de seguidores/seguidos."""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Profile
        fields = ['id', 'username', 'display_name', 'avatar']


class FollowSerializer(serializers.ModelSerializer):
    """Serializer para crear y listar relaciones de seguimiento."""
    from_profile = FollowerProfileSerializer(read_only=True)
    to_profile = FollowerProfileSerializer(read_only=True)

    # Campo para la creación, para recibir el ID del perfil a seguir
    to_profile_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Follow
        fields = ['id', 'from_profile', 'to_profile', 'created_at', 'to_profile_id']
        read_only_fields = ['id', 'from_profile', 'to_profile', 'created_at']

    def validate_to_profile_id(self, value):
        """Valida que el perfil a seguir exista."""
        if not Profile.objects.filter(id=value).exists():
            raise serializers.ValidationError("El perfil al que intentas seguir no existe.")
        return value

    def create(self, validated_data):
        from_profile = self.context['request'].user.profile
        to_profile_id = validated_data['to_profile_id']
        to_profile = Profile.objects.get(id=to_profile_id)

        try:
            follow, created = follow_profile(from_profile, to_profile)
            if not created:
                raise serializers.ValidationError({'detail': 'Ya sigues a este perfil.'})
            return follow
        except ValueError as e:
            raise serializers.ValidationError({'detail': str(e)})