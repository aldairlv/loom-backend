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


class RelationshipsFeedResponseMixin:
    """Mixin para estandarizar la respuesta de las vistas de lista de relaciones."""

    def build_feed_response(self, serializer_data):
        cursor = self.request.query_params.get('cursor')
        return Response({
            "meta": {"status": 200, "msg": "OK"},
            "response": {
                "feed": {
                    "elements": serializer_data,
                    "queryParams": {"cursor": cursor}
                }
            }
        }, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
        else:
            serializer = self.get_serializer(queryset, many=True)

        return self.build_feed_response(serializer.data)


@extend_schema(
    tags=['Relationships'],
    summary="Listar mis seguidores (followers)",
    description="Devuelve una lista de los perfiles que siguen al usuario autenticado."
)
class FollowersListView(RelationshipsFeedResponseMixin, generics.ListAPIView):
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
class FollowingListView(RelationshipsFeedResponseMixin, generics.ListAPIView):
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
class FriendsListView(RelationshipsFeedResponseMixin, generics.ListAPIView):
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


# ============================================================================
# NUEVAS VISTAS CON MEJOR SEMÁNTICA (endpoints /me/ y /users/{id}/)
# Reutilizan los mismos servicios que los endpoints legacy en /relationships/
# ============================================================================


@extend_schema(
    tags=['Me - Following'],
    summary="Listar mis seguidores",
    description="Devuelve la lista de usuarios que me siguen a mí.",
    deprecated=False
)
class MeFollowersView(RelationshipsFeedResponseMixin, generics.ListAPIView):
    """
    GET /api/v1/me/followers
    Lista los seguidores del usuario autenticado.
    """
    serializer_class = FollowerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_profile = self.request.user.profile
        return Profile.objects.filter(following_relationships__to_profile=user_profile)


@extend_schema(
    tags=['Me - Following'],
    summary="Listar mis seguidos",
    description="Devuelve la lista de usuarios a los que yo sigo.",
    deprecated=False
)
class MeFollowingView(RelationshipsFeedResponseMixin, generics.ListAPIView):
    """
    GET /api/v1/me/following
    Lista los perfiles que el usuario autenticado está siguiendo.
    """
    serializer_class = FollowerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_profile = self.request.user.profile
        return Profile.objects.filter(follower_relationships__from_profile=user_profile)


@extend_schema(
    tags=['Me - Following'],
    summary="Listar mis amigos",
    description="Devuelve la lista de usuarios con los que existe seguimiento mutuo.",
    deprecated=False
)
class MeFriendsView(RelationshipsFeedResponseMixin, generics.ListAPIView):
    """
    GET /api/v1/me/friends
    Lista los 'amigos' del usuario autenticado (seguimiento mutuo).
    """
    serializer_class = FollowerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_profile = self.request.user.profile
        following_ids = user_profile.following_relationships.values_list('to_profile_id', flat=True)
        return Profile.objects.filter(following_relationships__to_profile=user_profile, id__in=following_ids)


@extend_schema(
    tags=['Users - Followers'],
    summary="Seguir o dejar de seguir un usuario",
    description="POST: Añade al usuario autenticado a la lista de seguidores del usuario especificado. DELETE: Elimina al usuario autenticado de la lista de seguidores del usuario especificado.",
    parameters=[
        OpenApiParameter(name='user_id', description='El ID del usuario a seguir/dejar de seguir', required=True, type=str, location=OpenApiParameter.PATH)
    ]
)
class UserFollowersView(APIView):
    """
    POST /api/v1/users/{user_id}/followers - Seguir a un usuario
    DELETE /api/v1/users/{user_id}/followers - Dejar de seguir a un usuario
    Maneja ambas acciones en una sola vista.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """Crear un seguimiento: POST /api/v1/users/{user_id}/followers"""
        user_id = kwargs.get('user_id')
        try:
            to_profile = Profile.objects.get(id=user_id)
        except Profile.DoesNotExist:
            return Response(
                {"detail": f"Usuario con ID {user_id} no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        from_profile = request.user.profile
        
        try:
            follow, created = follow_profile(from_profile, to_profile)
            if not created:
                return Response(
                    {"detail": "Ya sigues a este usuario."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = FollowSerializer(follow)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        """Eliminar un seguimiento: DELETE /api/v1/users/{user_id}/followers"""
        user_id = kwargs.get('user_id')
        try:
            to_profile = Profile.objects.get(id=user_id)
        except Profile.DoesNotExist:
            return Response(
                {"detail": f"Usuario con ID {user_id} no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        from_profile = request.user.profile
        deleted_count = unfollow_profile(from_profile, to_profile)
        
        if deleted_count > 0:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {"detail": "No seguías a este usuario."},
            status=status.HTTP_404_NOT_FOUND
        )
