from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('counters', '0003_counterevent_actor'),
    ]

    operations = [
        migrations.AddField(
            model_name='counterevent',
            name='photo',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='event_photos/',
                verbose_name='Photo',
            ),
        ),
    ]
