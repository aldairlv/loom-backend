from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

# Create your models here.
import uuid
from django.conf import settings
from django.templatetags.static import static
from posts.models import Tag # Assuming Tag model is in posts app
from django.contrib.gis.db import models as gis_models
from assets.models import Media

class EventStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'
    CANCELLED = 'cancelled', 'Cancelled'
    COMPLETED = 'completed', 'Completed'

class EventCategory(models.TextChoices):
    # ==================================================
    # Académico, Ciencia y Tecnología
    # ==================================================
    SCIENCE = 'science', 'Science & Research'
    TECHNOLOGY = 'technology', 'Technology & Innovation'
    AI = 'ai', 'Artificial Intelligence'
    DATA = 'data', 'Data Science & Analytics'
    CYBERSECURITY = 'cybersecurity', 'Cybersecurity'
    ENGINEERING = 'engineering', 'Engineering'
    EDUCATION = 'education', 'Education & Learning'
    WORKSHOPS = 'workshops', 'Workshops & Training'
    CAREER = 'career', 'Career Development'

    # ==================================================
    # Negocios y Finanzas
    # ==================================================
    BUSINESS = 'business', 'Business & Entrepreneurship'
    STARTUPS = 'startups', 'Startups & Venture Capital'
    MARKETING = 'marketing', 'Marketing & Advertising'
    SALES = 'sales', 'Sales & Networking'
    FINANCE = 'finance', 'Finance & Investing'
    REAL_ESTATE = 'real_estate', 'Real Estate'

    # ==================================================
    # Arte y Cultura
    # ==================================================
    ARTS = 'arts', 'Arts & Culture'
    MUSIC = 'music', 'Music & Concerts'
    THEATER = 'theater', 'Theater & Performing Arts'
    DANCE = 'dance', 'Dance'
    FILM = 'film', 'Film, Media & Photography'
    LITERATURE = 'literature', 'Literature & Books'
    MUSEUMS = 'museums', 'Museums & Exhibitions'
    FASHION = 'fashion', 'Fashion & Design'
    CRAFTS = 'crafts', 'Crafts & Handmade'

    # ==================================================
    # Entretenimiento
    # ==================================================
    GAMING = 'gaming', 'Gaming & Esports'
    COMEDY = 'comedy', 'Comedy & Stand-up'
    NIGHTLIFE = 'nightlife', 'Nightlife & Parties'
    FESTIVALS = 'festivals', 'Festivals'
    CONVENTIONS = 'conventions', 'Conventions & Expos'

    # ==================================================
    # Deportes y Actividad Física
    # ==================================================
    SPORTS = 'sports', 'Sports'
    FITNESS = 'fitness', 'Fitness & Gym'
    RUNNING = 'running', 'Running & Marathons'
    CYCLING = 'cycling', 'Cycling'
    YOGA = 'yoga', 'Yoga & Meditation'
    MARTIAL_ARTS = 'martial_arts', 'Martial Arts'
    WATER_SPORTS = 'water_sports', 'Water Sports'

    # ==================================================
    # Aire Libre y Naturaleza
    # ==================================================
    OUTDOOR = 'outdoor', 'Outdoor & Adventure'
    HIKING = 'hiking', 'Hiking & Trekking'
    CAMPING = 'camping', 'Camping'
    NATURE = 'nature', 'Nature & Wildlife'
    ENVIRONMENT = 'environment', 'Environment & Sustainability'

    # ==================================================
    # Gastronomía
    # ==================================================
    FOOD = 'food', 'Food & Drink'
    WINE = 'wine', 'Wine Tasting'
    BEER = 'beer', 'Beer & Craft Brewing'
    COFFEE = 'coffee', 'Coffee & Specialty Drinks'
    COOKING = 'cooking', 'Cooking Classes'

    # ==================================================
    # Salud y Bienestar
    # ==================================================
    HEALTH = 'health', 'Health & Wellness'
    MENTAL_HEALTH = 'mental_health', 'Mental Health'
    WELLNESS = 'wellness', 'Wellness & Self-care'
    BEAUTY = 'beauty', 'Beauty & Personal Care'

    # ==================================================
    # Comunidad y Sociedad
    # ==================================================
    COMMUNITY = 'community', 'Community & Social'
    NETWORKING = 'networking', 'Networking'
    CHARITY = 'charity', 'Charity & Volunteering'
    RELIGION = 'religion', 'Religion & Spirituality'
    POLITICS = 'politics', 'Politics & Civic Engagement'
    LGBTQ = 'lgbtq', 'LGBTQ+'
    WOMEN = 'women', 'Women-focused Events'
    SENIORS = 'seniors', 'Senior Activities'

    # ==================================================
    # Familia
    # ==================================================
    FAMILY = 'family', 'Family & Kids'
    KIDS = 'kids', 'Kids Activities'
    PARENTING = 'parenting', 'Parenting'

    # ==================================================
    # Viajes y Estilo de Vida
    # ==================================================
    TRAVEL = 'travel', 'Travel & Tourism'
    LUXURY = 'luxury', 'Luxury Lifestyle'
    SHOPPING = 'shopping', 'Shopping & Markets'
    PETS = 'pets', 'Pets & Animals'
    AUTOMOTIVE = 'automotive', 'Cars & Automotive'

    # ==================================================
    # Eventos Especiales
    # ==================================================
    CONFERENCE = 'conference', 'Conferences'
    SEMINAR = 'seminar', 'Seminars'
    MEETUP = 'meetup', 'Meetups'
    EXHIBITION = 'exhibition', 'Exhibitions'
    COMPETITION = 'competition', 'Competitions'
    AWARDS = 'awards', 'Awards & Ceremonies'
    FUNDRAISER = 'fundraiser', 'Fundraisers'

    # ==================================================
    # Otros
    # ==================================================
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

    status = models.CharField(max_length=20, choices=EventStatus.choices, default=EventStatus.PUBLISHED,
                              help_text="Current status of the event.")

    category = models.CharField(max_length=20, choices=EventCategory.choices, default=EventCategory.OTHER,
                                help_text="Category of the event.")

    #banner_image = models.ImageField(upload_to='event_banners/', blank=True, null=True,
                                     #help_text="Banner image for the event.")

    requires_payment = models.BooleanField(default=False,
                                           help_text="True if attendees must pay to join the event.")
    price_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,
                                       help_text="Ticket price amount for paid events.")
    price_currency = models.CharField(max_length=10, blank=True, null=True,
                                      help_text="Currency code for the ticket price.")
    stripe_price_id = models.CharField(max_length=255, blank=True, null=True,
                                       help_text="Stripe Price ID for the event pricing.")

    class PaymentMethod(models.TextChoices):
        CREDIT_CARD = 'credit_card', 'Credit Card'
        APPLE_PAY = 'apple_pay', 'Apple Pay'
        PAYPAL = 'paypal', 'PayPal'

    payment_methods_allowed = models.JSONField(default=list, blank=True,
                                               help_text="Allowed payment methods for this event.")
    timezone = models.CharField(max_length=50, blank=True, null=True,
                                help_text="Timezone identifier for the event.")
    requires_qr_checkin = models.BooleanField(default=False,
                                              help_text="True when the event requires QR check-in.")
    meeting_instructions = models.TextField(blank=True, null=True,
                                            help_text="Instructions for meeting check-in or online conferencing.")
    support_email = models.CharField(max_length=255, blank=True, null=True,
                                     help_text="Support email address for the event.")
    support_url = models.URLField(blank=True, null=True,
                                  help_text="Support or help URL for the event.")
    website_url = models.URLField(blank=True, null=True,
                                  help_text="Website URL for the event.")
    whatsapp_url = models.URLField(blank=True, null=True,
                                   help_text="WhatsApp URL for the event.")
    telegram_url = models.URLField(blank=True, null=True,
                                   help_text="Telegram URL for the event.")
    discord_url = models.URLField(blank=True, null=True,
                                  help_text="Discord URL for the event.")
    zoom_url = models.URLField(blank=True, null=True,
                               help_text="Zoom URL for the event.")
    live_stream_url = models.URLField(blank=True, null=True,
                                      help_text="Live stream URL for online events.")
    secure_attendance_token = models.CharField(max_length=255, blank=True, null=True,
                                               help_text="Secure token used for attendance validation.")
    requirements = models.JSONField(default=list, blank=True,
                                    help_text="List of logistical requirements for the event.")
    is_free = models.BooleanField(default=False,
                                  help_text="True when the event is free.")
    thumbnail = models.ForeignKey(Media, blank=True, null=True,
                                  on_delete=models.SET_NULL,
                                  related_name='event_thumbnails',
                                  help_text="Single thumbnail asset for the event.")

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

    @property
    def rating_summary(self) -> dict:
        from django.db.models import Avg

        aggregate = self.reviews.aggregate(
            average_rating=Avg('rating'),
            total_reviews=models.Count('id')
        )
        average = aggregate['average_rating'] or 0.0
        total = aggregate['total_reviews'] or 0
        return {
            'average_rating': round(float(average), 1) if total else 0.0,
            'total_reviews': total
        }


class EventReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text="Event that is being reviewed."
    )
    user = models.ForeignKey(
        'profiles.Profile',
        on_delete=models.CASCADE,
        related_name='event_reviews',
        help_text="The profile that submitted this review."
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating between 1 and 5."
    )
    comment = models.TextField(blank=True, null=True,
                               help_text="Optional comment justifying the rating.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['-created_at']
        verbose_name = 'Event Review'
        verbose_name_plural = 'Event Reviews'

    def __str__(self):
        return f"Review {self.rating} for {self.event.title} by {self.user.display_name}"


class EventAttendance(models.Model):
    """
    Tracks attendance for an event, including a secure token for QR check-in
    and the check-in status.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendance_records')
    attendee = models.ForeignKey('profiles.Profile', on_delete=models.CASCADE, related_name='event_attendances')
    secure_attendance_token = models.CharField(
        max_length=255,
        unique=True,
        help_text="Secure unique token for this specific user and event attendance."
    )
    checked_in_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the attendee was checked in.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'attendee')
        ordering = ['-created_at']
        verbose_name = "Event Attendance"
        verbose_name_plural = "Event Attendances"

    def __str__(self):
        status = "Checked-in" if self.checked_in_at else "Registered"
        return f"{self.attendee.display_name} - {self.event.title} ({status})"
