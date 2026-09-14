from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CounterForm, StatusUpdateForm
from .models import Counter, CounterEvent


@login_required
def map_view(request):
    """Головна сторінка: карта з усіма лічильниками."""
    return render(request, 'counters/map.html')


@login_required
def counter_list(request):
    counters = Counter.objects.all()
    return render(request, 'counters/counter_list.html', {'counters': counters})


@login_required
def counters_json(request):
    """
    JSON зі списком усіх лічильників для відображення міток на карті.
    Викликається через fetch() з JS на клієнті.
    """
    counters = Counter.objects.all()
    data = [
        {
            'id': c.id,
            'name': c.name,
            'address': c.address,
            'lat': c.latitude,
            'lng': c.longitude,
            'status': c.status,
            'status_display': c.get_status_display(),
            'color': c.marker_color,
            'url': c.get_absolute_url(),
        }
        for c in counters
    ]
    return JsonResponse({'counters': data})


@login_required
def counter_add(request):
    """
    Додавання нового лічильника.
    Координати приходять з карти (клік по карті) як GET-параметри lat/lng.
    """
    initial = {}
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    if lat and lng:
        initial = {'latitude': lat, 'longitude': lng}

    if request.method == 'POST':
        form = CounterForm(request.POST)
        if form.is_valid():
            counter = form.save()
            # перший запис в історії — фіксуємо початковий статус
            CounterEvent.objects.create(
                counter=counter,
                status=counter.status,
                note='Počítadlo přidáno.',
            )
            messages.success(request, f'Počítadlo „{counter.name}" bylo přidáno.')
            return redirect('counter_detail', pk=counter.pk)
    else:
        if not lat or not lng:
            messages.info(request, 'Nejprve klikněte na mapu na požadovaném místě a zadejte souřadnice.')
            return redirect('map')
        form = CounterForm(initial=initial)

    return render(request, 'counters/counter_form.html', {'form': form, 'is_new': True})


@login_required
def counter_detail(request, pk):
    """Картка лічильника: інформація + історія подій + форма зміни статусу."""
    counter = get_object_or_404(Counter, pk=pk)
    events = counter.events.all()  # вже відсортовано за -created_at в Meta

    if request.method == 'POST':
        status_form = StatusUpdateForm(request.POST)
        if status_form.is_valid():
            event = status_form.save(commit=False)
            event.counter = counter
            event.save()
            # синхронізуємо поточний статус лічильника з останньою подією
            counter.status = event.status
            counter.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Stav byl aktualizován.')
            return redirect('counter_detail', pk=counter.pk)
    else:
        status_form = StatusUpdateForm(initial={'status': counter.status})

    return render(request, 'counters/counter_detail.html', {
        'counter': counter,
        'events': events,
        'status_form': status_form,
    })


@login_required
@require_POST
def counter_delete(request, pk):
    counter = get_object_or_404(Counter, pk=pk)
    name = counter.name
    counter.delete()
    messages.success(request, f'Počítadlo „{name}" bylo smazáno.')
    return redirect('map')


@login_required
@require_POST
def counter_clear_history(request, pk):
    """Smaže historii událostí počítadla; samotné počítadlo zůstane."""
    counter = get_object_or_404(Counter, pk=pk)
    # Dvojí potvrzení z formuláře — ochrana proti náhodnému odeslání
    if request.POST.get('confirm_clear') != 'yes':
        messages.error(request, 'Smazání historie nebylo potvrzeno.')
        return redirect('counter_detail', pk=counter.pk)

    deleted, _ = counter.events.all().delete()
    messages.success(
        request,
        f'Historie počítadla „{counter.name}" byla smazána ({deleted} záznamů).'
    )
    return redirect('counter_detail', pk=counter.pk)
