from django_opensearch_dsl import Document, fields
from django_opensearch_dsl.registries import registry

from events.models import Event, EventStatus
from posts.models import Post, PostStatus
from profiles.models import Profile


def _post_body(post):
    fragments = []
    media_url = None
    content_type = 'text'
    for content in post.contents.all().order_by('order'):
        if content.type == 'text' and content.text:
            fragments.append(content.text)
        elif content.media and content.media.url and media_url is None:
            media_url = content.media.url
        if content.type in ('image', 'video', 'audio'):
            content_type = content.type
    if not fragments and content_type == 'text':
        content_type = 'text'
    return '\n\n'.join(fragments), content_type, media_url


@registry.register_document
class PostDocument(Document):
    doc_type = fields.KeywordField()
    body = fields.TextField()
    tags = fields.ListField(fields.KeywordField())
    author_username = fields.KeywordField()
    author_avatar = fields.KeywordField()
    content_type = fields.KeywordField()
    media_url = fields.KeywordField()
    created_at = fields.DateField()
    sort_date = fields.DateField()

    class Index:
        name = 'posts_idx'
        settings = {'number_of_shards': 1, 'number_of_replicas': 0}

    class Django:
        model = Post
        fields = ['id']
        ignore_signals = True
        queryset_pagination = 128

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_deleted=False, status=PostStatus.PUBLISHED)
            .select_related('author__user')
            .prefetch_related('contents__media', 'tags')
        )

    def prepare_doc_type(self, instance):
        return 'posts'

    def prepare_body(self, instance):
        body, _, _ = _post_body(instance)
        return body

    def prepare_tags(self, instance):
        return list(instance.tags.values_list('name', flat=True))

    def prepare_author_username(self, instance):
        return instance.author.user.username

    def prepare_author_avatar(self, instance):
        return instance.author.get_avatar_url

    def prepare_content_type(self, instance):
        _, content_type, _ = _post_body(instance)
        return content_type

    def prepare_media_url(self, instance):
        _, _, media_url = _post_body(instance)
        return media_url or ''

    def prepare_created_at(self, instance):
        return instance.published_at or instance.created_at

    def prepare_sort_date(self, instance):
        return instance.published_at or instance.created_at


@registry.register_document
class EventDocument(Document):
    doc_type = fields.KeywordField()
    title = fields.TextField()
    body = fields.TextField()
    tags = fields.ListField(fields.KeywordField())
    author_username = fields.KeywordField()
    author_avatar = fields.KeywordField()
    location = fields.GeoPointField()
    location_name = fields.KeywordField()
    start_time = fields.DateField()
    media_url = fields.KeywordField()
    category = fields.KeywordField()
    sort_date = fields.DateField()

    class Index:
        name = 'events_idx'
        settings = {'number_of_shards': 1, 'number_of_replicas': 0}

    class Django:
        model = Event
        fields = ['id']
        ignore_signals = True
        queryset_pagination = 128

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                status=EventStatus.PUBLISHED,
                is_public=True,
                is_cancelled=False,
            )
            .select_related('creator__user', 'thumbnail')
            .prefetch_related('tags')
        )

    def prepare_doc_type(self, instance):
        return 'events'

    def prepare_title(self, instance):
        return instance.title

    def prepare_body(self, instance):
        return instance.description or ''

    def prepare_tags(self, instance):
        return list(instance.tags.values_list('name', flat=True))

    def prepare_author_username(self, instance):
        return instance.creator.user.username

    def prepare_author_avatar(self, instance):
        return instance.creator.get_avatar_url

    def prepare_location(self, instance):
        if instance.location:
            return {'lat': instance.location.y, 'lon': instance.location.x}
        return None

    def prepare_location_name(self, instance):
        return instance.location_name or instance.location_address or ''

    def prepare_start_time(self, instance):
        return instance.start_time

    def prepare_media_url(self, instance):
        if instance.thumbnail and instance.thumbnail.url:
            return instance.thumbnail.url
        return ''

    def prepare_category(self, instance):
        return instance.category

    def prepare_sort_date(self, instance):
        return instance.start_time


@registry.register_document
class UserDocument(Document):
    doc_type = fields.KeywordField()
    username = fields.KeywordField()
    display_name = fields.TextField()
    bio = fields.TextField()
    avatar = fields.KeywordField()
    city = fields.KeywordField()
    sort_date = fields.DateField()

    class Index:
        name = 'users_idx'
        settings = {'number_of_shards': 1, 'number_of_replicas': 0}

    class Django:
        model = Profile
        fields = ['id']
        ignore_signals = True
        queryset_pagination = 128

    def get_queryset(self):
        return super().get_queryset().select_related('user')

    def prepare_doc_type(self, instance):
        return 'users'

    def prepare_username(self, instance):
        return instance.user.username

    def prepare_display_name(self, instance):
        return instance.display_name

    def prepare_bio(self, instance):
        return instance.bio or ''

    def prepare_avatar(self, instance):
        return instance.get_avatar_url

    def prepare_city(self, instance):
        return instance.city or ''

    def prepare_sort_date(self, instance):
        return instance.user.date_joined
