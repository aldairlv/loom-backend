from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import get_object_or_404

from profiles.models import Profile
from .serializers import FollowSerializer, FollowerProfileSerializer
from .services import follow_profile, unfollow_profile, get_follow_queryset


@extend_schema(
    tags=['Relationships'],
    summary="Seguir a un perfil",
    description="Crea una relación de seguimiento desde el perfil del usuario autenticado hacia otro perfil."
)
class FollowCreateView(generics.CreateAPIView):
    """
    Vista para seguir a un perfil.
    El `from_profile` se obtiene del usuario autenticado.
    Se debe proporcionar el `to_profile_id` en el cuerpo de la solicitud.
    """
    serializer_class = FollowSerializer
    permission_classes = [IsAuthenticated]


@extend_schema(
    tags=['Relationships'],
    summary="Dejar de seguir a un perfil",
    description="Elimina una relación de seguimiento. Se debe proporcionar el ID del perfil a dejar de seguir.",
    parameters=[
        OpenApiParameter(name='profile_id', description='El ID del perfil a dejar de seguir', required=True, type=str, location=OpenApiParameter.PATH)
    ]
)
class UnfollowAPIView(APIView):
    """
    Vista para dejar de seguir a un perfil.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, profile_id, *args, **kwargs):
        from_profile = request.user.profile
        to_profile = get_object_or_404(Profile, id=profile_id)
        
        deleted_count = unfollow_profile(from_profile, to_profile)
        if deleted_count > 0:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"detail": "No seguías a este perfil."}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    tags=['Relationships'],
    summary="Listar mis seguidores (followers)",
    description="Devuelve una lista de los perfiles que siguen al usuario autenticado."
)
class FollowersListView(generics.ListAPIView):
    """
    Vista para listar los seguidores del usuario autenticado.
    """
    serializer_class = FollowerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_profile = self.request.user.profile
        # Usamos el related_name 'follower_relationships' del modelo Follow
        # para encontrar todas las relaciones donde el usuario es el 'to_profile'.
        # Luego, obtenemos los perfiles que iniciaron ese seguimiento ('from_profile').
        return Profile.objects.filter(following_relationships__to_profile=user_profile)


@extend_schema(
    tags=['Relationships'],
    summary="Listar perfiles que sigo (following)",
    description="Devuelve una lista de los perfiles a los que sigue el usuario autenticado."
)
class FollowingListView(generics.ListAPIView):
    """
    Vista para listar los perfiles que el usuario autenticado está siguiendo.
    """
    serializer_class = FollowerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_profile = self.request.user.profile
        # Usamos el related_name 'following_relationships' del modelo Follow
        # para encontrar todas las relaciones donde el usuario es el 'from_profile'.
        # Luego, obtenemos los perfiles que están siendo seguidos ('to_profile').
        return Profile.objects.filter(follower_relationships__from_profile=user_profile)


@extend_schema(
    tags=['Relationships'],
    summary="Listar mis amigos (seguimiento mutuo)",
    description="Devuelve una lista de perfiles con los que existe una relación de seguimiento mutua."
)
class FriendsListView(generics.ListAPIView):
    """
    Vista para listar 'amigos', es decir, perfiles donde el seguimiento es mutuo.
    """
    serializer_class = FollowerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_profile = self.request.user.profile
        # 1. Obtiene los IDs de los perfiles que el usuario actual sigue.
        following_ids = user_profile.following_relationships.values_list('to_profile_id', flat=True)
        # 2. Filtra los seguidores del usuario actual para encontrar solo aquellos que también están en la lista de 'seguidos'.
        # Esto nos da la intersección, es decir, los amigos.
        return Profile.objects.filter(following_relationships__to_profile=user_profile, id__in=following_ids)
