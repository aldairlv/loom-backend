from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from profiles.models import Profile
from events.models import Event
from .models import Like, PostComment, EventComment, Bookmark
from .serializers import LikeSerializer, PostCommentSerializer, EventCommentSerializer, BookmarkSerializer
from . import services


class LikeViewSet(viewsets.ModelViewSet):
    serializer_class = LikeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            profile = self.request.user.profiles.get(is_default=True)
        except Profile.DoesNotExist:
            return Like.objects.none()

        queryset = services.get_likes_for_profile(profile)
        post_id = self.request.query_params.get('post_id')
        if post_id:
            queryset = queryset.filter(post_id=post_id)
        return queryset

    def create(self, request, *args, **kwargs):
        try:
            profile = request.user.profiles.get(is_default=True)
        except Profile.DoesNotExist:
            raise ValidationError({
                'profile': 'El usuario no tiene un perfil por defecto.'
            })

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        post = serializer.validated_data['post']
        like, created = services.create_like(profile=profile, post=post)
        if not created:
            raise ValidationError({
                'detail': 'Ya existe un like para este post.'
            })

        output_serializer = self.get_serializer(like)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        like = self.get_object()
        services.delete_like(like)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostCommentViewSet(viewsets.ModelViewSet):
    serializer_class = PostCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = services.get_post_comments_queryset().filter(is_deleted=False)
        
        # Filtrar por post si se proporciona post_id
        post_id = self.request.query_params.get('post_id')
        if post_id:
            queryset = queryset.filter(post_id=post_id)
        
        # Filtrar solo comentarios raíz (parent=None) si se especifica
        root_only = self.request.query_params.get('root_only')
        if root_only:
            queryset = queryset.filter(parent__isnull=True)
        
        return queryset

    def create(self, request, *args, **kwargs):
        try:
            profile = request.user.profiles.get(is_default=True)
        except Profile.DoesNotExist:
            raise ValidationError({
                'profile': 'El usuario no tiene un perfil por defecto.'
            })

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        post = serializer.validated_data['post']
        text = serializer.validated_data['text']
        parent = serializer.validated_data.get('parent')

        # Validar que si hay parent, pertenece al mismo post
        if parent and parent.post_id != post.id:
            raise ValidationError({
                'parent': 'El comentario padre debe pertenecer al mismo post.'
            })

        comment = services.create_post_comment(
            profile=profile,
            post=post,
            text=text,
            parent=parent
        )

        output_serializer = self.get_serializer(comment)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        comment = self.get_object()
        serializer = self.get_serializer(comment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data.get('text')
        if text:
            comment = services.update_post_comment(comment, text)

        output_serializer = self.get_serializer(comment)
        return Response(output_serializer.data)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        services.delete_post_comment(comment, soft_delete=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EventCommentViewSet(viewsets.ModelViewSet):
    serializer_class = EventCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = services.get_event_comments_queryset().filter(is_deleted=False)
        
        # Filtrar por event si se proporciona event_id
        event_id = self.request.query_params.get('event_id')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        
        # Filtrar solo comentarios raíz (parent=None) si se especifica
        root_only = self.request.query_params.get('root_only')
        if root_only:
            queryset = queryset.filter(parent__isnull=True)
        
        return queryset

    def create(self, request, *args, **kwargs):
        try:
            profile = request.user.profiles.get(is_default=True)
        except Profile.DoesNotExist:
            raise ValidationError({
                'profile': 'El usuario no tiene un perfil por defecto.'
            })

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = serializer.validated_data['event']
        text = serializer.validated_data['text']
        parent = serializer.validated_data.get('parent')

        # Validar que si hay parent, pertenece al mismo event
        if parent and parent.event_id != event.id:
            raise ValidationError({
                'parent': 'El comentario padre debe pertenecer al mismo evento.'
            })

        comment = services.create_event_comment(
            profile=profile,
            event=event,
            text=text,
            parent=parent
        )

        output_serializer = self.get_serializer(comment)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        comment = self.get_object()
        serializer = self.get_serializer(comment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data.get('text')
        if text:
            comment = services.update_event_comment(comment, text)

        output_serializer = self.get_serializer(comment)
        return Response(output_serializer.data)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        services.delete_event_comment(comment, soft_delete=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class BookmarkViewSet(viewsets.ModelViewSet):
    serializer_class = BookmarkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            profile = self.request.user.profiles.get(is_default=True)
        except Profile.DoesNotExist:
            return Bookmark.objects.none()

        queryset = services.get_bookmarks_for_profile(profile)
        event_id = self.request.query_params.get('event_id')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        return queryset

    def create(self, request, *args, **kwargs):
        try:
            profile = request.user.profiles.get(is_default=True)
        except Profile.DoesNotExist:
            raise ValidationError({
                'profile': 'El usuario no tiene un perfil por defecto.'
            })

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = serializer.validated_data['event']
        bookmark, created = services.create_bookmark(profile=profile, event=event)
        if not created:
            raise ValidationError({
                'detail': 'Ya existe un bookmark para este evento.'
            })

        output_serializer = self.get_serializer(bookmark)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        bookmark = self.get_object()
        services.delete_bookmark(bookmark)
        return Response(status=status.HTTP_204_NO_CONTENT)
