from django.contrib.postgres.search import TrigramSimilarity
from django.core.cache import cache
from django.db.models import Count
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from posts.models import Tag
from profiles.models import Profile

from .filters import search_explore
from .serializers import (
    TagAutocompleteSerializer,
    UserAutocompleteSerializer,
    format_search_hit,
)

AUTOCOMPLETE_MIN_LENGTH = 2
AUTOCOMPLETE_CACHE_TTL = 60
USERNAME_MATCH_LIMIT = 6
DISPLAY_NAME_MATCH_LIMIT = 3
TAG_MATCH_LIMIT = 5
SIMILARITY_THRESHOLD = 0.15


class AutocompleteView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        empty = {'users': [], 'tags': []}
        if len(q) < AUTOCOMPLETE_MIN_LENGTH:
            return Response(empty)

        cache_key = f'autocomplete:{q.lower()}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        users_by_username = list(
            Profile.objects.select_related('user')
            .annotate(sim=TrigramSimilarity('user__username', q))
            .filter(sim__gt=SIMILARITY_THRESHOLD)
            .order_by('-sim')[:USERNAME_MATCH_LIMIT]
        )
        for profile in users_by_username:
            profile.match_type = 'username'

        found_ids = [p.id for p in users_by_username]
        remaining_slots = max(USERNAME_MATCH_LIMIT - len(users_by_username), 0)

        users_by_display = []
        if remaining_slots:
            users_by_display = list(
                Profile.objects.select_related('user')
                .annotate(sim=TrigramSimilarity('display_name', q))
                .filter(sim__gt=SIMILARITY_THRESHOLD)
                .exclude(id__in=found_ids)
                .order_by('-sim')[: min(remaining_slots, DISPLAY_NAME_MATCH_LIMIT)]
            )
            for profile in users_by_display:
                profile.match_type = 'display_name'

        users = users_by_username + users_by_display

        tags = (
            Tag.objects.annotate(
                sim=TrigramSimilarity('name', q),
                post_count=Count('posts', distinct=True),
            )
            .filter(sim__gt=SIMILARITY_THRESHOLD)
            .order_by('-sim', '-post_count')[:TAG_MATCH_LIMIT]
        )

        result = {
            'users': UserAutocompleteSerializer(
                users, many=True, context={'request': request}
            ).data,
            'tags': TagAutocompleteSerializer(tags, many=True).data,
        }
        cache.set(cache_key, result, timeout=AUTOCOMPLETE_CACHE_TTL)
        return Response(result)


class ExploreSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        type_param = request.query_params.get('type')
        if type_param in ('posts', 'events', 'users'):
            search_type = type_param
        else:
            search_type = None

        content_type = request.query_params.get('content_type')
        if content_type and content_type not in ('text', 'image', 'video', 'audio'):
            content_type = None

        try:
            page = max(int(request.query_params.get('page', 1)), 1)
        except (TypeError, ValueError):
            page = 1

        try:
            limit = min(max(int(request.query_params.get('limit', 20)), 1), 50)
        except (TypeError, ValueError):
            limit = 20

        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')

        hits, facets, total = search_explore(
            query=q,
            type_=search_type,
            page=page,
            limit=limit,
            content_type=content_type,
            lat=lat,
            lon=lon,
        )

        results = [
            formatted
            for hit in hits
            if (formatted := format_search_hit(hit, request=request))
        ]

        return Response({
            'meta': {
                'query': q,
                'type': search_type,
                'page': page,
                'limit': limit,
                'total_results': total,
                'facets': facets,
            },
            'results': results,
            'next_page': page + 1 if (page * limit) < total else None,
        })
