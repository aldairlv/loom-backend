import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from django.db import transaction
from django.db.models import QuerySet, Q
from django.utils.text import slugify
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance

from profiles.models import Profile
from posts.models import Tag # Assuming Tag model is in posts app
from .models import Event, EventStatus, EventCategory

logger = logging.getLogger(__name__)

class EventService:
    @staticmethod
    def get_event_queryset() -> QuerySet[Event]:
        """
        Returns a base queryset for Event, optimized with select_related and prefetch_related.
        """
        return Event.objects.select_related('creator').prefetch_related('tags', 'assets')

    @staticmethod
    def get_event_by_id(event_id: uuid.UUID) -> Optional[Event]:
        """
        Retrieves a single event by its UUID.
        """
        try:
            return EventService.get_event_queryset().get(id=event_id, is_cancelled=False)
        except Event.DoesNotExist:
            return None

    @staticmethod
    def get_events_for_profile(profile: Profile, include_cancelled: bool = False) -> QuerySet[Event]:
        """
        Retrieves events created by a specific profile.
        """
        queryset = EventService.get_event_queryset().filter(creator=profile)
        if not include_cancelled:
            queryset = queryset.filter(is_cancelled=False)
        return queryset.order_by('start_time')

    @staticmethod
    def create_event(creator: Profile, event_data: Dict[str, Any]) -> Event:
        """
        Creates a new event.
        Handles tag assignment and slug generation.
        """
        with transaction.atomic():
            tags_data = event_data.pop('tags', [])
            assets_data = event_data.pop('assets', [])
            # The serializer creates 'location' from lat/lon, but doesn't remove them.
            # We must remove them here before passing to the model create method.
            event_data.pop('latitude', None)
            event_data.pop('longitude', None)
            
            # Slug generation is handled in the model's save method, but we can pre-process if needed
            # For now, let the model handle it.
            
            event = Event.objects.create(creator=creator, **event_data)
            
            event.tags.set(tags_data)
            event.assets.set(assets_data)
            return event

    @staticmethod
    def update_event(event: Event, update_data: Dict[str, Any]) -> Event:
        """
        Updates an existing event.
        Handles tag assignment and slug regeneration if title changes.
        """
        with transaction.atomic():
            tags_data: Optional[List[Tag]] = update_data.pop('tags', None)
            
            # If title is updated and slug is not explicitly provided, clear slug to regenerate
            if 'title' in update_data and 'slug' not in update_data:
                event.slug = '' # This will trigger slug generation in model's save method

            for attr, value in update_data.items():
                setattr(event, attr, value)
            
            event.save()

            if tags_data is not None:
                event.tags.set(tags_data)
            
            return event

    @staticmethod
    def cancel_event(event: Event) -> Event:
        """
        Soft cancels an event by setting is_cancelled to True and status to CANCELLED.
        """
        with transaction.atomic():
            event.is_cancelled = True
            event.status = EventStatus.CANCELLED
            event.save()
            return event

    @staticmethod
    def rsvp_toggle(event: Event, profile: Profile) -> tuple[bool, str]:
        """
        Toggles a profile's attendance for an event (RSVP).

        Returns a tuple: (joined: bool, message: str)
        """
        is_attending = event.attendees.filter(pk=profile.pk).exists()

        if is_attending:
            # If already attending, remove (Cancel RSVP)
            event.attendees.remove(profile)
            joined = False
            message = "Asistencia cancelada con éxito."
        else:
            # If not attending, add (Confirm RSVP)
            # Optional business logic: Check if the event is full
            if event.max_attendees and event.attendees.count() >= event.max_attendees:
                raise ValueError("Este evento ha alcanzado el límite máximo de asistentes.")
            
            event.attendees.add(profile)
            joined = True
            message = "Asistencia confirmada con éxito."
        return joined, message

    @staticmethod
    def delete_event_permanently(event: Event) -> None:
        """
        Deletes an event permanently from the database. Use with caution.
        """
        event.delete()

    @staticmethod
    def search_events(query: str, profile: Optional[Profile] = None) -> QuerySet[Event]:
        queryset = EventService.get_event_queryset().filter(is_cancelled=False, is_public=True)
        if profile:
            queryset = queryset | EventService.get_event_queryset().filter(creator=profile, is_cancelled=False)
        queryset = queryset.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct()
        return queryset.order_by('start_time')

    @staticmethod
    def get_public_and_user_events(user_profile: Optional[Profile] = None) -> QuerySet[Event]:
        """
        Returns a queryset of public, non-cancelled events, plus private events of the user.
        """
        # Base queryset: public and not cancelled events
        queryset = EventService.get_event_queryset().filter(is_public=True, is_cancelled=False)

        # If the user is authenticated, also include their own private/draft events
        if user_profile:
            user_events = EventService.get_event_queryset().filter(creator=user_profile, is_cancelled=False)
            queryset = (queryset | user_events).distinct()

        return queryset.order_by('start_time')

    @staticmethod
    def filter_events(params: Dict[str, Any], user_profile: Optional[Profile] = None) -> QuerySet[Event]:
        """
        Aplica filtros inteligentes a la lista de eventos.
        """
        logger.info("--- Iniciando EventService.filter_events ---")
        queryset = EventService.get_public_and_user_events(user_profile)
        logger.info(f"Paso 0: Queryset inicial (públicos + del usuario). Total: {queryset.count()} eventos.")

        # 1. Filtro de Geolocalización
        lat = params.get('lat')
        logger.info(f"Filtro Geo: Procesando lat={lat}, lng={params.get('lng')}, radius={params.get('radius')}, anywhere={params.get('anywhere')}")
        lng = params.get('lng')
        radius = params.get('radius', 15)  # Radio por defecto de 15 km
        anywhere = params.get('anywhere', 'false').lower() == 'true'
        
        ref_point = None
        order_by_distance = False
        if not anywhere:
            if lat and lng:
                try:
                    ref_point = Point(float(lng), float(lat), srid=4326)
                except (ValueError, TypeError):
                    logger.warning(f"Coordenadas inválidas recibidas: lat={lat}, lng={lng}")
                    pass # Ignore if coordinates are invalid
            elif user_profile and user_profile.location:
                ref_point = user_profile.location
                logger.info("Filtro Geo: Usando localización del perfil de usuario.")

            logger.info(f"Filtro Geo: Punto de referencia para búsqueda: {ref_point}")
            if ref_point:
                # Filter by distance and annotate for ordering
                queryset = queryset.filter(
                    location__dwithin=(ref_point, float(radius) * 1000) # dwithin espera metros
                ).annotate(
                    distance=Distance('location', ref_point)
                )
                order_by_distance = True
        else:
            logger.info("Filtro Geo: 'anywhere' es true, se omiten filtros de localización.")
        # If no reference point is found and 'anywhere' is not true, no location filter is applied.
        logger.info(f"Paso 1: Después de filtro de geolocalización. Total: {queryset.count()} eventos.")

        # 2. Filtro Temporal
        anytime = params.get('anytime', 'false').lower() == 'true'
        date_filter = params.get('date')
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        logger.info(f"Filtro Temporal: Procesando anytime={anytime}, date={date_filter}, start_date={start_date}, end_date={end_date}")

        
        now = timezone.now()
        
        if not anytime:
            if date_filter:
                today = now.date()
                if date_filter == 'today':
                    logger.info("Filtro Temporal: Aplicando filtro 'today'.")
                    queryset = queryset.filter(start_time__date=today)
                elif date_filter == 'tomorrow':
                    logger.info("Filtro Temporal: Aplicando filtro 'tomorrow'.")
                    tomorrow = today + timedelta(days=1)
                    queryset = queryset.filter(start_time__date=tomorrow)
                elif date_filter == 'weekend':
                    logger.info("Filtro Temporal: Aplicando filtro 'weekend'.")
                    # Próximo Sábado (5) y Domingo (6)
                    days_until_saturday = (5 - today.weekday() + 7) % 7
                    saturday = today + timedelta(days=days_until_saturday)
                    sunday = saturday + timedelta(days=1)
                    queryset = queryset.filter(start_time__date__in=[saturday, sunday])
            
            elif start_date and end_date:
                logger.info(f"Filtro Temporal: Aplicando rango de fechas: {start_date} a {end_date}.")
                queryset = queryset.filter(start_time__date__gte=start_date, end_time__date__lte=end_date)
            elif start_date:
                queryset = queryset.filter(start_time__date=start_date)
            elif end_date:
                # Eventos que terminan antes de `end_date` pero que no han terminado aún
                queryset = queryset.filter(end_time__date__lte=end_date, end_time__gte=now)
            else:
                # Comportamiento por defecto: eventos activos o futuros
                logger.info("Filtro Temporal: Aplicando filtro por defecto (eventos activos o futuros).")
                # Un evento está activo si su `end_time` es futuro. Si no tiene `end_time`, consideramos `start_time`.
                queryset = queryset.filter(
                    Q(end_time__gte=now) | Q(end_time__isnull=True, start_time__gte=now)
                )
        else:
            logger.info("Filtro Temporal: 'anytime' es true, se omiten filtros de fecha.")
        logger.info(f"Paso 2: Después de filtro temporal. Total: {queryset.count()} eventos.")

        # Order by distance if applicable, otherwise by start time
        if order_by_distance:
            logger.info("Ordenando por distancia.")
            queryset = queryset.order_by('distance')
        else:
            logger.info("Ordenando por fecha de inicio.")
            queryset = queryset.order_by('start_time')

        # 3. Filtro por Tags/Categoría
        tags_query = params.get('tags') or params.get('category')
        if tags_query:
            tag_names = [tag.strip() for tag in tags_query.split(',')]
            logger.info(f"Filtro Tags: Aplicando filtro por tags: {tag_names}")
            queryset = queryset.filter(tags__name__in=tag_names).distinct()
            logger.info(f"Paso 3.1: Después de filtro por tags. Total: {queryset.count()} eventos.")

        category_filter = params.get('category')
        if category_filter:
            # You can allow multiple categories by splitting with comma
            categories = [cat.strip() for cat in category_filter.split(',')]
            logger.info(f"Filtro Categoría: Aplicando filtro por categorías: {categories}")
            queryset = queryset.filter(category__in=categories)
            logger.info(f"Paso 3.2: Después de filtro por categoría. Total: {queryset.count()} eventos.")

        # 4. Búsqueda por texto
        search_query = params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | Q(description__icontains=search_query)
            ).distinct()
            logger.info(f"Paso 4: Después de filtro de búsqueda de texto '{search_query}'. Total: {queryset.count()} eventos.")

        logger.info(f"--- Finalizando EventService.filter_events. Devolviendo {queryset.count()} eventos. ---")
        return queryset