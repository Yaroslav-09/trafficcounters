from django.conf import settings
from django.db import models
from django.urls import reverse


class Counter(models.Model):
    """Фізичний лічильник людей, встановлений десь на місцевості."""

    STATUS_WORKING = 'working'
    STATUS_DEFECT = 'defect'
    STATUS_DISABLED = 'disabled'

    STATUS_CHOICES = [
        (STATUS_WORKING, 'V provozu'),
        (STATUS_DEFECT, 'Porucha'),
        (STATUS_DISABLED, 'Vypnuto'),
    ]

    STATUS_COLORS = {
        STATUS_WORKING: '#2e8b57',   # зелений
        STATUS_DEFECT: '#d64545',    # червоний
        STATUS_DISABLED: '#9a9a9a',  # сірий
    }

    name = models.CharField('Název', max_length=150)
    address = models.CharField('Adresa / orientační bod', max_length=255, blank=True)
    latitude = models.FloatField('Zeměpisná šířka')
    longitude = models.FloatField('Zeměpisná délka')
    status = models.CharField(
        'Stav', max_length=20, choices=STATUS_CHOICES, default=STATUS_WORKING
    )
    description = models.TextField('Popis', blank=True)
    created_at = models.DateTimeField('Přidáno', auto_now_add=True)
    updated_at = models.DateTimeField('Aktualizováno', auto_now=True)

    class Meta:
        verbose_name = 'Počítadlo'
        verbose_name_plural = 'Počítadla'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.get_status_display()})'

    def get_absolute_url(self):
        return reverse('counter_detail', args=[self.pk])

    @property
    def marker_color(self):
        return self.STATUS_COLORS.get(self.status, '#3388ff')


class CounterEvent(models.Model):
    """
    Запис в історії лічильника: зміна статусу з нотаткою.
    Кожна зміна статусу (додали дефект, полагодили, знову ввели в роботу)
    зберігається окремим рядком — так завжди видно повну історію обслуговування.
    """

    counter = models.ForeignKey(
        Counter, related_name='events', on_delete=models.CASCADE, verbose_name='Počítadlo'
    )
    status = models.CharField(
        'Stav', max_length=20, choices=Counter.STATUS_CHOICES
    )
    note = models.TextField('Komentář', blank=True)
    created_at = models.DateTimeField('Datum', auto_now_add=True)

    class Meta:
        verbose_name = 'Událost'
        verbose_name_plural = 'Historie událostí'
        ordering = ['-created_at']

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='counter_events',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='User',
    )

    def __str__(self):
        return f'{self.counter.name}: {self.get_status_display()} ({self.created_at:%d.%m.%Y %H:%M})'
