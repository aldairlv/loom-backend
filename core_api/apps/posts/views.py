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
from interactions.serializers import LikeSerializer, PostCommentSerializer
from interactions.models import PostComment as InteractionPostComment
from . import services
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from django.shortcuts import get_object_or_404
from django.conf import settings


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

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"}
                },
                "required": ["text"]
            }
        },
        examples=[
            OpenApiExample(
                'Create post comment',
                value={"text": "nice post"},
                request_only=True,
            )
        ],
    )
    @action(detail=True, methods=['get', 'post'], url_path='comments', permission_classes=[IsAuthenticated])
    def comments(self, request, pk=None):
        """GET: Lista los comentarios raíz de un post (con sus replies).
        POST: Crear un comentario directamente sobre el post (sin parent)."""
        post = self.get_object()

        if request.method == 'GET':
            # Soporte para incluir comentarios eliminados vía query param
            include_deleted = request.query_params.get('include_deleted')
            if include_deleted and include_deleted.lower() in ('1', 'true', 'yes'):
                base_qs = interaction_services.get_post_comments_for_post(post, include_deleted=True).filter(parent__isnull=True)
            else:
                base_qs = interaction_services.get_root_post_comments_for_post(post)

            # Orden estable por fecha y id
            queryset = base_qs.order_by('created_at', 'id')

            # Cursor-based offset pagination (simple): cursor is an integer offset.
            # If the client sends cursor=null (or no cursor), treat as first page / reload.
            raw_cursor = request.query_params.get('cursor')
            if raw_cursor is None or str(raw_cursor).lower() in ('null', 'none', ''):
                offset = 0
            else:
                try:
                    offset = int(raw_cursor)
                    if offset < 0:
                        offset = 0
                except Exception:
                    offset = 0

            page_size = getattr(settings, 'COMMENTS_PAGE_SIZE', 10)

            # Fetch one extra to know if there is a next page
            items = list(queryset[offset: offset + page_size + 1])
            has_more = len(items) > page_size
            page_items = items[:page_size]

            serializer = PostCommentSerializer(page_items, many=True, context=self.get_serializer_context())

            next_cursor = (offset + page_size) if has_more else None

            # Build meta like other responses
            request_user = request
            user_id = None
            if request_user and hasattr(request_user, 'user') and request_user.user.is_authenticated:
                try:
                    user_id = str(request_user.user.id)
                except Exception:
                    user_id = None

            response_body = {
                "meta": {"status": 200, "msg": "OK", "xRoomUserId": user_id},
                "response": {
                    "comments": {
                        "elements": serializer.data,
                        "queryParams": {"cursor": next_cursor}
                    }
                }
            }

            return Response(response_body)

        # POST -> crear comentario raíz
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response({"detail": "El usuario no tiene un perfil."}, status=status.HTTP_400_BAD_REQUEST)

        text = request.data.get('text')
        if text is None:
            return Response({"text": "Este campo es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        comment = interaction_services.create_post_comment(
            profile=profile,
            post=post,
            text=text,
            parent=None
        )

        output_serializer = PostCommentSerializer(comment, context=self.get_serializer_context())
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post', 'delete'], url_path=r'comments/(?P<comment_id>[^/.]+)', permission_classes=[IsAuthenticated])
    def comment_detail(self, request, pk=None, comment_id=None):
        """Crear una respuesta a un comentario o eliminar un comentario específico."""
        post = self.get_object()
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response({"detail": "El usuario no tiene un perfil."}, status=status.HTTP_400_BAD_REQUEST)

        # Obtener comentario padre/objetivo
        parent_comment = get_object_or_404(InteractionPostComment, pk=comment_id)
        if parent_comment.post_id != post.id:
            return Response({"detail": "El comentario especificado no pertenece a este post."}, status=status.HTTP_400_BAD_REQUEST)

        if request.method == 'POST':
            text = request.data.get('text')
            if text is None:
                return Response({"text": "Este campo es requerido."}, status=status.HTTP_400_BAD_REQUEST)

            comment = interaction_services.create_post_comment(
                profile=profile,
                post=post,
                text=text,
                parent=parent_comment
            )

            output_serializer = PostCommentSerializer(comment, context=self.get_serializer_context())
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)

        # DELETE
        interaction_services.delete_post_comment(parent_comment, soft_delete=True)
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