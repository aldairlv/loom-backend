from rest_framework import serializers

from .models import Like, PostComment, EventComment, Bookmark
from profiles.models import Profile
from posts.models import Post
from events.models import Event


class LikeSerializer(serializers.ModelSerializer):
    profile = serializers.PrimaryKeyRelatedField(read_only=True)
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all())

    class Meta:
        model = Like
        fields = ['id', 'profile', 'post', 'created_at']
        read_only_fields = ['id', 'profile', 'created_at']


class BaseCommentSerializer(serializers.ModelSerializer):
    profile = serializers.PrimaryKeyRelatedField(read_only=True)
    root = serializers.PrimaryKeyRelatedField(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        fields = ['id', 'profile', 'parent', 'root', 'text', 'depth', 'created_at', 'updated_at', 'is_deleted', 'replies']
        read_only_fields = ['id', 'profile', 'root', 'created_at', 'updated_at', 'depth', 'is_deleted']

    def get_replies(self, obj):
        """Obtiene las respuestas directas a este comentario (no recursivo)"""
        if obj.replies.exists():
            return self.__class__(obj.replies.all(), many=True).data
        return []


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
