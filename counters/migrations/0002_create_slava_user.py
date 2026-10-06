from django.conf import settings
from django.db import migrations


def create_slava_user(apps, schema_editor):
    # Účty se nesmí seedovat z migrací (slabé/ pevné heslo v kódu).
    # Vytvoř admin účet: python manage.py createsuperuser
    return


class Migration(migrations.Migration):

    dependencies = [
        ('counters', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(create_slava_user, reverse_code=migrations.RunPython.noop),
    ]
