from django.db import migrations, models
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0004_post_layout'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='show_trailing',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='post',
            name='trail_ids',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.UUIDField(), blank=True, default=list, size=None),
        ),
    ]
