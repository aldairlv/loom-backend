from rest_framework import serializers
from .models import Profile

class ProfileFileUpdateSerializer(serializers.ModelSerializer):
    """
    Un serializador específico para manejar la subida de avatar y banner en PATCH/PUT.
    """
    class Meta:
        model = Profile
        fields = ['avatar', 'banner']