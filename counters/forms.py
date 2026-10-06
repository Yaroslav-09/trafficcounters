from django import forms
from django.core.exceptions import ValidationError

from .models import Counter, CounterEvent


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


class EventPhotoValidationMixin:
    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not photo or not self.files.get('photo'):
            return photo

        if photo.size > 8 * 1024 * 1024:
            raise ValidationError('Fotka může mít nejvýše 8 MB.')

        width, height = photo.image.size
        if width > 8000 or height > 8000 or width * height > 25_000_000:
            raise ValidationError('Rozlišení fotky je příliš vysoké.')

        return photo


class StatusUpdateForm(EventPhotoValidationMixin, forms.ModelForm):
    """Форма для додавання нового запису в історію (зміна статусу)."""

    class Meta:
        model = CounterEvent
        fields = ['status', 'note', 'photo']
        widgets = {
            'photo': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
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
