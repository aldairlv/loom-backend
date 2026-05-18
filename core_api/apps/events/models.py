from django.db import models

# Create your models here.
import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.templatetags.static import static
from posts.models import Tag # Assuming Tag model is in posts app
from django.contrib.gis.db import models as gis_models
from assets.models import Media

class EventStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    SCHEDULED = 'scheduled', 'Scheduled'
    CANCELLED = 'cancelled', 'Cancelled'
    COMPLETED = 'completed', 'Completed'

class EventCategory(models.TextChoices):
    SCIENCE = 'science', 'Science'
    TECHNOLOGY = 'technology', 'Technology'
    SPORTS = 'sports', 'Sports'
    ARTS = 'arts', 'Arts'
    MUSIC = 'music', 'Music'
    FOOD = 'food', 'Food'
    OTHER = 'other', 'Other'

class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    creator = models.ForeignKey(
        'profiles.Profile',
        on_delete=models.CASCADE,
        related_name='created_events',
        help_text="The profile that created this event."
    )

    title = models.CharField(max_length=200, help_text="Title of the event.")
    slug = models.SlugField(max_length=255, unique=True, blank=True,
                            help_text="URL-friendly version of the title. Auto-generated if left blank.")
    description = models.TextField(blank=True, null=True,
                                   help_text="Detailed description of the event.")

    start_time = models.DateTimeField(help_text="When the event starts.")
    end_time = models.DateTimeField(blank=True, null=True,
                                   help_text="When the event ends (optional).")

    location_name = models.CharField(max_length=255, blank=True, null=True,
                                     help_text="Name of the location (e.g., 'Online', 'Central Park Cafe').")
    location_address = models.CharField(max_length=500, blank=True, null=True,
                                        help_text="Physical address or URL for online events.")
    location = gis_models.PointField(
        srid=4326,
        spatial_index=True,
        null=True,
        blank=True,
        help_text="Localización del evento en formato (Longitud, Latitud) usando WGS84."
    )
    max_attendees = models.PositiveIntegerField(blank=True, null=True,
                                                 help_text="Maximum number of attendees allowed (optional).")
    
    is_online = models.BooleanField(default=False,
                                    help_text="True if the event is online, False if physical.")
    is_public = models.BooleanField(default=True,
                                    help_text="True if the event is publicly visible, False for private events.")
    is_cancelled = models.BooleanField(default=False,
                                       help_text="True if the event has been cancelled (soft delete).")

    status = models.CharField(max_length=20, choices=EventStatus.choices, default=EventStatus.SCHEDULED,
                              help_text="Current status of the event.")

    category = models.CharField(max_length=20, choices=EventCategory.choices, default=EventCategory.OTHER,
                                help_text="Category of the event.")

    #banner_image = models.ImageField(upload_to='event_banners/', blank=True, null=True,
                                     #help_text="Banner image for the event.")

    tags = models.ManyToManyField(Tag, blank=True, related_name='events',
                                  help_text="Tags for categorization and discoverability.")

    assets = models.ManyToManyField(Media, blank=True, related_name='events',
                                    help_text="Associated media assets for the event.")

    attendees = models.ManyToManyField(
        'profiles.Profile',
        blank=True,
        related_name='attending_events',
        help_text="Profiles that have RSVP'd to this event."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']
        verbose_name = "Event"
        verbose_name_plural = "Events"
        indexes = [
            models.Index(fields=['start_time', 'status']),
            models.Index(fields=['creator', 'start_time']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # Ensure slug is unique, append UUID part if necessary
            original_slug = self.slug
            counter = 1
            while Event.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} by {self.creator.display_name}"

    @property
    def rsvp_count(self) -> int:
        return self.attendees.count()

    @property
    def get_banner_url(self) -> str:
        if self.banner_image and hasattr(self.banner_image, 'url'):
            return self.banner_image.url
        return static('images/default_event_banner.png') # Assuming a default banner image
