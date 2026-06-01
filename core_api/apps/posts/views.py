from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from profiles.models import Profile
from .models import Post, Tag, PostStatus
from interactions.models import Like
from interactions import services as interaction_services
from .serializers import PostSerializer, TagSerializer, PostCreateSerializer
from .tasks import indexar_post_task
from interactions.serializers import LikeSerializer
from . import services
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.shortcuts import get_object_or_404


class PostCursorPagination(CursorPagination):
    page_size = 10
    ordering = ('-created_at', '-id')


class PostViewSet(viewsets.ModelViewSet):
    pagination_class = PostCursorPagination
    
    def get_queryset(self):
        # Filtramos solo los que no están eliminados
        return Post.objects.filter(is_deleted=False).select_related('author', 'parent__author').prefetch_related('tags', 'contents__media', 'likes')

    def get_serializer_class(self):
        if self.action == 'create':
            return PostCreateSerializer
        return PostSerializer

    def create(self, request, *args, **kwargs):
        # Usamos PostCreateSerializer que valida el formato polimórfico de 'contents_input'
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Obtenemos el perfil del usuario que hace la petición.
        try:
            author_profile = request.user.profile
        except Profile.DoesNotExist: # Se produce si el usuario no tiene perfil por alguna razón
            return Response({"error": "El usuario no tiene un perfil por defecto."}, status=status.HTTP_400_BAD_REQUEST)

        # 'contents' ahora viene de 'contents_input' en validated_data
        contents_data = serializer.validated_data.pop('contents', [])
        
        post = services.create_post(
            author=author_profile,
            data=serializer.validated_data, # Contiene status, parent, root, tags, layout...
            contents_data=contents_data
        )

        # Actualizamos la fecha del último post del perfil del autor
        author_profile.last_posted_at = timezone.now()
        author_profile.save()
        
        indexar_post_task.apply_async(args=[post.id], ignore_result=True)
        # Devolvemos el post usando el serializer de lectura (PostSerializer)
        return Response(PostSerializer(post, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        post = self.get_object()
        serializer = self.get_serializer(post, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        updated_post = services.update_post(post, serializer.validated_data)
        return Response(PostSerializer(updated_post).data)

    def destroy(self, request, *args, **kwargs):
        post = self.get_object()
        services.delete_post(post)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='cursor', description='El cursor para la paginación de la siguiente página.', type=str),
        ]
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='following')
    def following_feed(self, request, *args, **kwargs):
        """
        Devuelve un feed con los posts de los perfiles que el usuario actual sigue.
        Los resultados están ordenados por fecha de creación descendente.
        """
        try:
            user_profile = request.user.profile
        except Profile.DoesNotExist:
            return Response({"error": "El usuario actual no tiene un perfil."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Obtener los IDs de los perfiles que el usuario sigue.
        following_profile_ids = user_profile.following_relationships.values_list('to_profile_id', flat=True)

        # 2. Filtrar los posts de esos perfiles.

        queryset = self.get_queryset().filter(
            author_id__in=following_profile_ids
        ).order_by('-created_at', '-id') # Ordenar por fecha y desempatar por id

        # 3. Paginar y serializar los resultados
        page = self.paginate_queryset(queryset)
        serializer_data = []
        cursor = None

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serializer_data = serializer.data
            next_link = self.paginator.get_next_link()
            if next_link:
                cursor = next_link.split('cursor=')[-1]
        else:
            serializer = self.get_serializer(queryset, many=True)
            serializer_data = serializer.data

        return Response({
            "meta": {"status": 200, "msg": "OK"},
            "response": {
                "feed": {
                    "elements": serializer_data,
                    "queryParams": {"cursor": cursor}
                }
            }
        })
    @extend_schema(
        parameters=[
            OpenApiParameter(name='cursor', description='El cursor para la paginación de la siguiente página.', type=str),
        ]
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='tags')
    def tags_feed(self, request, *args, **kwargs):
        """
        Devuelve un feed con los posts de los perfiles que el usuario actual sigue.
        Los resultados están ordenados por fecha de creación descendente.
        """
        try:
            user_profile = request.user.profile
        except Profile.DoesNotExist:
            return Response({"error": "El usuario actual no tiene un perfil."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Obtener los tags que el usuario sigue.
        followed_tags = user_profile.followed_tags.all()
        if not followed_tags.exists():
            return Response({
                "meta": {"status": 200, "msg": "OK"},
                "response": {
                    "feed": {
                        "elements": [],
                        "queryParams": {"cursor": None},
                        "message": "No sigues ningún tag."
                    }
                }
            })

        # 2. Filtrar los posts que contienen cualquiera de esos tags.
        queryset = self.get_queryset().filter(
            tags__in=followed_tags
        ).distinct().order_by('-created_at', '-id')

        page = self.paginate_queryset(queryset)
        serializer_data = []
        cursor = None

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serializer_data = serializer.data
            next_link = self.paginator.get_next_link()
            if next_link:
                cursor = next_link.split('cursor=')[-1]
        else:
            serializer = self.get_serializer(queryset, many=True)
            serializer_data = serializer.data

        return Response({
            "meta": {"status": 200, "msg": "OK"},
            "response": {
                "feed": {
                    "elements": serializer_data,
                    "queryParams": {"cursor": cursor}
                }
            }
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='cursor', description='El cursor para la paginación de la siguiente página.', type=str),
        ]
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='recommend')
    def recommend_feed(self, request, *args, **kwargs):
        """
        Devuelve un feed de recomendación con todos los posts publicados.
        Los resultados están ordenados por fecha de creación descendente y paginados por cursor.
        """
        queryset = self.get_queryset().filter(
            status=PostStatus.PUBLISHED
        ).order_by('-created_at', '-id')

        page = self.paginate_queryset(queryset)
        serializer_data = []
        cursor = None

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serializer_data = serializer.data
            next_link = self.paginator.get_next_link()
            if next_link:
                cursor = next_link.split('cursor=')[-1]
        else:
            serializer = self.get_serializer(queryset, many=True)
            serializer_data = serializer.data

        return Response({
            "meta": {"status": 200, "msg": "OK"},
            "response": {
                "feed": {
                    "elements": serializer_data,
                    "queryParams": {"cursor": cursor}
                }
            }
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='cursor', description='El cursor para la paginación de la siguiente página.', type=str),
        ]
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='liked')
    def liked_posts(self, request, *args, **kwargs):
        """
        Devuelve un feed con los posts a los que el usuario autenticado ha dado "like".
        Los resultados están ordenados por fecha de creación descendente y paginados por cursor.
        """
        try:
            user_profile = request.user.profile
        except Profile.DoesNotExist:
            return Response({"error": "El usuario actual no tiene un perfil."}, status=status.HTTP_400_BAD_REQUEST)

        # Filtra los posts basándose en el modelo 'Like' de la app 'interactions'.
        # El related_name en el modelo Like es 'likes'.
        queryset = self.get_queryset().filter(
            likes__profile=user_profile
        ).order_by('-created_at', '-id')

        page = self.paginate_queryset(queryset)
        serializer_data = []
        cursor = None

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serializer_data = serializer.data
            next_link = self.paginator.get_next_link()
            if next_link:
                cursor = next_link.split('cursor=')[-1]
        else:
            serializer = self.get_serializer(queryset, many=True)
            serializer_data = serializer.data

        return Response({
            "meta": {"status": 200, "msg": "OK"},
            "response": {
                "feed": {
                    "elements": serializer_data,
                    "queryParams": {"cursor": cursor}
                }
            }
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(name='cursor', description='El cursor para la paginación de la siguiente página.', type=str),
        ]
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='me')
    def my_posts(self, request, *args, **kwargs):
        """
        Devuelve un feed con los posts del usuario autenticado.
        Los resultados están ordenados por fecha de creación descendente y paginados por cursor.
        """
        try:
            user_profile = request.user.profile
        except Profile.DoesNotExist:
            return Response({"error": "El usuario actual no tiene un perfil."}, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset().filter(
            author=user_profile
        ).order_by('-created_at', '-id')

        page = self.paginate_queryset(queryset)
        serializer_data = []
        cursor = None

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            serializer_data = serializer.data
            next_link = self.paginator.get_next_link()
            if next_link:
                cursor = next_link.split('cursor=')[-1]
        else:
            # Fallback por si la paginación no está activa
            serializer = self.get_serializer(queryset, many=True)
            serializer_data = serializer.data

        return Response({
            "meta": {"status": 200, "msg": "OK"},
            "response": {
                "feed": {
                    "elements": serializer_data,
                    "queryParams": {
                        "cursor": cursor
                    }
                }
            }
        })

    @extend_schema(
        summary="Gestionar 'Like' en un Post",
        description="Crea o elimina una relación 'Like' entre el usuario autenticado y un post. `POST` para dar like, `DELETE` para quitarlo.",
        request=None,
        responses={
            '201': LikeSerializer,
            '200': LikeSerializer,
            '204': {"description": "Like eliminado con éxito."}
        },
        tags=['Interactions']
    )
    @action(detail=True, methods=['post', 'delete'], url_path='likes', permission_classes=[IsAuthenticated])
    def likes(self, request, pk=None):
        """
        Gestiona los 'likes' de un post.
        - POST: Da 'like' a un post. Es idempotente.
        - DELETE: Quita el 'like' de un post.
        """
        post = self.get_object()
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response({"detail": "El usuario no tiene un perfil."}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'POST':
            like, created = interaction_services.create_like(profile=profile, post=post)
            serializer = LikeSerializer(like)
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            return Response(serializer.data, status=status_code)

        like = get_object_or_404(Like, profile=profile, post=post)
        interaction_services.delete_like(like)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def follow(self, request, pk=None):
        tag = self.get_object()
        request.user.profile.followed_tags.add(tag)
        return Response({'status': 'tag followed'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def unfollow(self, request, pk=None):
        tag = self.get_object()
        request.user.profile.followed_tags.remove(tag)
        return Response({'status': 'tag unfollowed'}, status=status.HTTP_200_OK)