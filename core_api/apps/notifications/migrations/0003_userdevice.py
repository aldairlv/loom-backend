# Generated migration for UserDevice model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('notifications', '0002_rename_notifications_notification_recipient_is_read_created_at_notificatio_recipie_86ea8b_idx'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserDevice',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('device_id', models.CharField(help_text='ID único del hardware', max_length=255, unique=True)),
                ('registration_token', models.TextField(help_text='Token de Firebase/APNS', unique=True)),
                ('device_type', models.CharField(choices=[('android', 'Android'), ('ios', 'iOS'), ('web', 'Web')], default='android', max_length=10)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='devices', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Device',
                'verbose_name_plural': 'User Devices',
            },
        ),
        migrations.AddIndex(
            model_name='userdevice',
            index=models.Index(fields=['account', 'is_active'], name='notifications_account_is_active_idx'),
        ),
    ]
