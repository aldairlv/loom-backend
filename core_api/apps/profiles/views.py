from django.shortcuts import render
# profiles/views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiExample

from .mixins import MultiSerializerViewSetMixin
from .models import Profile
from .serializers import ProfileSerializer # Serializador principal

class ProfileViewSet(MultiSerializerViewSetMixin, ModelViewSet):
    queryset = Profile.objects.all()
    parser_classes = (MultiPartParser, FormParser) # Permite subida de archivos

    serializer_class = ProfileSerializer 

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "display_name": {"type": "string"},
                    "bio": {"type": "string"},
                    "city": {"type": "string"},
                    "timezone": {"type": "string"},
                    "can_be_followed": {"type": "boolean"},
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "avatar": {"type": "string", "format": "binary"},
                    "banner": {"type": "string", "format": "binary"}
                },
                "required": []
            }
        },
        responses={200: ProfileSerializer},
        examples=[
            OpenApiExample(
                'Profile update example',
                value={
                    'display_name': 'Aldair',
                    'bio': 'Fullstack developer.',
                    'city': 'Valencia',
                    'timezone': 'Europe/Madrid',
                    'can_be_followed': True,
                    'latitude': 39.478,
                    'longitude': -0.376,
                },
                request_only=True,
            ),
            OpenApiExample(
                'Profile response example',
                value={
                    'id': 'd290f1ee-6c54-4b01-90e6-d701748f0851',
                    'user': 1,
                    'display_name': 'Aldair',
                    'bio': 'Fullstack developer.',
                    'city': 'Valencia',
                    'timezone': 'Europe/Madrid',
                    'can_be_followed': True,
                    'avatar_url': 'http://localhost:8000/media/avatars/profile.jpg',
                    'banner_url': 'http://localhost:8000/media/banners/banner.jpg',
                    'location_coords': {'latitude': 39.478, 'longitude': -0.376}
                },
                response_only=True,
            )
        ]
    )
    def update(self, request, *args, **kwargs): # PUT
        return super().update(request, *args, **kwargs)

    @extend_schema(
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "display_name": {"type": "string"},
                    "bio": {"type": "string"},
                    "city": {"type": "string"},
                    "timezone": {"type": "string"},
                    "can_be_followed": {"type": "boolean"},
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                    "avatar": {"type": "string", "format": "binary"},
                    "banner": {"type": "string", "format": "binary"}
                },
                "required": []
            }
        },
        responses={200: ProfileSerializer},
        examples=[
            OpenApiExample(
                'Profile patch example',
                value={
                    'bio': 'Updated bio text.',
                    'city': 'Barcelona',
                },
                request_only=True,
            ),
            OpenApiExample(
                'Profile patch response example',
                value={
                    'id': 'd290f1ee-6c54-4b01-90e6-d701748f0851',
                    'user': 1,
                    'display_name': 'Aldair',
                    'bio': 'Updated bio text.',
                    'city': 'Barcelona',
                    'timezone': 'Europe/Madrid',
                    'can_be_followed': True,
                    'avatar_url': 'http://localhost:8000/media/avatars/updated-avatar.jpg',
                    'banner_url': 'http://localhost:8000/media/banners/updated-banner.jpg',
                    'location_coords': {'latitude': 39.478, 'longitude': -0.376}
                },
                response_only=True,
            )
        ]
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_default:
            return Response(
                {"detail": "No puedes eliminar tu perfil principal. Cambia el principal primero."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
    

    def get_serializer_context(self):
        # Esto es vital para que el serializer pueda construir la URL absoluta
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context