from datetime import date, timedelta
from importlib import import_module
from types import SimpleNamespace
from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from .models import ContactChangeNotice, Course, LearningProgram, LearningProgramStep, ProgramEnrollment, ProgramRelease


@override_settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_ID='')
class ContactNoticeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('notice', is_first_login=False)
        self.url = reverse('contact_change_notice')
        self.dashboard = reverse('dashboard_student')
        self.client.force_login(self.user)

    def test_gate_acknowledgement_is_required_and_persists_across_sessions(self):
        notice = ContactChangeNotice.objects.create(user=self.user)
        for method in (self.client.get, self.client.post):
            self.assertRedirects(method(self.dashboard), self.url, fetch_redirect_response=False)
        self.assertContains(self.client.get(self.url), '0032 476 073 171')
        self.assertEqual(self.client.post(self.url).status_code, 400)
        notice.refresh_from_db(); self.assertIsNone(notice.acknowledged_at)
        self.assertRedirects(self.client.post(self.url, {'understood':'yes'}), self.dashboard, fetch_redirect_response=False)
        notice.refresh_from_db(); self.assertIsNotNone(notice.acknowledged_at)
        first = notice.acknowledged_at
        self.client.logout(); self.client.force_login(self.user)
        self.assertRedirects(self.client.get(self.url), self.dashboard, fetch_redirect_response=False)
        self.client.post(self.url, {'understood':'yes'})
        notice.refresh_from_db(); self.assertEqual(first, notice.acknowledged_at)

    def test_csrf_and_authentication(self):
        ContactChangeNotice.objects.create(user=self.user)
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.user)
        self.assertEqual(csrf.post(self.url, {'understood':'yes'}).status_code, 403)
        self.client.logout(); self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertIsNone(ContactChangeNotice.objects.get(user=self.user).acknowledged_at)

    def test_no_recipient_is_not_gated_and_logout_remains_available(self):
        self.assertRedirects(self.client.get(self.url), self.dashboard, fetch_redirect_response=False)
        ContactChangeNotice.objects.create(user=self.user)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_snapshot_excludes_finished_paused_future_and_nonstudents(self):
        program = LearningProgram.objects.create(slug='notice',name='Notice')
        course = Course.objects.create(duration=timedelta(hours=1))
        step = LearningProgramStep.objects.create(program=program,course=course,day_offset=0)
        active = ProgramEnrollment.objects.create(user=self.user,program=program,start_date=date(2026,10,1))
        users = {}
        for name in ('finished','paused','future','staff','disabled','both'):
            u = get_user_model().objects.create_user(name,is_staff=name=='staff',is_active=name!='disabled')
            users[name] = u
            e = ProgramEnrollment.objects.create(user=u,program=program,start_date=date(2026,11,1) if name=='future' else date(2026,10,1),is_active=name!='paused')
            if name in ('finished','both'):
                ProgramRelease.objects.create(enrollment=e,step=step,status='sent')
        other = LearningProgram.objects.create(slug='other',name='Other')
        LearningProgramStep.objects.create(program=other,course=course,day_offset=0)
        ProgramEnrollment.objects.create(user=users['both'],program=other,start_date=date(2026,10,1))
        seed = import_module('core.migrations.0034_contact_change_notice').seed_current_students
        editor = SimpleNamespace(connection=SimpleNamespace(alias='default'))
        seed(apps, editor)
        self.assertSetEqual(set(ContactChangeNotice.objects.values_list('user_id',flat=True)), {self.user.pk,users['both'].pk})
        ContactChangeNotice.objects.filter(user=self.user).update(acknowledged_at=timezone.now())
        seed(apps, editor)
        self.assertIsNotNone(ContactChangeNotice.objects.get(user=self.user).acknowledged_at)
