from django import forms

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


class StatusUpdateForm(forms.ModelForm):
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
