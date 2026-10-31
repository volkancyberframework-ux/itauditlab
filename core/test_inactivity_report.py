from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import patch, Mock
import requests
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from .account_inactivity import run_due_check
from .inactivity_report import report_parts, send_report, send_pending_reports
from .models import AccountInactivityRun

@override_settings(GRCUSTASI_TELEGRAM_BOT_TOKEN='test-bot', GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID='test-admin',TELEGRAM_BOT_TOKEN='',TELEGRAM_CHAT_ID='')
class InactivityReportTests(TestCase):
    def setUp(self):
        self.now=datetime(2026,11,1,6,tzinfo=dt_timezone.utc)
        self.user=get_user_model().objects.create_user('inactive-report',email='student@example.test')
        get_user_model().objects.filter(pk=self.user.pk).update(date_joined=self.now-timedelta(days=60),
            last_login=self.now-timedelta(days=25),last_account_access_at=self.now-timedelta(days=25))

    def response(self):
        response=Mock();response.json.return_value={'ok':True};return response

    def test_snapshot_email_and_last_access_survive_reactivation_and_deletion(self):
        run=run_due_check(now=self.now)
        get_user_model().objects.filter(pk=self.user.pk).update(email='changed@example.test',is_active=True,last_account_access_at=self.now)
        self.user.delete()
        text='\n'.join(report_parts(run))
        self.assertIn('student@example.test',text);self.assertNotIn('changed@example.test',text)
        self.assertIn('07.10.2026 09:00 (Türkiye)',text)
        self.assertIn('Pasife alınan hesap: 1',text)
        self.assertNotIn('guler.volkan@yahoo.com',text)

    @patch('core.inactivity_report.requests.post')
    def test_success_once_and_missing_settings_are_retryable(self,post):
        post.return_value=self.response();run=run_due_check(now=self.now)
        with override_settings(GRCUSTASI_TELEGRAM_BOT_TOKEN=''):
            self.assertFalse(send_report(run.pk));post.assert_not_called()
        self.assertTrue(send_report(run.pk));self.assertTrue(send_report(run.pk))
        self.assertEqual(post.call_count,1)
        run.refresh_from_db();self.assertIsNotNone(run.telegram_sent_at);self.assertEqual(run.telegram_error,'')
        self.assertEqual(post.call_args.kwargs['data']['chat_id'],'test-admin')
        self.assertTrue(send_pending_reports());self.assertEqual(post.call_count,1)

    @patch('core.inactivity_report.requests.post')
    def test_failure_does_not_undo_account_deactivation_and_retries(self,post):
        post.side_effect=requests.Timeout('temporary')
        with patch('django.utils.timezone.now',return_value=self.now):
            with self.assertRaises(CommandError):call_command('check_account_inactivity')
        self.user.refresh_from_db();self.assertFalse(self.user.is_active)
        run=AccountInactivityRun.objects.get(reporting_date=self.now.date())
        self.assertIsNone(run.telegram_sent_at);self.assertEqual(run.telegram_error,'Timeout')
        first_completed=run.completed_at
        post.side_effect=None;post.return_value=self.response()
        with patch('django.utils.timezone.now',return_value=self.now+timedelta(minutes=1)):
            call_command('check_account_inactivity')
        run.refresh_from_db();self.assertEqual(run.completed_at,first_completed);self.assertIsNotNone(run.telegram_sent_at)
        self.assertEqual(run.disabled_user_ids,[self.user.pk])

    @patch('core.inactivity_report.requests.post')
    def test_long_report_resumes_after_last_acknowledged_page(self,post):
        rows=[dict(user_id=i,email=f'student-{i:04}@example.test',last_access_at=(self.now-timedelta(days=25)).isoformat()) for i in range(120)]
        run=AccountInactivityRun.objects.create(reporting_date=self.now.date(),completed_at=self.now,
            disabled_user_ids=list(range(120)),disabled_accounts=rows)
        parts=report_parts(run);self.assertGreater(len(parts),1);self.assertTrue(all(len(p)<3800 for p in parts))
        for row in rows:self.assertEqual(sum(row['email'] in part for part in parts),1)
        post.side_effect=[self.response(),requests.Timeout('page 2')]
        self.assertFalse(send_report(run.pk));run.refresh_from_db();self.assertEqual(run.telegram_parts_sent,1)
        post.side_effect=None;post.return_value=self.response()
        self.assertTrue(send_report(run.pk));self.assertEqual(post.call_count,len(parts)+1)
        self.assertEqual(post.call_args_list[2].kwargs['data']['text'],parts[1])

    @patch('core.inactivity_report.requests.post')
    def test_zero_accounts_still_produces_daily_summary(self,post):
        get_user_model().objects.filter(pk=self.user.pk).update(last_account_access_at=self.now)
        post.return_value=self.response();run=run_due_check(now=self.now)
        self.assertIn('pasife alınan hesap yok',report_parts(run)[0])
        self.assertTrue(send_report(run.pk));self.assertEqual(post.call_count,1)

    def test_never_logged_in_does_not_claim_creation_date_is_access(self):
        get_user_model().objects.filter(pk=self.user.pk).update(last_login=None,last_account_access_at=None)
        run=run_due_check(now=self.now);text=report_parts(run)[0]
        self.assertIn('Son erişim: giriş kaydı yok',text);self.assertIn('Hesap açılışı:',text)

    @patch('core.inactivity_report.requests.post')
    def test_api_rejection_not_marked_sent_and_before_0900_no_notification(self,post):
        with patch('django.utils.timezone.now',return_value=self.now-timedelta(seconds=1)):
            call_command('check_account_inactivity')
        post.assert_not_called()
        run=run_due_check(now=self.now)
        response=self.response();response.json.return_value={'ok':False};post.return_value=response
        self.assertFalse(send_report(run.pk));run.refresh_from_db();self.assertIsNone(run.telegram_sent_at)
        self.assertEqual(run.telegram_parts_sent,0)
