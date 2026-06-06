# Generated manually for event payment fields and reviews

from django.db import migrations, models
import uuid
import django.db.models.deletion
from django.core.validators import MaxValueValidator, MinValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0007_alter_event_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='requires_payment',
            field=models.BooleanField(default=False, help_text='True if attendees must pay to join the event.'),
        ),
        migrations.AddField(
            model_name='event',
            name='price_amount',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Ticket price amount for paid events.', max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='price_currency',
            field=models.CharField(blank=True, help_text='Currency code for the ticket price.', max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='stripe_price_id',
            field=models.CharField(blank=True, help_text='Stripe Price ID for the event pricing.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='payment_methods_allowed',
            field=models.JSONField(blank=True, default=list, help_text='Allowed payment methods for this event.'),
        ),
        migrations.AddField(
            model_name='event',
            name='timezone',
            field=models.CharField(blank=True, help_text='Timezone identifier for the event.', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='requires_qr_checkin',
            field=models.BooleanField(default=False, help_text='True when the event requires QR check-in.'),
        ),
        migrations.AddField(
            model_name='event',
            name='meeting_instructions',
            field=models.TextField(blank=True, help_text='Instructions for meeting check-in or online conferencing.', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='support_url',
            field=models.URLField(blank=True, help_text='Support or help URL for the event.', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='live_stream_url',
            field=models.URLField(blank=True, help_text='Live stream URL for online events.', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='is_free',
            field=models.BooleanField(default=False, help_text='True when the event is free.'),
        ),
        migrations.AddField(
            model_name='event',
            name='thumbnail',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='event_thumbnails', to='assets.media', help_text='Single thumbnail asset for the event.'),
        ),
        migrations.CreateModel(
            name='EventReview',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('rating', models.PositiveSmallIntegerField(help_text='Rating between 1 and 5.', validators=[MinValueValidator(1), MaxValueValidator(5)])),
                ('comment', models.TextField(blank=True, help_text='Optional comment justifying the rating.', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event', models.ForeignKey(help_text='Event that is being reviewed.', on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='events.event')),
                ('user', models.ForeignKey(help_text='The profile that submitted this review.', on_delete=django.db.models.deletion.CASCADE, related_name='event_reviews', to='profiles.profile')),
            ],
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Event Review',
                'verbose_name_plural': 'Event Reviews',
                'unique_together': (('event', 'user'),),
            },
        ),
    ]
