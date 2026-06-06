# Generated manually for event extra URL fields and requirements

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0008_add_event_payment_and_reviews'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='requirements',
            field=models.JSONField(blank=True, default=list, help_text='List of logistical requirements for the event.'),
        ),
        migrations.AddField(
            model_name='event',
            name='support_email',
            field=models.CharField(blank=True, help_text='Support email address for the event.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='website_url',
            field=models.URLField(blank=True, help_text='Website URL for the event.', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='whatsapp_url',
            field=models.URLField(blank=True, help_text='WhatsApp URL for the event.', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='telegram_url',
            field=models.URLField(blank=True, help_text='Telegram URL for the event.', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='discord_url',
            field=models.URLField(blank=True, help_text='Discord URL for the event.', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='zoom_url',
            field=models.URLField(blank=True, help_text='Zoom URL for the event.', null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='secure_attendance_token',
            field=models.CharField(blank=True, help_text='Secure token used for attendance validation.', max_length=255, null=True),
        ),
    ]
