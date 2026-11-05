from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.db.models.deletion import ProtectedError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from .models import Office, Visit, Visitor


class VisitorWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user('security', password='test-password')
        cls.admin = get_user_model().objects.create_superuser('administrator', password='test-password')
        cls.office = Office.objects.create(office_name='Registrar', location='Main building')

    def setUp(self):
        self.client.force_login(self.staff)
        self.data = dict(first_name='Maria', last_name='Santos', contact_number='09171234567',
                         address='Manila', visitor_type='Parent/Guardian', purpose='Request school records',
                         office=self.office.pk, person_to_visit='Registrar staff')

    def register(self, **changes):
        return self.client.post(reverse('register_visitor'), self.data | changes)

    def test_complete_workflow_and_returning_visitor(self):
        self.assertRedirects(self.register(), reverse('active_visitors'))
        visit = Visit.objects.get()
        self.assertEqual(visit.visitor.first_name, 'Maria')
        self.assertEqual(visit.visitor.last_name, 'Santos')
        self.assertEqual(visit.recorded_by, self.staff)
        self.assertEqual(visit.status, 'Inside')
        self.assertIsNone(visit.time_out)
        response = self.client.get(reverse('register_visitor'), {'q': 'Maria Santos'})
        self.assertContains(response, 'Use profile')
        response = self.client.get(reverse('register_visitor'), {'visitor': visit.visitor_id})
        self.assertEqual(response.context['form'].initial['first_name'], 'Maria')
        self.client.post(reverse('active_visitors'), {'visit_id': visit.pk})
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'Completed')
        self.assertIsNotNone(visit.time_out)
        original_time = visit.time_out
        self.client.post(reverse('active_visitors'), {'visit_id': visit.pk})
        visit.refresh_from_db()
        self.assertEqual(visit.time_out, original_time)
        self.assertContains(self.client.get(reverse('visitor_history')), 'Maria Santos')
        self.assertRedirects(self.register(visitor=visit.visitor_id), reverse('active_visitors'))
        self.assertEqual(Visitor.objects.count(), 1)
        self.assertEqual(Visit.objects.count(), 2)

    def test_reuse_exact_profile_without_selected_id_and_block_duplicate_arrival(self):
        self.register()
        response = self.register()
        self.assertContains(response, 'already inside')
        self.assertEqual(Visit.objects.count(), 1)
        self.client.post(reverse('active_visitors'), {'visit_id': Visit.objects.get().pk})
        self.assertRedirects(self.register(first_name='MARIA'), reverse('active_visitors'))
        self.assertEqual(Visitor.objects.count(), 1)

    def test_invalid_input_is_preserved_and_writes_nothing(self):
        for changes, field in [({'office': 'bad'}, 'office'), ({'office': 999999}, 'office'),
                               ({'visitor_type': 'Student'}, 'visitor_type'),
                               ({'contact_number': 'abc'}, 'contact_number'),
                               ({'first_name': ' '}, 'first_name'),
                               ({'last_name': 'S' * 101}, 'last_name'),
                               ({'visitor': 999999}, 'visitor'), ({'address': ''}, 'address')]:
            with self.subTest(field=field, changes=changes):
                response = self.register(**changes)
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context['form'].errors)
                self.assertContains(response, 'Request school records')
                self.assertEqual(Visit.objects.count(), 0)
                self.assertEqual(Visitor.objects.count(), 0)

    def test_filters_and_reports_agree(self):
        self.register()
        filters = {'q': 'Maria Santos', 'visitor_type': 'Parent/Guardian', 'office': self.office.pk,
                   'status': 'Inside', 'date_from': timezone.localdate().isoformat(),
                   'date_to': timezone.localdate().isoformat()}
        for route in ('visitor_history', 'active_visitors'):
            response = self.client.get(reverse(route), filters)
            self.assertContains(response, 'Maria Santos')
            self.assertEqual(response.context['page_obj'].paginator.count, 1)
            self.assertEqual(self.client.get(reverse(route), {'q': 'nobody'}).context['page_obj'].paginator.count, 0)
        response = self.client.get(reverse('reports'), filters)
        self.assertEqual(response.context['total_visits'], 1)
        self.assertEqual(response.context['inside'], 1)
        self.assertEqual(self.client.get(reverse('reports'), {'status': 'Completed'}).context['total_visits'], 0)
        for filters in ({'office': 'bad'}, {'date_from': 'invalid'}, {'date_from': '2026-11-05', 'date_to': '2026-11-01'}):
            response = self.client.get(reverse('visitor_history'), filters)
            self.assertTrue(response.context['form'].errors)
            self.assertEqual(response.context['page_obj'].paginator.count, 0)

    def test_dashboard_uses_manila_dates_and_zero_filled_trend(self):
        self.register()
        today = timezone.localdate()
        local_midnight = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        Visit.objects.update(time_in=local_midnight + timedelta(minutes=1))
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['visitors_today'], 1)
        self.assertEqual(len(response.context['trend']), 7)
        self.assertEqual(response.context['trend'][-1]['total'], 1)
        self.assertEqual(response.context['trend'][0]['total'], 0)
        month_response = self.client.get(reverse('dashboard'), {'period': 'month'})
        self.assertEqual(len(month_response.context['trend']), 30)
        self.assertEqual(month_response.context['trend_total'], 1)
        self.assertEqual(month_response.context['total_visits'], 1)
        self.assertEqual(sum(item['total'] for item in month_response.context['type_summary']), 1)
        self.assertEqual(len(self.client.get(reverse('dashboard'), {'period': 'invalid'}).context['trend']), 7)
        Visit.objects.update(time_in=local_midnight - timedelta(minutes=1))
        self.assertEqual(self.client.get(reverse('dashboard')).context['visitors_today'], 0)

    def test_access_and_logout(self):
        anonymous = Client()
        for route in ('dashboard', 'register_visitor', 'active_visitors', 'visitor_history', 'reports'):
            self.assertEqual(anonymous.get(reverse(route)).status_code, 302)
        self.assertNotContains(self.client.get(reverse('dashboard')), 'School Offices')
        self.assertEqual(self.client.get(reverse('admin:visitors_office_changelist')).status_code, 302)
        self.assertEqual(self.client.get(reverse('admin:auth_user_changelist')).status_code, 302)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))
        self.client.force_login(self.admin)
        self.assertNotContains(self.client.get(reverse('dashboard')), 'School Offices')
        self.assertNotContains(self.client.get(reverse('dashboard')), 'aria-label="Administration"')
        self.assertEqual(self.client.get(reverse('admin:visitors_office_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:auth_user_changelist')).status_code, 200)

    def test_post_actions_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.staff)
        for route in ('register_visitor', 'active_visitors', 'logout'):
            self.assertEqual(client.post(reverse(route), self.data).status_code, 403)

    def test_unknown_timeout_and_protected_history(self):
        self.register()
        self.assertEqual(self.client.post(reverse('active_visitors'), {'visit_id': 99999}).status_code, 404)
        self.assertRedirects(self.client.post(reverse('active_visitors'), {'visit_id': 'bad'}), reverse('active_visitors'))
        with self.assertRaises(ProtectedError):
            self.office.delete()
        with self.assertRaises(ProtectedError):
            Visitor.objects.get().delete()

    def test_pagination_preserves_filters(self):
        self.register()
        visit = Visit.objects.get()
        Visit.objects.bulk_create([Visit(visitor=visit.visitor, office=self.office, purpose='Records', recorded_by=self.staff) for _ in range(25)])
        response = self.client.get(reverse('visitor_history'), {'q': 'Maria', 'status': 'Inside'})
        self.assertEqual(len(response.context['visits']), 25)
        self.assertContains(response, 'page=2')
        response = self.client.get(reverse('visitor_history'), {'q': 'Maria', 'status': 'Inside', 'page': 2})
        self.assertEqual(len(response.context['visits']), 1)

    def test_records_remain_readable_after_recording_account_is_removed(self):
        self.register()
        self.client.force_login(self.admin)
        self.staff.delete()
        for route in ('active_visitors', 'visitor_history'):
            self.assertContains(self.client.get(reverse(route)), 'Unavailable')

    def test_registration_explains_missing_destinations(self):
        self.office.delete()
        self.assertContains(self.client.get(reverse('register_visitor')), 'add a school office')
        response = self.register()
        self.assertIn('office', response.context['form'].errors)
        self.assertFalse(Visitor.objects.exists())

    def test_login_success_failure_and_inactive_account(self):
        self.client.logout()
        self.assertContains(self.client.post(reverse('login'), {'username': 'security', 'password': 'wrong'}), 'Invalid username')
        self.assertRedirects(self.client.post(reverse('login'), {'username': 'security', 'password': 'test-password'}), reverse('dashboard'))
        self.client.logout()
        self.staff.is_active = False
        self.staff.save()
        self.assertContains(self.client.post(reverse('login'), {'username': 'security', 'password': 'test-password'}), 'Invalid username')

    def test_other_visitor_type_requires_details_and_preserves_invalid_input(self):
        for detail in ('', '   ', 'R' * 101):
            response = self.register(visitor_type='Other', visitor_type_other=detail)
            self.assertIn('visitor_type_other', response.context['form'].errors)
            self.assertEqual(response.context['form']['visitor_type'].value(), 'Other')
            self.assertFalse(Visitor.objects.exists())
            self.assertFalse(Visit.objects.exists())
        response = self.register(visitor_type='Other', visitor_type_other='Researcher', office='bad')
        self.assertEqual(response.context['form']['visitor_type_other'].value(), 'Researcher')
        self.assertFalse(Visitor.objects.exists())

    def test_other_visitor_type_is_saved_displayed_reused_and_cleared(self):
        self.assertRedirects(self.register(visitor_type='Other', visitor_type_other='  Researcher  '), reverse('active_visitors'))
        visitor = Visitor.objects.get()
        self.assertEqual(visitor.visitor_type_other, 'Researcher')
        self.assertEqual(visitor.visitor_type_display, 'Other: Researcher')
        for route in ('dashboard', 'active_visitors', 'visitor_history'):
            self.assertContains(self.client.get(reverse(route)), 'Other: Researcher')
        self.assertContains(self.client.get(reverse('register_visitor'), {'q': 'Maria'}), 'Other: Researcher')
        response = self.client.get(reverse('register_visitor'), {'visitor': visitor.pk})
        self.assertEqual(response.context['form'].initial['visitor_type_other'], 'Researcher')
        self.assertEqual(self.client.get(reverse('visitor_history'), {'visitor_type': 'Other'}).context['page_obj'].paginator.count, 1)
        self.client.post(reverse('active_visitors'), {'visit_id': Visit.objects.get().pk})
        self.assertRedirects(self.register(visitor=visitor.pk, visitor_type='Guest', visitor_type_other='Researcher'), reverse('active_visitors'))
        visitor.refresh_from_db()
        self.assertEqual(visitor.visitor_type, 'Guest')
        self.assertEqual(visitor.visitor_type_other, '')
        self.assertEqual(Visitor.objects.count(), 1)

    def test_admin_other_visitor_type_validation(self):
        from django.forms import modelform_factory
        form_class = modelform_factory(Visitor, fields='__all__')
        data = {key: self.data[key] for key in ('first_name', 'last_name', 'contact_number', 'address')}
        form = form_class(data | {'visitor_type': 'Other'})
        self.assertFalse(form.is_valid())
        self.assertIn('visitor_type_other', form.errors)
        form = form_class(data | {'visitor_type': 'Other', 'visitor_type_other': 'Researcher'})
        self.assertTrue(form.is_valid(), form.errors)
        visitor = form.save()
        self.assertEqual(visitor.visitor_type_display, 'Other: Researcher')
