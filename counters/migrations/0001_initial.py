from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Counter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, verbose_name='Назва')),
                ('address', models.CharField(blank=True, max_length=255, verbose_name='Адреса / орієнтир')),
                ('latitude', models.FloatField(verbose_name='Широта')),
                ('longitude', models.FloatField(verbose_name='Довгота')),
                ('status', models.CharField(
                    choices=[('working', 'Працює'), ('defect', 'Несправний'), ('disabled', 'Вимкнений')],
                    default='working', max_length=20, verbose_name='Статус'
                )),
                ('description', models.TextField(blank=True, verbose_name='Опис')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Додано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Оновлено')),
            ],
            options={
                'verbose_name': 'Лічильник',
                'verbose_name_plural': 'Лічильники',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='CounterEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[('working', 'Працює'), ('defect', 'Несправний'), ('disabled', 'Вимкнений')],
                    max_length=20, verbose_name='Статус'
                )),
                ('note', models.TextField(blank=True, verbose_name='Коментар')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата')),
                ('counter', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='events',
                    to='counters.counter', verbose_name='Лічильник'
                )),
            ],
            options={
                'verbose_name': 'Подія',
                'verbose_name_plural': 'Історія подій',
                'ordering': ['-created_at'],
            },
        ),
    ]
