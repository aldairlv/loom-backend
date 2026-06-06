from rest_framework import serializers

from .models import Notification, UserDevice
from interactions.models import Like, PostComment, EventComment
from interactions.serializers import LikeSerializer, PostCommentSerializer, EventCommentSerializer
from relationships.models import Follow
from relationships.serializers import FollowSerializer
from profiles.models import Profile
from profiles.serializers import ProfileSerializer
from posts.serializers import PostAuthorSerializer, PostContentSerializer


class NotificationSerializer(serializers.ModelSerializer):
    content_type = serializers.CharField(source='content_type.model', read_only=True)
    target_id = serializers.UUIDField(source='object_id', read_only=True)
    target_data = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'event_type',
            'is_read',
            'created_at',
            'content_type',
            'target_id',
            'target_data',
        ]
        read_only_fields = fields

    def get_target_data(self, obj):
        target = obj.target_object
        if target is None:
            return None

        if isinstance(target, Like):
            post = target.post
            # Get root post if it exists, otherwise use the post itself
            root_post = post.root if post.root else post
            return {
                'id': str(target.id),
                'author': PostAuthorSerializer(target.profile, context=self.context).data,
                'post': {
                    'id': str(post.id),
                    'content_data': PostContentSerializer(root_post.contents.all(), many=True, context=self.context).data,
                },
            }

        if isinstance(target, PostComment):
            return PostCommentSerializer(target, context=self.context).data

        if isinstance(target, EventComment):
            return EventCommentSerializer(target, context=self.context).data

        if isinstance(target, Follow):
            return FollowSerializer(target, context=self.context).data

        if isinstance(target, Profile):
            return ProfileSerializer(target, context=self.context).data

        return {
            'id': str(obj.object_id),
            'type': obj.content_type.model,
        }


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = [
            'id',
            'device_id',
            'registration_token',
            'device_type',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
