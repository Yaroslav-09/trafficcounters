from django import forms
from django.core.exceptions import ValidationError

from .models import Counter, CounterEvent

# Přibližný bounding box ČR (stejný jako na mapě).
CZECHIA_LAT_MIN, CZECHIA_LAT_MAX = 48.35, 51.15
CZECHIA_LNG_MIN, CZECHIA_LNG_MAX = 11.85, 19.10
ALLOWED_IMAGE_FORMATS = frozenset({'JPEG', 'PNG', 'GIF', 'WEBP'})


class CounterForm(forms.ModelForm):
    class Meta:
        model = Counter
        fields = ['name', 'address', 'latitude', 'longitude', 'status', 'description']
        widgets = {
            'latitude': forms.NumberInput(attrs={'step': 'any', 'readonly': 'readonly'}),
            'longitude': forms.NumberInput(attrs={'step': 'any', 'readonly': 'readonly'}),
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

    def clean_latitude(self):
        lat = self.cleaned_data['latitude']
        if not (CZECHIA_LAT_MIN <= lat <= CZECHIA_LAT_MAX):
            raise ValidationError('Zeměpisná šířka musí být v rozsahu České republiky.')
        return lat

    def clean_longitude(self):
        lng = self.cleaned_data['longitude']
        if not (CZECHIA_LNG_MIN <= lng <= CZECHIA_LNG_MAX):
            raise ValidationError('Zeměpisná délka musí být v rozsahu České republiky.')
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
        labels = {
            'status': 'Nový stav',
            'note': 'Komentář',
        }


class CounterEventAdminForm(EventPhotoValidationMixin, forms.ModelForm):
    class Meta:
        model = CounterEvent
        fields = '__all__'
