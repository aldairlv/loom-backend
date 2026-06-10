from rest_framework import serializers

from posts.models import Tag
from profiles.models import Profile


class UserAutocompleteSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.SerializerMethodField()
    match_type = serializers.CharField(read_only=True)

    class Meta:
        model = Profile
        fields = ['id', 'username', 'display_name', 'avatar', 'match_type']

    def get_avatar(self, obj):
        request = self.context.get('request')
        url = obj.get_avatar_url
        if request and url:
            return request.build_absolute_uri(url)
        return url


class TagAutocompleteSerializer(serializers.ModelSerializer):
    post_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tag
        fields = ['id', 'name', 'post_count']


def _absolute_url(request, url):
    if not url:
        return None
    if request:
        return request.build_absolute_uri(url)
    return url


def _author_block(source, request):
    username = source.get('author_username') or source.get('username')
    avatar_key = 'author_avatar' if 'author_username' in source else 'avatar'
    return {
        'username': username,
        'avatar': _absolute_url(request, source.get(avatar_key)),
    }


def format_post_result(hit, request=None):
    source = hit if 'doc_type' in hit else hit
    body = source.get('body', '')
    username = source.get('author_username', '')
    return {
        'id': str(source.get('id', hit.get('_id', ''))),
        'type': 'post',
        'content_type': source.get('content_type'),
        'title': f'Post de @{username}' if username else 'Post',
        'body': body[:280] if body else '',
        'media_url': _absolute_url(request, source.get('media_url')) or None,
        'tags': source.get('tags', []),
        'author': _author_block(source, request),
        'created_at': source.get('created_at'),
    }


def format_event_result(hit, request=None):
    source = hit if 'doc_type' in hit else hit
    return {
        'id': str(source.get('id', hit.get('_id', ''))),
        'type': 'event',
        'content_type': None,
        'title': source.get('title', ''),
        'body': (source.get('body') or '')[:280],
        'media_url': _absolute_url(request, source.get('media_url')) or None,
        'tags': source.get('tags', []),
        'author': _author_block(source, request),
        'location': {
            'name': source.get('location_name'),
            'coordinates': source.get('location'),
        },
        'date': source.get('start_time'),
        'category': source.get('category'),
    }


def format_user_result(hit, request=None):
    source = hit if 'doc_type' in hit else hit
    return {
        'id': str(source.get('id', hit.get('_id', ''))),
        'type': 'user',
        'content_type': None,
        'title': source.get('display_name', ''),
        'body': (source.get('bio') or '')[:280],
        'media_url': None,
        'tags': [],
        'author': {
            'username': source.get('username'),
            'avatar': _absolute_url(request, source.get('avatar')),
        },
        'city': source.get('city'),
    }


def format_search_hit(hit, request=None):
    doc_type = hit.get('doc_type')
    if doc_type == 'posts':
        return format_post_result(hit, request)
    if doc_type == 'events':
        return format_event_result(hit, request)
    if doc_type == 'users':
        return format_user_result(hit, request)
    return None
