from rest_framework import serializers

from .models import Like, PostComment, EventComment, Bookmark
from profiles.models import Profile
from posts.models import Post
from events.models import Event
from relationships.models import Follow


class LikeSerializer(serializers.ModelSerializer):
    profile = serializers.PrimaryKeyRelatedField(read_only=True)
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all())

    class Meta:
        model = Like
        fields = ['id', 'profile', 'post', 'created_at']
        read_only_fields = ['id', 'profile', 'created_at']


class CommentAuthorSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    is_followed = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['id', 'display_name', 'avatar_url', 'is_followed']

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if request and obj.get_avatar_url:
            return request.build_absolute_uri(obj.get_avatar_url)
        return obj.get_avatar_url

    def get_is_followed(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user') or request.user.is_anonymous:
            return False
        try:
            from_profile = request.user.profile
        except Exception:
            return False
        return Follow.objects.filter(from_profile=from_profile, to_profile=obj).exists()


class BaseCommentSerializer(serializers.ModelSerializer):
    author = CommentAuthorSerializer(read_only=True, source='profile')
    root = serializers.PrimaryKeyRelatedField(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        fields = ['id', 'author', 'parent', 'root', 'text', 'depth', 'created_at', 'updated_at', 'is_deleted', 'replies']
        read_only_fields = ['id', 'author', 'root', 'created_at', 'updated_at', 'depth', 'is_deleted']

    def get_replies(self, obj):
        """Obtiene las respuestas directas a este comentario (no recursivo)"""
        if obj.replies.exists():
            return self.__class__(obj.replies.all(), many=True, context=self.context).data
        return []

    def to_representation(self, instance):
        """Reemplaza el texto cuando el comentario está marcado como eliminado,
        pero mantiene las respuestas (replies) intactas y visibles."""
        data = super().to_representation(instance)
        try:
            is_deleted = getattr(instance, 'is_deleted', False)
        except Exception:
            is_deleted = False
        if is_deleted:
            data['text'] = "[Este comentario ha sido eliminado]"
        return data


class PostCommentSerializer(BaseCommentSerializer):
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all())
    parent = serializers.PrimaryKeyRelatedField(
        queryset=PostComment.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta(BaseCommentSerializer.Meta):
        model = PostComment
        fields = BaseCommentSerializer.Meta.fields + ['post']


class EventCommentSerializer(BaseCommentSerializer):
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())
    parent = serializers.PrimaryKeyRelatedField(
        queryset=EventComment.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta(BaseCommentSerializer.Meta):
        model = EventComment
        fields = BaseCommentSerializer.Meta.fields + ['event']


class BookmarkSerializer(serializers.ModelSerializer):
    profile = serializers.PrimaryKeyRelatedField(read_only=True)
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())

    class Meta:
        model = Bookmark
        fields = ['id', 'profile', 'event', 'created_at']
        read_only_fields = ['id', 'profile', 'created_at']
