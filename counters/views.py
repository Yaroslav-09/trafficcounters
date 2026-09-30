import mimetypes
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, connection
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CounterForm, StatusUpdateForm
from .models import Counter, CounterEvent


def staff_required(view_func):
    """Only authenticated staff accounts can view or change business data."""
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if not request.user.is_active or not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped_view


def healthz(request):
    """Readiness check pro Render: aplikace i databáze musí být dostupné."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except DatabaseError:
        return HttpResponse('unavailable', content_type='text/plain', status=503)
    return HttpResponse('ok', content_type='text/plain')


@staff_required
def map_view(request):
    """Головна сторінка: карта з усіма лічильниками."""
    return render(request, 'counters/map.html')


@staff_required
def counter_list(request):
    counters = Counter.objects.all()
    return render(request, 'counters/counter_list.html', {'counters': counters})


@staff_required
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


@staff_required
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
                actor=request.user,
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


@staff_required
def counter_detail(request, pk):
    """Картка лічильника: інформація + історія подій + форма зміни статусу."""
    counter = get_object_or_404(Counter, pk=pk)
    events = counter.events.all()  # вже відсортовано за -created_at в Meta

    if request.method == 'POST':
        status_form = StatusUpdateForm(request.POST, request.FILES)
        if status_form.is_valid():
            event = status_form.save(commit=False)
            event.counter = counter
            event.actor = request.user
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


@staff_required
def counter_event_photo(request, pk):
    event = get_object_or_404(CounterEvent.objects.only('photo'), pk=pk)
    if not event.photo:
        raise Http404

    content_type, _ = mimetypes.guess_type(event.photo.name)
    if not content_type or not content_type.startswith('image/'):
        content_type = 'application/octet-stream'

    try:
        photo_file = event.photo.open('rb')
    except OSError as error:
        raise Http404 from error

    response = FileResponse(photo_file, content_type=content_type)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response


@staff_required
@require_POST
def counter_delete(request, pk):
    counter = get_object_or_404(Counter, pk=pk)
    name = counter.name
    counter.delete()
    messages.success(request, f'Počítadlo „{name}" bylo smazáno.')
    return redirect('map')


@staff_required
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
