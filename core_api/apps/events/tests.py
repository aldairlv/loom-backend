from django.test import TestCase
from django.contrib.gis.geos import Point
from django.utils import timezone

from accounts.models import User
from profiles.models import Profile
from .models import Event, EventStatus, EventCategory
from .services import EventService


class EventServiceGeoFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            display_name='Test User',
            location=Point(0.0, 0.0, srid=4326)
        )

        Event.objects.create(
            creator=self.profile,
            title='Nearby Event',
            description='An event close to the user location.',
            start_time=timezone.now() + timezone.timedelta(days=1),
            status=EventStatus.PUBLISHED,
            is_public=True,
            location=Point(0.1, 0.1, srid=4326),
            category=EventCategory.OTHER,
        )
        Event.objects.create(
            creator=self.profile,
            title='Far Away Event',
            description='An event outside the default radius.',
            start_time=timezone.now() + timezone.timedelta(days=1),
            status=EventStatus.PUBLISHED,
            is_public=True,
            location=Point(10.0, 10.0, srid=4326),
            category=EventCategory.OTHER,
        )

        self.valid_user = User.objects.create_user(
            email='valid@example.com',
            username='validuser',
            password='testpass123'
        )
        self.valid_profile = Profile.objects.create(
            user=self.valid_user,
            display_name='Valid User',
            location=Point(0.1, 0.1, srid=4326)
        )

    def test_filter_events_ignores_zero_zero_user_location(self):
        queryset = EventService.filter_events({}, self.profile)
        self.assertEqual(queryset.count(), 2)
        titles = {event.title for event in queryset}
        self.assertSetEqual(titles, {'Nearby Event', 'Far Away Event'})

    def test_filter_events_uses_valid_profile_location(self):
        queryset = EventService.filter_events({}, self.valid_profile)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().title, 'Nearby Event')
