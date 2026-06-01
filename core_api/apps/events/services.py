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
from django.contrib.gis.measure import D  # Importamos D para manejar distancias

from profiles.models import Profile
from posts.models import Tag # Assuming Tag model is in posts app
from .models import Event, EventStatus, EventCategory

logger = logging.getLogger(__name__)

class EventService:
    DEFAULT_RADIUS_KM = 30

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
        print("--- Iniciando EventService.filter_events ---")
        # Modificación: Partimos de un queryset que ya filtra por 'SCHEDULED'
        base_queryset = EventService.get_public_and_user_events(user_profile)
        queryset = base_queryset.filter(
            status=EventStatus.SCHEDULED
        )
        print(f"Paso 0: Queryset inicial (públicos + del usuario, 'SCHEDULED'). Total: {queryset.count()} eventos.")

        # 1. Filtro de Geolocalización
        lat = params.get('lat')
        print(f"Filtro Geo: Procesando lat={lat}, lng={params.get('lng')}, radius={params.get('radius')}, anywhere={params.get('anywhere')}")
        lng = params.get('lng')
        radius = params.get('radius', EventService.DEFAULT_RADIUS_KM)  # Radio por defecto de 30 km
        anywhere = params.get('anywhere', 'false').lower() == 'true'
        
        try:
            radius = float(radius)
        except (TypeError, ValueError):
            print(f"ADVERTENCIA: Radio inválido recibido: radius={params.get('radius')}. Usando valor por defecto 30 km.")
            radius = 30.0

        ref_point = None
        order_by_distance = False
        if not anywhere:
            if lat and lng:
                try:
                    ref_point = Point(float(lng), float(lat), srid=4326)
                except (ValueError, TypeError):
                    print(f"ADVERTENCIA: Coordenadas inválidas recibidas: lat={lat}, lng={lng}")
                    pass # Ignore if coordinates are invalid
            elif user_profile and user_profile.location:
                ref_point = user_profile.location
                print("Filtro Geo: Usando localización del perfil de usuario.")

            if ref_point:
                print(f"Filtro Geo: Punto de referencia encontrado: {ref_point}. Aplicando filtro de radio de {radius} km.")
                try:
                    queryset = queryset.filter(
                        location__distance_lte=(ref_point, D(km=radius))
                    ).annotate(distance=Distance('location', ref_point))
                    # Ordenar por distancia y luego por ID para un orden consistente
                    # y evitar problemas con la paginación por cursor.
                    queryset = queryset.order_by('distance', '-id')
                    order_by_distance = True
                except Exception as exc:
                    print(f"ERROR: No se pudo aplicar el filtro de distancia. Detalles: {exc}")
                    queryset = queryset.none()
            else:
                # Si no hay punto de referencia (ni en params ni en perfil), y no es 'anywhere',
                # no devolvemos ningún resultado geolocalizado.
                print("Filtro Geo: No hay punto de referencia y 'anywhere' es false. No se devuelven eventos.")
                queryset = queryset.none()
        else:
            print("Filtro Geo: 'anywhere' es true, se omiten filtros de localización.")
        # If no reference point is found and 'anywhere' is not true, no location filter is applied.
        print(f"Paso 1: Después de filtro de geolocalización. Total: {queryset.count()} eventos.")

        # 2. Filtro Temporal
        anytime = params.get('anytime', 'false').lower() == 'true'
        date_filter = params.get('date')
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        print(f"Filtro Temporal: Procesando anytime={anytime}, date={date_filter}, start_date={start_date}, end_date={end_date}")

        
        now = timezone.now()
        
        if not anytime:
            if date_filter == 'soon':
                print("Filtro Temporal: Aplicando filtro 'soon' (activos o futuros).")
                queryset = queryset.filter(
                    Q(end_time__gte=now) | Q(end_time__isnull=True, start_time__gte=now)
                )
            elif date_filter:
                today = now.date()
                if date_filter == 'today':
                    print("Filtro Temporal: Aplicando filtro 'today'.")
                    queryset = queryset.filter(start_time__date=today)
                elif date_filter == 'tomorrow':
                    print("Filtro Temporal: Aplicando filtro 'tomorrow'.")
                    tomorrow = today + timedelta(days=1)
                    queryset = queryset.filter(start_time__date=tomorrow)
                elif date_filter == 'weekend':
                    print("Filtro Temporal: Aplicando filtro 'weekend'.")
                    # Próximo Sábado (5) y Domingo (6)
                    days_until_saturday = (5 - today.weekday() + 7) % 7
                    saturday = today + timedelta(days=days_until_saturday)
                    sunday = saturday + timedelta(days=1)
                    queryset = queryset.filter(start_time__date__in=[saturday, sunday])
            
            elif start_date and end_date:
                print(f"Filtro Temporal: Aplicando rango de fechas: {start_date} a {end_date}.")
                queryset = queryset.filter(start_time__date__gte=start_date, end_time__date__lte=end_date)
            elif start_date:
                queryset = queryset.filter(start_time__date=start_date)
            elif end_date:
                # Eventos que terminan antes de `end_date` pero que no han terminado aún
                queryset = queryset.filter(end_time__date__lte=end_date, end_time__gte=now)
            else:
                # Comportamiento por defecto: eventos activos o futuros
                print("Filtro Temporal: Aplicando filtro por defecto (eventos activos o futuros).")
                # Un evento está activo si su `end_time` es futuro. Si no tiene `end_time`, consideramos `start_time`.
                queryset = queryset.filter(
                    Q(end_time__gte=now) | Q(end_time__isnull=True, start_time__gte=now)
                )
        else:
            print("Filtro Temporal: 'anytime' es true, se omiten filtros de fecha.")
        print(f"Paso 2: Después de filtro temporal. Total: {queryset.count()} eventos.")

        # Si no se ordenó por distancia, se mantiene el orden por defecto por fecha de inicio.
        # El `order_by('distance')` anterior sobreescribe cualquier ordenación previa.
        if not order_by_distance:
            print("Ordenando por fecha de inicio.")
            # Re-aplicamos el orden por si se perdió en algún `distinct()`
            queryset = queryset.order_by('start_time', '-id') # Mantener el orden por defecto con desempate

        # 3. Filtro por Tags/Categoría
        tags_query = params.get('tags') or params.get('category')
        if tags_query:
            tag_names = [tag.strip() for tag in tags_query.split(',')]
            print(f"Filtro Tags: Aplicando filtro por tags: {tag_names}")
            queryset = queryset.filter(tags__name__in=tag_names).distinct()
            print(f"Paso 3.1: Después de filtro por tags. Total: {queryset.count()} eventos.")

        category_filter = params.get('category')
        if category_filter:
            # You can allow multiple categories by splitting with comma
            categories = [cat.strip() for cat in category_filter.split(',')]
            print(f"Filtro Categoría: Aplicando filtro por categorías: {categories}")
            queryset = queryset.filter(category__in=categories)
            print(f"Paso 3.2: Después de filtro por categoría. Total: {queryset.count()} eventos.")

        # 4. Búsqueda por texto
        search_query = params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | Q(description__icontains=search_query)
            ).distinct()
            print(f"Paso 4: Después de filtro de búsqueda de texto '{search_query}'. Total: {queryset.count()} eventos.")

        print(f"--- Finalizando EventService.filter_events. Devolviendo {queryset.count()} eventos. ---")
        return queryset