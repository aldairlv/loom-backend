import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from rest_framework.decorators import action
from rest_framework.pagination import CursorPagination
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiParameter

from profiles.models import Profile
from .models import Event
from .serializers import EventSerializer
from .nested_serializers import EventFeedSerializer
from . import services

logger = logging.getLogger(__name__)

class EventCursorPagination(CursorPagination):
    page_size = 10
    ordering = 'start_time' # Orden por defecto si no hay geo-búsqueda

class EventViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = EventCursorPagination

    def get_queryset(self):
        """
        Aplica el filtrado según la acción.
        - 'list': Devuelve todos los eventos públicos y no cancelados, más los del propio usuario.
        - 'feed': Usa el servicio de filtrado avanzado para el feed.
        """
        user_profile = None
        if self.request.user.is_authenticated:
            try:
                user_profile = self.request.user.profile
            except Profile.DoesNotExist:
                user_profile = None

        # Si la acción es 'feed', usamos el filtro complejo.
        if self.action == 'feed':
            queryset = services.EventService.filter_events(self.request.query_params, user_profile)
        else:
            # Para 'list' y otras acciones, un queryset más simple.
            queryset = services.EventService.get_public_and_user_events(user_profile)

        # Pro-Tip de Rendimiento: Prefetch related objects
        return queryset.prefetch_related('attendees', 'tags', 'assets')

    def get_serializer_class(self):
        """
        Return different serializers for list/retrieve vs create/update.
        """
        if self.action in ['list', 'retrieve', 'feed']:
            return EventFeedSerializer
        return EventSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name='radius', description='Search radius in kilometers.', type=int),
            OpenApiParameter(name='lat', description='Latitude for search center.', type=float),
            OpenApiParameter(name='lng', description='Longitude for search center.', type=float),
            OpenApiParameter(name='date', description='Filter by date: "today", "tomorrow", "weekend".', type=str),
            OpenApiParameter(name='start_date', description='Filter by start date (YYYY-MM-DD).', type=str),
            OpenApiParameter(name='end_date', description='Filter by end date (YYYY-MM-DD).', type=str),
            OpenApiParameter(name='category', description='Filter by category name (e.g., "sports,music").', type=str),
            OpenApiParameter(name='anywhere', description='Ignore location filters.', type=bool),
            OpenApiParameter(name='anytime', description='Ignore date filters.', type=bool),
            OpenApiParameter(name='cursor', description='The pagination cursor value for the next or previous page.', type=str),
        ]
    )
    @action(detail=False, methods=['get'])
    def feed(self, request, *args, **kwargs):
        logger.info("="*20 + " INICIANDO /events/feed/ " + "="*20)
        logger.info(f"Query Params recibidos: {request.query_params}")

        queryset = self.filter_queryset(self.get_queryset())
        logger.info(f"Queryset después de get_queryset y filter_queryset: {queryset.query}")
        logger.info(f"Número de eventos encontrados ANTES de paginar: {queryset.count()}")

        page = self.paginate_queryset(queryset)

        if page is not None:
            logger.info(f"Paginación aplicada. Número de eventos en la página actual: {len(page)}")
            serializer = self.get_serializer(page, many=True)
        else:
            logger.warning("La paginación devolvió None. Se serializará el queryset completo.")
            serializer = self.get_serializer(queryset, many=True)
        logger.info(f"Serialización completada. Número de elementos serializados: {len(serializer.data)}")

        # Build the transparent queryParams object
        raw_radius = request.query_params.get('radius')
        try:
            effective_radius = float(raw_radius) if raw_radius is not None else services.EventService.DEFAULT_RADIUS_KM
        except (TypeError, ValueError):
            effective_radius = services.EventService.DEFAULT_RADIUS_KM

        effective_anywhere = request.query_params.get('anywhere', 'false').lower() == 'true'
        effective_anytime = request.query_params.get('anytime', 'false').lower() == 'true'

        effective_lat = request.query_params.get('lat')
        effective_lng = request.query_params.get('lng')
        try:
            effective_lat = float(effective_lat) if effective_lat is not None else None
            effective_lng = float(effective_lng) if effective_lng is not None else None
        except (TypeError, ValueError):
            effective_lat = None
            effective_lng = None

        if not effective_anywhere and (effective_lat is None or effective_lng is None):
            try:
                user_profile = request.user.profile
            except Profile.DoesNotExist:
                user_profile = None
            if user_profile and user_profile.location:
                effective_lat = user_profile.location.y
                effective_lng = user_profile.location.x

        active_filters = {
            'radius': effective_radius,
            'lat': effective_lat,
            'lng': effective_lng,
            'date': request.query_params.get('date'),
            'start_date': request.query_params.get('start_date'),
            'end_date': request.query_params.get('end_date'),
            'category': request.query_params.get('category'),
            'anywhere': effective_anywhere,
            'anytime': effective_anytime,
            'limit': self.pagination_class.page_size
        }

        # Get cursor for next/previous page
        paginator = self.paginator
        next_link = paginator.get_next_link()
        cursor = None
        if next_link:
            cursor = next_link.split('cursor=')[-1]

        logger.info(f"Respuesta final contiene {len(serializer.data)} elementos.")
        logger.info("="*20 + " FIN /events/feed/ " + "="*20 + "\n")

        return Response({
            "meta": {"status": 200, "msg": "OK"},
            "response": {
                "feed": {
                    "elements": serializer.data,
                    "queryParams": {
                        "available_fields": "?radius&lat&lng&date&start_date&end_date&category&anywhere&anytime&search",
                        "active_filters": active_filters,
                        "cursor": cursor
                    }
                }
            }
        })

    def list(self, request, *args, **kwargs):
        # Ahora 'list' usa el comportamiento por defecto de ModelViewSet,
        # que llamará a get_queryset, paginate, get_serializer y devolverá una respuesta paginada estándar.
        # No es necesario sobreescribirlo si el comportamiento por defecto es suficiente.
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        # For a single object, we can wrap it in the desired structure as well
        return Response({
            "meta": {"status": 200, "msg": "OK"},
            "response": {
                "feed": {
                    "elements": [serializer.data],
                    "queryParams": {} # Can be populated if needed
                }
            }
        })



    def perform_create(self, serializer: EventSerializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied("Authentication required to create an event.")
        try:
            creator_profile = self.request.user.profile
        except Profile.DoesNotExist:
            raise ValidationError({'creator': 'The authenticated user does not have a default profile to create events.'})
        event = services.EventService.create_event(creator=creator_profile, event_data=serializer.validated_data)
        serializer.instance = event

    def perform_update(self, serializer: EventSerializer):
        event: Event = self.get_object()
        if not self.request.user.is_authenticated or event.creator.user != self.request.user:
            raise PermissionDenied("You do not have permission to edit this event.")
        updated_event = services.EventService.update_event(event, serializer.validated_data)
        serializer.instance = updated_event

    def perform_destroy(self, instance: Event):
        if not self.request.user.is_authenticated or instance.creator.user != self.request.user:
            raise PermissionDenied("You do not have permission to cancel this event.")
        services.EventService.cancel_event(instance) # Use soft delete

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rsvp(self, request, pk=None):
        """
        Toggles the authenticated user's RSVP status for an event.
        """
        event = self.get_object()
        try:
            user_profile = request.user.profile
        except Profile.DoesNotExist:
            return Response(
                {"error": "El usuario no tiene un perfil para realizar esta acción."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            joined, message = services.EventService.rsvp_toggle(event, user_profile)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "msg": message,
            "status": "success",
            "data": {
                "is_attending": joined,
                "rsvp_count": event.rsvp_count
            }
        }, status=status.HTTP_200_OK)
