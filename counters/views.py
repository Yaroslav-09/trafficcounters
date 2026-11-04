import mimetypes
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import DatabaseError, connection
from django.db.models import F, OuterRef, Q, Subquery
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CounterForm, CounterInspectionForm, StatusUpdateForm
from .models import Client, Counter, CounterEvent, CounterInspection, CounterType


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
    latest_inspection = CounterInspection.objects.filter(
        counter_id=OuterRef('pk')
    ).order_by('-inspected_at', '-created_at')
    annotated_counters = Counter.objects.select_related('client', 'counter_type').annotate(
        last_inspection_date=Subquery(latest_inspection.values('inspected_at')[:1]),
        next_inspection_date=Subquery(latest_inspection.values('next_inspection_at')[:1]),
        last_inspection_result=Subquery(latest_inspection.values('result')[:1]),
        last_inspector=Subquery(latest_inspection.values('actor__username')[:1]),
    )
    counters = annotated_counters
    today = timezone.localdate()

    status_filter = request.GET.get('status', '')
    client_filter = request.GET.get('client', '')
    type_filter = request.GET.get('type', '')
    check_filter = request.GET.get('check', '')
    search = request.GET.get('q', '').strip()[:100]
    sort = request.GET.get('sort', 'name')

    if status_filter in dict(Counter.STATUS_CHOICES):
        counters = counters.filter(status=status_filter)
    if client_filter.isdigit():
        counters = counters.filter(client_id=int(client_filter))
    if type_filter.isdigit():
        counters = counters.filter(counter_type_id=int(type_filter))
    if search:
        counters = counters.filter(
            Q(name__icontains=search)
            | Q(address__icontains=search)
            | Q(client__name__icontains=search)
            | Q(counter_type__name__icontains=search)
        )
    if check_filter == 'verified':
        counters = counters.filter(last_inspection_date__isnull=False).filter(
            Q(next_inspection_date__isnull=True) | Q(next_inspection_date__gt=today)
        )
    elif check_filter == 'unverified':
        counters = counters.filter(last_inspection_date__isnull=True)
    elif check_filter == 'overdue':
        counters = counters.filter(next_inspection_date__lte=today)
    elif check_filter == 'due':
        counters = counters.filter(
            Q(last_inspection_date__isnull=True)
            | Q(next_inspection_date__lte=today)
        )

    sort_options = {
        'name': 'name', '-name': '-name',
        'status': 'status', '-status': '-status',
        'client': 'client__name', '-client': '-client__name',
        'type': 'counter_type__name', '-type': '-counter_type__name',
        'verified_newest': F('last_inspection_date').desc(nulls_last=True),
        'verified_oldest': F('last_inspection_date').asc(nulls_first=True),
        'updated': '-updated_at', 'oldest': 'updated_at',
    }
    if sort not in sort_options:
        sort = 'name'
    counters = counters.order_by(sort_options[sort], 'name')

    page_obj = Paginator(counters, 25).get_page(request.GET.get('page'))
    query_params = request.GET.copy()
    query_params.pop('page', None)
    status_totals = {
        status: Counter.objects.filter(status=status).count()
        for status, _label in Counter.STATUS_CHOICES
    }
    verification_totals = {
        'verified': annotated_counters.filter(last_inspection_date__isnull=False).filter(
            Q(next_inspection_date__isnull=True) | Q(next_inspection_date__gt=today)
        ).count(),
        'unverified': Counter.objects.filter(inspections__isnull=True).distinct().count(),
        'overdue': annotated_counters.filter(next_inspection_date__lte=today).count(),
    }
    return render(request, 'counters/counter_list.html', {
        'page_obj': page_obj,
        'counters': page_obj.object_list,
        'clients': Client.objects.order_by('name'),
        'counter_types': CounterType.objects.order_by('name'),
        'status_choices': Counter.STATUS_CHOICES,
        'status_totals': status_totals,
        'total_counters': Counter.objects.count(),
        'today': today,
        'verification_totals': verification_totals,
        'filter_query': query_params.urlencode(),
        'filters': {
            'status': status_filter, 'client': client_filter,
            'type': type_filter, 'check': check_filter,
            'q': search, 'sort': sort,
        },
    })


@staff_required
def counters_json(request):
    """
    JSON зі списком усіх лічильників для відображення міток на карті.
    Викликається через fetch() з JS на клієнті.
    """
    latest_inspection = CounterInspection.objects.filter(
        counter_id=OuterRef('pk')
    ).order_by('-inspected_at', '-created_at')
    counters = Counter.objects.select_related('client', 'counter_type').annotate(
        last_inspection_date=Subquery(latest_inspection.values('inspected_at')[:1]),
        next_inspection_date=Subquery(latest_inspection.values('next_inspection_at')[:1]),
        last_inspection_result=Subquery(latest_inspection.values('result')[:1]),
        last_inspector=Subquery(latest_inspection.values('actor__username')[:1]),
    )
    today = timezone.localdate()
    result_labels = dict(CounterInspection.RESULT_CHOICES)
    data = []
    for c in counters:
        overdue = bool(c.next_inspection_date and c.next_inspection_date <= today)
        data.append({
            'id': c.id,
            'name': c.name,
            'address': c.address,
            'lat': c.latitude,
            'lng': c.longitude,
            'status': c.status,
            'status_display': c.get_status_display(),
            'color': c.marker_color,
            'client': c.client.name if c.client_id else '',
            'counter_type': c.counter_type.name if c.counter_type_id else '',
            'last_inspection_date': c.last_inspection_date.isoformat() if c.last_inspection_date else '',
            'next_inspection_date': c.next_inspection_date.isoformat() if c.next_inspection_date else '',
            'last_inspection_result': c.last_inspection_result or '',
            'last_inspection_result_display': result_labels.get(c.last_inspection_result, ''),
            'last_inspector': c.last_inspector or '',
            'is_verified': bool(c.last_inspection_date and not overdue),
            'verification_overdue': overdue,
            'url': c.get_absolute_url(),
        })
    return JsonResponse({'counters': data})


@staff_required
def counter_add(request):
    """
    Додавання нового лічильника: координати можна взяти з карти або ввести вручну.
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
        form = CounterForm(initial=initial)

    return render(request, 'counters/counter_form.html', {
        'form': form,
        'is_new': True,
        'client_names': form.client_names,
        'counter_type_names': form.counter_type_names,
    })


@staff_required
def counter_detail(request, pk):
    """Картка лічильника: інформація + історія подій + форма зміни статусу."""
    counter = get_object_or_404(Counter, pk=pk)
    events = counter.events.all()  # вже відсортовано за -created_at в Meta
    inspections = counter.inspections.select_related('actor')

    if request.method == 'POST':
        if 'inspection_submit' in request.POST:
            inspection_form = CounterInspectionForm(request.POST)
            status_form = StatusUpdateForm(initial={'status': counter.status})
            if inspection_form.is_valid():
                inspection = inspection_form.save(commit=False)
                inspection.counter = counter
                inspection.actor = request.user
                inspection.save()

                new_status = (
                    Counter.STATUS_DEFECT
                    if inspection.result == CounterInspection.RESULT_ISSUE
                    else Counter.STATUS_WORKING
                )
                if counter.status != new_status:
                    counter.status = new_status
                    counter.save(update_fields=['status', 'updated_at'])
                    CounterEvent.objects.create(
                        counter=counter,
                        actor=request.user,
                        status=new_status,
                        note='Stav byl aktualizován na základě kontroly.',
                    )
                messages.success(request, 'Kontrola sčítače byla uložena.')
                return redirect('counter_detail', pk=counter.pk)
        else:
            status_form = StatusUpdateForm(request.POST, request.FILES)
            inspection_form = CounterInspectionForm()
            if status_form.is_valid():
                event = status_form.save(commit=False)
                event.counter = counter
                event.actor = request.user
                event.save()
                counter.status = event.status
                counter.save(update_fields=['status', 'updated_at'])
                messages.success(request, 'Stav byl aktualizován.')
                return redirect('counter_detail', pk=counter.pk)
    else:
        status_form = StatusUpdateForm(initial={'status': counter.status})
        inspection_form = CounterInspectionForm()

    return render(request, 'counters/counter_detail.html', {
        'counter': counter,
        'events': events,
        'inspections': inspections,
        'status_form': status_form,
        'inspection_form': inspection_form,
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

    response = FileResponse(photo_file, content_type=content_type, as_attachment=False)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    response['Content-Disposition'] = 'inline'
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
