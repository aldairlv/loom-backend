# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='media',
            name='original_filename',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
