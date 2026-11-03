from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client as WebClient, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Client, Counter, CounterEvent, CounterInspection, CounterType


class CounterManagementTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='operator', password='test-password', is_staff=True,
        )
        self.web = WebClient()
        self.web.force_login(self.user)
        self.client_record = Client.objects.create(name='Klient A')
        self.counter_type = CounterType.objects.create(name='Infračervený')
        self.counter = Counter.objects.create(
            name='Sčítač Praha',
            address='Praha',
            latitude=50.08,
            longitude=14.42,
            status=Counter.STATUS_WORKING,
            client=self.client_record,
            counter_type=self.counter_type,
        )

    def test_list_filters_by_status_client_and_type(self):
        Counter.objects.create(
            name='Sčítač Brno', address='Brno', latitude=49.2, longitude=16.6,
            status=Counter.STATUS_DEFECT,
        )

        response = self.web.get(reverse('counter_list'), {
            'status': Counter.STATUS_WORKING,
            'client': self.client_record.pk,
            'type': self.counter_type.pk,
            'sort': '-name',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['counters']), [self.counter])
        self.assertContains(response, 'Klient A')

    def test_detail_and_add_form_render_for_staff(self):
        detail = self.web.get(reverse('counter_detail', args=[self.counter.pk]))
        add_form = self.web.get(reverse('counter_add'), {'lat': '50.08', 'lng': '14.42'})

        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, 'Kontrola sčítače')
        self.assertContains(detail, 'Klient A')
        self.assertEqual(add_form.status_code, 200)
        self.assertContains(add_form, 'Klient, kterému sčítač patří')
        self.assertContains(add_form, 'Typ sčítače')

    def test_counter_add_form_saves_with_client_and_type(self):
        response = self.web.post(reverse('counter_add'), {
            'name': 'Nový sčítač',
            'client': self.client_record.pk,
            'counter_type': self.counter_type.pk,
            'address': 'Praha',
            'latitude': '50.08',
            'longitude': '14.42',
            'status': Counter.STATUS_WORKING,
            'description': '',
        })

        created = Counter.objects.get(name='Nový sčítač')
        self.assertRedirects(response, reverse('counter_detail', args=[created.pk]))
        self.assertEqual(created.client, self.client_record)
        self.assertEqual(created.counter_type, self.counter_type)

    def test_due_filter_includes_never_inspected_and_overdue_counters(self):
        overdue_date = timezone.localdate() - timedelta(days=1)
        CounterInspection.objects.create(
            counter=self.counter,
            inspected_at=overdue_date - timedelta(days=30),
            result=CounterInspection.RESULT_OK,
            next_inspection_at=overdue_date,
            actor=self.user,
        )
        never_checked = Counter.objects.create(
            name='Sčítač bez kontroly', address='', latitude=50.1, longitude=14.4,
        )

        response = self.web.get(reverse('counter_list'), {'check': 'due'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context['counters']), {never_checked, self.counter})

    def test_verification_filter_is_independent_from_operational_status(self):
        self.counter.status = Counter.STATUS_DEFECT
        self.counter.save(update_fields=['status'])
        CounterInspection.objects.create(
            counter=self.counter,
            inspected_at=timezone.localdate(),
            result=CounterInspection.RESULT_OK,
            next_inspection_at=timezone.localdate() + timedelta(days=30),
            actor=self.user,
        )

        response = self.web.get(reverse('counter_list'), {'check': 'verified'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['counters']), [self.counter])
        self.assertContains(response, 'Ověřeno · v pořádku')
        self.assertContains(response, 'Porucha')
        self.assertEqual(response.context['verification_totals']['verified'], 1)

    def test_failed_inspection_marks_counter_defective_and_records_actor(self):
        response = self.web.post(reverse('counter_detail', args=[self.counter.pk]), {
            'inspection_submit': '1',
            'inspected_at': timezone.localdate().isoformat(),
            'result': CounterInspection.RESULT_ISSUE,
            'note': 'Poškozený senzor',
            'next_inspection_at': '',
        })

        self.assertRedirects(response, reverse('counter_detail', args=[self.counter.pk]))
        self.counter.refresh_from_db()
        self.assertEqual(self.counter.status, Counter.STATUS_DEFECT)
        inspection = CounterInspection.objects.get(counter=self.counter)
        self.assertEqual(inspection.actor, self.user)
        event = CounterEvent.objects.get(counter=self.counter)
        self.assertEqual(event.status, Counter.STATUS_DEFECT)
        self.assertEqual(event.actor, self.user)

    def test_successful_inspection_returns_counter_to_service(self):
        self.counter.status = Counter.STATUS_DEFECT
        self.counter.save(update_fields=['status'])

        self.web.post(reverse('counter_detail', args=[self.counter.pk]), {
            'inspection_submit': '1',
            'inspected_at': timezone.localdate().isoformat(),
            'result': CounterInspection.RESULT_OK,
            'note': 'Ověřeno při pravidelné kontrole',
            'next_inspection_at': '',
        })

        self.counter.refresh_from_db()
        self.assertEqual(self.counter.status, Counter.STATUS_WORKING)
        self.assertEqual(CounterEvent.objects.get(counter=self.counter).status, Counter.STATUS_WORKING)

    def test_map_data_exposes_verification_separately_from_operational_status(self):
        self.counter.status = Counter.STATUS_DEFECT
        self.counter.save(update_fields=['status'])
        CounterInspection.objects.create(
            counter=self.counter,
            inspected_at=timezone.localdate(),
            result=CounterInspection.RESULT_OK,
            next_inspection_at=timezone.localdate() + timedelta(days=30),
            actor=self.user,
        )

        response = self.web.get(reverse('counters_json'))

        self.assertEqual(response.status_code, 200)
        counter_data = next(
            item for item in response.json()['counters'] if item['id'] == self.counter.pk
        )
        self.assertTrue(counter_data['is_verified'])
        self.assertFalse(counter_data['verification_overdue'])
        self.assertEqual(counter_data['status'], Counter.STATUS_DEFECT)
        self.assertEqual(counter_data['last_inspection_result'], CounterInspection.RESULT_OK)
