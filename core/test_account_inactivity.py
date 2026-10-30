from datetime import datetime, timedelta, timezone as dt_timezone
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch
from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from .account_inactivity import run_due_check, touch_access, INACTIVITY_MESSAGE
from .models import AccountInactivityRun, PageVisit
from mobile_api.models import AnalyticsEvent, UserPathProgress, LearningPath

@override_settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_ID='', STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class InactivityTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.addCleanup(cache.clear)
        self.now = datetime(2026,11,1,6,0,tzinfo=dt_timezone.utc)  # 09:00 Istanbul
        self.password='Inactive-test-896!'
        self.user=get_user_model().objects.create_user('inactive',email='inactive@example.test',password=self.password,
            is_first_login=False,is_mobile=True,mobile_email_verified=True,mobile_full_access=True)
        get_user_model().objects.filter(pk=self.user.pk).update(date_joined=self.now-timedelta(days=60),
            last_login=self.now-timedelta(days=25),last_account_access_at=self.now-timedelta(days=25))
        self.user.refresh_from_db()

    def test_0900_schedule_strict_20_day_boundary_and_idempotence(self):
        self.assertIsNone(run_due_check(now=self.now-timedelta(seconds=1)))
        self.assertFalse(AccountInactivityRun.objects.exists())
        get_user_model().objects.filter(pk=self.user.pk).update(last_account_access_at=self.now-timedelta(days=20))
        run=run_due_check(now=self.now)
        self.user.refresh_from_db();self.assertTrue(self.user.is_active)
        self.assertEqual(run.disabled_user_ids,[])
        again=run_due_check(now=self.now+timedelta(hours=3));self.assertEqual(again.pk,run.pk)
        next_run=run_due_check(now=self.now+timedelta(days=1))
        self.assertEqual(next_run.disabled_user_ids,[self.user.pk])
        self.user.refresh_from_db();self.assertFalse(self.user.is_active)

    def test_both_owner_emails_are_exempt_including_staff_paid_otherwise_not_exempt(self):
        for i,email in enumerate(('GULER.VOLKAN@YAHOO.COM','volkancyberframework@gmail.com')):
            owner=get_user_model().objects.create_user('owner'+str(i),email=email)
            get_user_model().objects.filter(pk=owner.pk).update(date_joined=self.now-timedelta(days=100))
        get_user_model().objects.filter(pk=self.user.pk).update(is_staff=True,is_superuser=True)
        run=run_due_check(now=self.now)
        self.assertEqual(run.disabled_user_ids,[self.user.pk])
        self.assertEqual(get_user_model().objects.filter(username__startswith='owner',is_active=True).count(),2)

    def test_recent_real_access_keeps_account_and_failed_attempt_does_not(self):
        touch_access(self.user,now=self.now-timedelta(days=1),force=True)
        self.assertEqual(run_due_check(now=self.now).disabled_user_ids,[])
        self.assertEqual(self.client.post(reverse('login'),{'email':self.user.email,'password':'wrong'}).status_code,200)
        self.user.refresh_from_db();self.assertEqual(self.user.last_account_access_at,self.now-timedelta(days=1))

    def test_expired_session_and_tokens_cannot_bypass_disablement(self):
        self.client.force_login(self.user)
        get_user_model().objects.filter(pk=self.user.pk).update(last_login=self.now-timedelta(days=25))
        refresh=RefreshToken.for_user(self.user)
        run_due_check(now=self.now)
        self.assertTrue(BlacklistedToken.objects.filter(token__jti=refresh['jti']).exists())
        response=self.client.get(reverse('dashboard_student'))
        self.assertEqual(response.status_code,302);self.assertIn('/login/',response.url)
        api=APIClient();api.credentials(HTTP_AUTHORIZATION='Bearer '+str(refresh.access_token))
        self.assertEqual(api.get('/api/mobile/v1/profile/').status_code,401)
        self.assertNotEqual(api.post('/api/mobile/v1/auth/refresh/',{'refresh':str(refresh)},format='json').status_code,200)

    def test_notice_only_for_correct_password_and_inactivity_reason(self):
        run_due_check(now=self.now)
        self.assertContains(self.client.post(reverse('login'),{'email':self.user.email,'password':self.password}),INACTIVITY_MESSAGE)
        self.assertNotContains(self.client.post(reverse('login'),{'email':self.user.email,'password':'wrong'}),INACTIVITY_MESSAGE)
        api=APIClient()
        response=api.post('/api/mobile/v1/auth/login/',{'email':self.user.email,'password':self.password},format='json')
        self.assertEqual(response.status_code,403);self.assertEqual(response.data['detail'],INACTIVITY_MESSAGE)
        self.assertNotIn('access',response.data)
        get_user_model().objects.filter(pk=self.user.pk).update(inactivity_disabled_at=None)
        self.assertNotContains(self.client.post(reverse('login'),{'email':self.user.email,'password':self.password}),INACTIVITY_MESSAGE)

    def test_successful_web_and_mobile_login_record_access(self):
        response=self.client.post(reverse('login'),{'email':self.user.email,'password':self.password})
        self.assertEqual(response.status_code,302)
        self.user.refresh_from_db();self.assertGreater(self.user.last_account_access_at,self.now-timedelta(days=2))
        old=self.user.last_account_access_at
        response=APIClient().post('/api/mobile/v1/auth/login/',{'email':self.user.email,'password':self.password},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.user.refresh_from_db();self.assertGreaterEqual(self.user.last_account_access_at,old)

    def test_reactivation_resets_clock_and_disabled_reason(self):
        run_due_check(now=self.now)
        self.user.refresh_from_db()
        self.user.is_active=True;self.user.save(update_fields=['is_active'])
        self.user.refresh_from_db();self.assertIsNone(self.user.inactivity_disabled_at)
        self.assertGreater(self.user.last_account_access_at,self.now-timedelta(days=2))
        self.assertNotIn(self.user.pk,run_due_check(now=self.now+timedelta(days=1)).disabled_user_ids)

    def test_background_refresh_does_not_extend_access_and_real_mobile_request_does(self):
        api=APIClient();api.force_authenticate(self.user)
        with patch('mobile_api.views.MobileThrottle.allow_request',return_value=True):
            response=api.get('/api/mobile/v1/profile/')
        self.assertEqual(response.status_code,200,response.data)
        self.user.refresh_from_db();recent=self.user.last_account_access_at
        token=RefreshToken.for_user(self.user)
        APIClient().post('/api/mobile/v1/auth/refresh/',{'refresh':str(token)},format='json')
        self.user.refresh_from_db();self.assertEqual(self.user.last_account_access_at,recent)

    def test_backfill_uses_real_events_not_automatic_assignments(self):
        old=self.now-timedelta(days=25)
        event=AnalyticsEvent.objects.create(user=self.user,name='app_opened')
        AnalyticsEvent.objects.filter(pk=event.pk).update(created_at=old)
        path=LearningPath.objects.create(title='Automatic')
        UserPathProgress.objects.create(user=self.user,path=path)
        migration=import_module('core.migrations.0035_account_inactivity_policy')
        migration.backfill_access(apps,SimpleNamespace(connection=__import__('django.db',fromlist=['connection']).connection))
        self.user.refresh_from_db();self.assertEqual(self.user.last_account_access_at,old)

    def test_failure_rolls_back_and_can_retry(self):
        with patch('rest_framework_simplejwt.token_blacklist.models.OutstandingToken.objects.filter',side_effect=RuntimeError('unavailable')):
            with self.assertRaises(RuntimeError):run_due_check(now=self.now)
        self.user.refresh_from_db();self.assertTrue(self.user.is_active)
        self.assertFalse(AccountInactivityRun.objects.exists())
        self.assertEqual(run_due_check(now=self.now).disabled_user_ids,[self.user.pk])

    def test_scheduler_waits_until_turkey_0900_and_retries_failed_command(self):
        from itaudit.inactivity_scheduler import tick
        with patch('itaudit.inactivity_scheduler.subprocess.run') as command:
            self.assertIsNone(tick(None,now=self.now-timedelta(seconds=1)))
            command.assert_not_called()
            completed=tick(None,now=self.now)
            self.assertEqual(completed,self.now.astimezone(__import__('zoneinfo').ZoneInfo('Europe/Istanbul')).date())
            command.assert_called_once()
            self.assertEqual(tick(completed,now=self.now+timedelta(hours=1)),completed)
            command.assert_called_once()
            command.side_effect=__import__('subprocess').TimeoutExpired('check',120)
            with self.assertRaises(__import__('subprocess').TimeoutExpired):tick(None,now=self.now)

    def test_stale_last_login_update_does_not_clear_disabled_reason(self):
        stale=get_user_model().objects.get(pk=self.user.pk)
        run_due_check(now=self.now)
        stale.last_login=self.now;stale.save(update_fields=['last_login'])
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active);self.assertIsNotNone(self.user.inactivity_disabled_at)

    def test_never_used_accounts_start_at_creation_date(self):
        old=get_user_model().objects.create_user('never-old',email='old@example.test')
        fresh=get_user_model().objects.create_user('never-new',email='new@example.test')
        get_user_model().objects.filter(pk=old.pk).update(date_joined=self.now-timedelta(days=21))
        get_user_model().objects.filter(pk=fresh.pk).update(date_joined=self.now-timedelta(days=19))
        run=run_due_check(now=self.now)
        self.assertIn(old.pk,run.disabled_user_ids);self.assertNotIn(fresh.pk,run.disabled_user_ids)

    def test_web_access_updates_clock_but_heartbeat_does_not(self):
        self.client.force_login(self.user)
        self.client.get(reverse('dashboard_student'))
        self.user.refresh_from_db();recent=self.user.last_account_access_at
        self.assertGreater(recent,self.now-timedelta(days=2))
        old=self.now-timedelta(days=19)
        get_user_model().objects.filter(pk=self.user.pk).update(last_account_access_at=old)
        self.client.post(reverse('heartbeat'),{},content_type='application/json')
        self.user.refresh_from_db();self.assertEqual(self.user.last_account_access_at,old)
