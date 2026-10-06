from django.db import migrations


def harden_seeded_default_user(apps, schema_editor):
    """
    Pokud v DB zbyl účet ze staré seed migrace se známým slabým heslem,
    deaktivuj ho a zneplatni heslo. Legitimní účty se silným heslem nechá.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(username='slava')
    except User.DoesNotExist:
        return

    # Kontrola jen proti historicky seedovanému heslu; jiné heslo = nechat.
    if not user.has_usable_password() or not user.check_password('slava'):
        return

    user.set_unusable_password()
    user.is_active = False
    user.save(update_fields=['password', 'is_active'])


class Migration(migrations.Migration):

    dependencies = [
        ('counters', '0004_counterevent_photo'),
    ]

    operations = [
        migrations.RunPython(
            harden_seeded_default_user,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
