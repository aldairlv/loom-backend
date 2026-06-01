# posts/views.py
import time
import uuid
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from .models import PendingFeedItem
from .services import FeedService
from .serializers import FeedResponseSerializer


class FeedViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    page_size = 10

    @extend_schema(
        summary="Retrieve 'For You' feed",
        responses=FeedResponseSerializer,
    )
    @action(detail=False, methods=['get'], url_path='for-you')
    def for_you(self, request):
        # 1. Soportamos un cursor enriquecido con offset y posición global.
        incoming_cursor = request.query_params.get('cursor')
        if incoming_cursor is not None:
            incoming_cursor = incoming_cursor.strip()

        normalized_cursor = None
        if incoming_cursor and incoming_cursor.lower() not in ('null', 'none', ''):
            normalized_cursor = incoming_cursor

        offset = 0
        start_position = 1
        if normalized_cursor:
            if '|' in normalized_cursor:
                raw_cursor, raw_start = normalized_cursor.split('|', 1)
                try:
                    offset = int(raw_cursor)
                except Exception:
                    offset = 0
                try:
                    start_position = int(raw_start)
                except Exception:
                    start_position = 1
            else:
                try:
                    offset = int(normalized_cursor)
                except Exception:
                    offset = 0

        is_new_session = normalized_cursor is None
        pending_item = None
        inject_pending = False

        if request.user.is_authenticated:
            pending_item = PendingFeedItem.objects.filter(
                user=request.user,
                is_consumed=False,
            ).order_by('created_at').first()

            if pending_item:
                if pending_item.created_at and (
                    time.time() - pending_item.created_at.timestamp()
                ) > FeedService.CAROUSEL_EXPIRE_SECONDS:
                    pending_item.delete()
                    pending_item = None
                elif FeedService.has_carousel_cooldown(request.user):
                    inject_pending = False
                else:
                    inject_pending = True

        post_limit = self.page_size - 2 if inject_pending else self.page_size

        # 2. Consumimos el feed desde Redis ZSET y traemos los detalles de los posts.
        page, next_offset = FeedService.get_user_feed_page(
            user=request.user,
            offset=offset,
            limit=post_limit,
            request=request,
            reset_session=is_new_session,
        )

        feed_elements = list(page)

        if inject_pending and pending_item:
            virtual_title = {
                'virtual_type': 'title',
                'pending_id': str(pending_item.id),
                'text': pending_item.titulo,
            }
            virtual_carousel = {
                'virtual_type': 'carousel',
                'tipo': pending_item.tipo,
                'pending_id': str(pending_item.id),
                'payload': pending_item.payload,
            }

            if feed_elements:
                first_post = feed_elements.pop(0)
                feed_elements = [first_post, virtual_title, virtual_carousel] + feed_elements
            else:
                feed_elements = [virtual_title, virtual_carousel]

            pending_item.is_consumed = True
            pending_item.save(update_fields=['is_consumed'])
            FeedService.set_last_carousel_timestamp(request.user)

        # 3. Generamos el cursor enriquecido para la próxima página.
        next_cursor = None
        if next_offset is not None and len(feed_elements) == self.page_size:
            next_cursor = f"{next_offset}|{start_position + len(feed_elements)}"

        # 4. Generamos un session_id único para este stream de peticiones
        stream_session_id = uuid.uuid4().hex

        # 5. Preparamos el contexto para los serializadores anidados.
        context = {
            'request': request,
            'session_id': stream_session_id,
            'cursor': next_cursor,
            'start_position': start_position,
        }

        # 6. Pasamos la página de posts al serializador global
        serializer = FeedResponseSerializer(feed_elements, context=context)

        return Response(serializer.data)