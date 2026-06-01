# posts/services.py
import os
import json
import logging
import threading
import time
import requests
from redis import Redis
from redis.exceptions import ResponseError
from posts.models import Post, PostStatus
from posts.serializers import PostSerializer

logger = logging.getLogger(__name__)

class FeedService:
    RECOMMENDATION_SERVICE_URL = os.environ.get(
        'RECOMMENDATION_SERVICE_URL',
        'http://recommendation_service:8080/api/v1'
    )
    USER_FEED_ZSET_KEY = 'feed:for_you:{user_id}'
    BLOOM_ACTUAL_KEY = 'feed:for_you:{user_id}:bf:actual'
    BLOOM_PAST_KEY = 'feed:for_you:{user_id}:bf:past'
    BLOOM_ROTATION_KEY = 'feed:for_you:{user_id}:bf:rotation'
    POST_CACHE_KEY = 'post:{post_id}'
    POST_CACHE_TTL = int(os.environ.get('POST_CACHE_TTL_SECONDS', 60 * 60 * 6))
    MAX_RECOMMENDATIONS = int(os.environ.get('MAX_RECOMMENDATIONS', 150))
    MIN_FEED_BUFFER_THRESHOLD = int(os.environ.get('MIN_FEED_BUFFER_THRESHOLD', 20))
    FEED_REFILL_TARGET = int(os.environ.get('FEED_REFILL_TARGET', 100))
    FEED_FETCH_BATCH = int(os.environ.get('FEED_FETCH_BATCH', 100))
    BLOOM_ERROR_RATE = float(os.environ.get('BLOOM_ERROR_RATE', 0.001))
    BLOOM_CAPACITY = int(os.environ.get('BLOOM_CAPACITY', 100000))
    CAROUSEL_COOLDOWN_SECONDS = int(os.environ.get('CAROUSEL_COOLDOWN_SECONDS', 10 * 60))
    CAROUSEL_EXPIRE_SECONDS = int(os.environ.get('CAROUSEL_EXPIRE_SECONDS', 2 * 24 * 60 * 60))
    REDIS_URL = os.environ.get('REDIS_URL') or os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    LAST_CAROUSEL_TIME_KEY = 'user:{user_id}:last_carousel_time'

    @classmethod
    def get_redis_client(cls) -> Redis:
        return Redis.from_url(cls.REDIS_URL, decode_responses=True)

    @classmethod
    def build_feed_zset_key(cls, user_id) -> str:
        return cls.USER_FEED_ZSET_KEY.format(user_id=user_id)

    @classmethod
    def build_post_cache_key(cls, post_id) -> str:
        return cls.POST_CACHE_KEY.format(post_id=post_id)

    @classmethod
    def cache_posts_bulk(cls, posts, request=None) -> None:
        if not posts:
            return
        client = cls.get_redis_client()
        pipeline = client.pipeline()
        for post in posts:
            cache_key = cls.build_post_cache_key(post.id)
            payload = PostSerializer(post, context={'request': request}).data
            pipeline.set(cache_key, json.dumps(payload), ex=cls.POST_CACHE_TTL)
        pipeline.execute()

    @classmethod
    def get_cached_posts(cls, post_ids):
        if not post_ids:
            return []
        client = cls.get_redis_client()
        keys = [cls.build_post_cache_key(post_id) for post_id in post_ids]
        values = client.mget(keys)
        parsed = []
        for value in values:
            if not value:
                parsed.append(None)
                continue
            try:
                parsed.append(json.loads(value))
            except json.JSONDecodeError:
                parsed.append(None)
        return parsed

    @classmethod
    def build_last_carousel_time_key(cls, user_id):
        return cls.LAST_CAROUSEL_TIME_KEY.format(user_id=user_id)

    @classmethod
    def get_last_carousel_timestamp(cls, user):
        if not user or not hasattr(user, 'id'):
            return None
        client = cls.get_redis_client()
        value = client.get(cls.build_last_carousel_time_key(user.id))
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @classmethod
    def set_last_carousel_timestamp(cls, user, timestamp=None):
        if not user or not hasattr(user, 'id'):
            return
        client = cls.get_redis_client()
        now_ts = float(timestamp or time.time())
        client.set(cls.build_last_carousel_time_key(user.id), now_ts)

    @classmethod
    def has_carousel_cooldown(cls, user):
        last_ts = cls.get_last_carousel_timestamp(user)
        if last_ts is None:
            return False
        return (time.time() - last_ts) < cls.CAROUSEL_COOLDOWN_SECONDS

    @classmethod
    def fetch_posts_by_ids(cls, post_ids, request=None):
        if not post_ids:
            return []
        cached_posts = cls.get_cached_posts(post_ids)
        missing_ids = [post_ids[idx] for idx, payload in enumerate(cached_posts) if payload is None]
        result = cached_posts.copy()

        if missing_ids:
            queryset = Post.objects.filter(
                id__in=missing_ids,
                status=PostStatus.PUBLISHED,
                is_deleted=False,
            ).select_related('author').prefetch_related('contents', 'tags')
            posts_by_id = {str(post.id): post for post in queryset}
            fresh_posts = []
            for post_id in missing_ids:
                post = posts_by_id.get(str(post_id))
                if post:
                    fresh_posts.append(post)
            cls.cache_posts_bulk(fresh_posts, request=request)

            for idx, payload in enumerate(result):
                if payload is None:
                    post_id = str(post_ids[idx])
                    result[idx] = posts_by_id.get(post_id)

        return [item for item in result if item is not None]

    @classmethod
    def update_user_feed_zset(cls, user) -> bool:
        if not user or not hasattr(user, 'id'):
            return False

        try:
            redis_client = cls.get_redis_client()
            response = requests.post(
                f"{cls.RECOMMENDATION_SERVICE_URL}/recommendations/posts",
                json={
                    'profile_id': str(user.id),
                    'limit': cls.MAX_RECOMMENDATIONS,
                },
                timeout=10,
            )
            response.raise_for_status()

            recommendations = response.json().get('recommended_ids', [])
            if not recommendations:
                logger.info(f'No recommendations found for user {user.id}')
                return False

            zadd_mapping = {}
            if isinstance(recommendations, list) and recommendations:
                first_item = recommendations[0]
                if isinstance(first_item, dict):
                    for item in recommendations:
                        post_id = item.get('id') or item.get('post_id')
                        if not post_id:
                            continue
                        try:
                            score = float(item.get('score', 0.0))
                        except (TypeError, ValueError):
                            score = 0.0
                        zadd_mapping[str(post_id)] = score
                else:
                    for index, post_id in enumerate(recommendations):
                        zadd_mapping[str(post_id)] = float(len(recommendations) - index)

            if not zadd_mapping:
                logger.info(f'No valid recommendation IDs returned for user {user.id}')
                return False

            key = cls.build_feed_zset_key(user.id)
            pipeline = redis_client.pipeline()
            pipeline.delete(key)
            pipeline.zadd(key, mapping=zadd_mapping)
            pipeline.execute()
            return True

        except requests.exceptions.RequestException as exc:
            logger.error(f'Error calling recommendation service: {exc}')
            return False
        except Exception as exc:
            logger.exception(f'Error updating Redis feed zset for user {user.id}: {exc}')
            return False

    @classmethod
    def get_user_feed_page(cls, user, offset=0, limit=10, request=None, reset_session=False):
        if not user or not hasattr(user, 'id') or user.is_anonymous:
            queryset = Post.objects.filter(status=PostStatus.PUBLISHED, is_deleted=False)
            queryset = queryset.select_related('author').prefetch_related('contents', 'tags')[:limit]
            return list(queryset), None

        redis_client = cls.get_redis_client()
        key = cls.build_feed_zset_key(user.id)

        if reset_session:
            cls.update_user_feed_zset(user)

        has_feed = redis_client.zcard(key) > 0
        if not has_feed:
            cls.update_user_feed_zset(user)

        post_ids = redis_client.zrevrange(key, offset, offset + limit - 1)
        if not post_ids:
            queryset = Post.objects.filter(status=PostStatus.PUBLISHED, is_deleted=False)
            queryset = queryset.select_related('author').prefetch_related('contents', 'tags')[:limit]
            return list(queryset), None

        posts = cls.fetch_posts_by_ids(post_ids, request=request)
        if not posts:
            queryset = Post.objects.filter(status=PostStatus.PUBLISHED, is_deleted=False)
            queryset = queryset.select_related('author').prefetch_related('contents', 'tags')[:limit]
            return list(queryset), None

        next_offset = offset + len(posts) if len(posts) == limit else None
        return posts, next_offset