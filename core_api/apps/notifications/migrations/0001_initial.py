import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('profiles', '0007_profile_last_posted_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_type', models.CharField(choices=[('LIKE', 'Like'), ('COMMENT', 'Comment'), ('FOLLOW', 'Follow')], max_length=16)),
                ('object_id', models.UUIDField()),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='profiles.profile')),
            ],
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Notification',
                'verbose_name_plural': 'Notifications',
                'indexes': [
                    models.Index(fields=['recipient', 'is_read', 'created_at'], name='notifications_notification_recipient_is_read_created_at'),
                ],
            },
        ),
    ]
