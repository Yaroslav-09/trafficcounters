from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Client(models.Model):
    name = models.CharField('Klient', max_length=150, unique=True)
    contact_person = models.CharField('Kontaktní osoba', max_length=150, blank=True)
    email = models.EmailField('E-mail', blank=True)
    phone = models.CharField('Telefon', max_length=40, blank=True)
    is_active = models.BooleanField('Aktivní', default=True)
    notes = models.TextField('Poznámka', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Klient'
        verbose_name_plural = 'Klienti'

    def __str__(self):
        return self.name


class CounterType(models.Model):
    name = models.CharField('Typ sčítače', max_length=100, unique=True)
    description = models.CharField('Popis', max_length=255, blank=True)
    is_active = models.BooleanField('Aktivní', default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Typ sčítače'
        verbose_name_plural = 'Typy sčítačů'

    def __str__(self):
        return self.name


class Counter(models.Model):
    """Fyzický sčítač lidí umístěný v terénu."""

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
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, null=True, blank=True,
        related_name='counters', verbose_name='Klient',
    )
    counter_type = models.ForeignKey(
        CounterType, on_delete=models.PROTECT, null=True, blank=True,
        related_name='counters', verbose_name='Typ sčítače',
    )
    created_at = models.DateTimeField('Přidáno', auto_now_add=True)
    updated_at = models.DateTimeField('Aktualizováno', auto_now=True)

    class Meta:
        verbose_name = 'Sčítač'
        verbose_name_plural = 'Sčítače'
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
    Záznam v historii sčítače: změna stavu s poznámkou.
    Každá změna stavu se ukládá zvlášť, aby byla vidět celá historie servisu.
    """

    counter = models.ForeignKey(
        Counter, related_name='events', on_delete=models.CASCADE, verbose_name='Sčítač'
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
    photo = models.ImageField(
        upload_to='event_photos/',
        blank=True,
        null=True,
        verbose_name='Photo',
    )

    def __str__(self):
        return f'{self.counter.name}: {self.get_status_display()} ({self.created_at:%d.%m.%Y %H:%M})'


class CounterInspection(models.Model):
    RESULT_OK = 'ok'
    RESULT_ISSUE = 'issue'
    RESULT_CHOICES = [
        (RESULT_OK, 'V pořádku'),
        (RESULT_ISSUE, 'Zjištěna závada'),
    ]

    counter = models.ForeignKey(
        Counter, related_name='inspections', on_delete=models.CASCADE,
        verbose_name='Sčítač',
    )
    inspected_at = models.DateField('Datum kontroly', default=timezone.localdate)
    result = models.CharField('Výsledek', max_length=10, choices=RESULT_CHOICES)
    note = models.TextField('Poznámka ke kontrole', blank=True)
    next_inspection_at = models.DateField(
        'Další kontrola', null=True, blank=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='counter_inspections',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Kontroloval(a)',
    )
    created_at = models.DateTimeField('Zapsáno', auto_now_add=True)

    class Meta:
        ordering = ['-inspected_at', '-created_at']
        verbose_name = 'Kontrola sčítače'
        verbose_name_plural = 'Kontroly sčítačů'

    def __str__(self):
        return f'{self.counter.name}: {self.get_result_display()} ({self.inspected_at:%d.%m.%Y})'
