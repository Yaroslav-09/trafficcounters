from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Client, Counter, CounterEvent, CounterInspection, CounterType

ALLOWED_IMAGE_FORMATS = frozenset({'JPEG', 'PNG', 'GIF', 'WEBP'})


class CounterForm(forms.ModelForm):
    client_name = forms.CharField(
        label='Klient, kterému sčítač patří',
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'list': 'client-suggestions',
            'placeholder': 'Vyberte nebo napište nového klienta',
            'autocomplete': 'off',
        }),
    )
    counter_type_name = forms.CharField(
        label='Typ sčítače',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'list': 'counter-type-suggestions',
            'placeholder': 'Vyberte nebo napište nový typ',
            'autocomplete': 'off',
        }),
    )

    class Meta:
        model = Counter
        fields = [
            'name', 'client_name', 'counter_type_name', 'address', 'latitude', 'longitude',
            'status', 'description',
        ]
        widgets = {
            'latitude': forms.NumberInput(attrs={'step': 'any', 'placeholder': 'Např. 50.087451'}),
            'longitude': forms.NumberInput(attrs={'step': 'any', 'placeholder': 'Např. 14.420671'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'name': 'Název počítadla',
            'address': 'Adresa / orientační bod',
            'latitude': 'Zeměpisná šířka',
            'longitude': 'Zeměpisná délka',
            'status': 'Počáteční stav',
            'description': 'Popis',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_names = Client.objects.filter(is_active=True).values_list('name', flat=True)
        self.counter_type_names = CounterType.objects.filter(is_active=True).values_list('name', flat=True)

    def save(self, commit=True):
        """Najde existujícího klienta/typ, nebo ho vytvoří podle zadaného názvu."""
        with transaction.atomic():
            client_name = self.cleaned_data.get('client_name', '').strip()
            type_name = self.cleaned_data.get('counter_type_name', '').strip()

            self.instance.client = self._get_or_create_named(Client, client_name)
            self.instance.counter_type = self._get_or_create_named(CounterType, type_name)
            return super().save(commit=commit)

    @staticmethod
    def _get_or_create_named(model, name):
        if not name:
            return None
        existing = model.objects.filter(name__iexact=name).first()
        return existing or model.objects.create(name=name)

    def clean_latitude(self):
        lat = self.cleaned_data['latitude']
        if not -90 <= lat <= 90:
            raise ValidationError('Zeměpisná šířka musí být mezi -90 a 90 stupni.')
        return lat

    def clean_longitude(self):
        lng = self.cleaned_data['longitude']
        if not -180 <= lng <= 180:
            raise ValidationError('Zeměpisná délka musí být mezi -180 a 180 stupni.')
        return lng


class EventPhotoValidationMixin:
    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not photo or not self.files.get('photo'):
            return photo

        if photo.size > 8 * 1024 * 1024:
            raise ValidationError('Fotka může mít nejvýše 8 MB.')

        from PIL import Image

        try:
            photo.seek(0)
            with Image.open(photo) as image:
                fmt = (image.format or '').upper()
                width, height = image.size
                # load() odhalí poškozené / zkrácené soubory dřív než uložení
                image.load()
        except Exception as exc:
            raise ValidationError('Soubor není platný obrázek.') from exc
        finally:
            photo.seek(0)

        if fmt not in ALLOWED_IMAGE_FORMATS:
            raise ValidationError('Povolené formáty fotky: JPEG, PNG, GIF, WEBP.')

        if width > 8000 or height > 8000 or width * height > 25_000_000:
            raise ValidationError('Rozlišení fotky je příliš vysoké.')

        return photo


class StatusUpdateForm(EventPhotoValidationMixin, forms.ModelForm):
    """Форма для додавання нового запису в історію (зміна статусу)."""

    class Meta:
        model = CounterEvent
        fields = ['status', 'note', 'photo']
        widgets = {
            'photo': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/gif,image/webp'}),
            'note': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Např.: vyměněn senzor, nyní funguje správně'}),
        }


class CounterInspectionForm(forms.ModelForm):
    class Meta:
        model = CounterInspection
        fields = ['inspected_at', 'result', 'note', 'next_inspection_at']
        widgets = {
            'inspected_at': forms.DateInput(attrs={'type': 'date'}),
            'next_inspection_at': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        inspected_at = cleaned_data.get('inspected_at')
        next_inspection_at = cleaned_data.get('next_inspection_at')
        if inspected_at and next_inspection_at and next_inspection_at < inspected_at:
            self.add_error('next_inspection_at', 'Další kontrola nemůže být před datem této kontroly.')
        return cleaned_data
        labels = {
            'status': 'Nový stav',
            'note': 'Komentář',
        }


class CounterEventAdminForm(EventPhotoValidationMixin, forms.ModelForm):
    class Meta:
        model = CounterEvent
        fields = '__all__'
