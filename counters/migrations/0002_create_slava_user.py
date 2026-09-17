from django.conf import settings
from django.db import migrations


def create_slava_user(apps, schema_editor):
    # Podpora pro případný custom user model
    app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    User = apps.get_model(app_label, model_name)

    if User.objects.filter(username='slava').exists():
        return

    # Pokus o vytvoření přes create_superuser; pokud selže, použij create_user a nastav práva
    try:
        User.objects.create_superuser(username='slava', email='', password='slava')
    except TypeError:
        u = User.objects.create_user('slava', email='', password='slava')
        u.is_staff = True
        u.is_superuser = True
        u.save()


class Migration(migrations.Migration):

    dependencies = [
        ('counters', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(create_slava_user, reverse_code=migrations.RunPython.noop),
    ]
