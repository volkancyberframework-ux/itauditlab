from datetime import date, datetime, timezone as dt_timezone
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import CustomUser, WeeklyTelegramSchedule
from core.weekly_notifications import WEEKDAYS, send_weekly_telegram_note


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class WeeklyTelegramTests(TestCase):
    @patch('core.weekly_notifications.send_telegram', return_value=True)
    def test_each_day_and_weekly_recurrence(self, send):
        WeeklyTelegramSchedule.objects.create(**{field: f'Not {field}' for field in WEEKDAYS})
        for offset in range(14):
            day = date(2026, 10, 26).fromordinal(date(2026, 10, 26).toordinal() + offset)
            self.assertTrue(send_weekly_telegram_note(day))
            self.assertIn(f'Not {WEEKDAYS[offset % 7]}', send.call_args.args[0])
            self.assertEqual(send.call_args.kwargs['idempotency_key'], f'weekly-note:{day.isoformat()}')

    @patch('core.weekly_notifications.send_telegram')
    def test_missing_and_blank_notes_are_skipped(self, send):
        self.assertFalse(send_weekly_telegram_note(date(2026, 10, 26)))
        WeeklyTelegramSchedule.objects.create(monday='  \n ')
        self.assertFalse(send_weekly_telegram_note(date(2026, 10, 26)))
        send.assert_not_called()

    @patch('core.weekly_notifications.timezone.now', return_value=datetime(2026, 10, 25, 22, tzinfo=dt_timezone.utc))
    @patch('core.weekly_notifications.send_telegram', return_value=True)
    def test_istanbul_day_boundary(self, send, now):
        WeeklyTelegramSchedule.objects.create(monday='Pazartesi notu', sunday='Pazar notu')
        send_weekly_telegram_note()
        self.assertIn('Pazartesi notu', send.call_args.args[0])

    def test_length_limit(self):
        with self.assertRaises(ValidationError):
            WeeklyTelegramSchedule(monday='a' * 3501).full_clean()

    def test_admin_single_page_save(self):
        user = CustomUser.objects.create_superuser(username='weeklyadmin', email='weekly@example.com', password='test-pass')
        self.client.force_login(user)
        response = self.client.get(reverse('admin:core_weeklytelegramschedule_changelist'))
        self.assertRedirects(response, reverse('admin:core_weeklytelegramschedule_add'))
        data = {field: f'{field} notu' for field in WEEKDAYS}
        response = self.client.post(reverse('admin:core_weeklytelegramschedule_add'), data)
        self.assertEqual(response.status_code, 302)
        obj = WeeklyTelegramSchedule.objects.get(pk=1)
        self.assertEqual(obj.sunday, 'sunday notu')
        response = self.client.get(reverse('admin:core_weeklytelegramschedule_changelist'))
        self.assertRedirects(response, reverse('admin:core_weeklytelegramschedule_change', args=[1]))
        for label in ('Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar'):
            self.assertContains(self.client.get(response.url), label)

    @patch('skool.services.requests.post')
    @override_settings(GRCUSTASI_TELEGRAM_BOT_TOKEN='local-test-token', GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID='local-test-chat')
    def test_same_day_sent_once_and_next_week_sent_again(self, post):
        WeeklyTelegramSchedule.objects.create(monday='Haftalık hatırlatma')
        self.assertTrue(send_weekly_telegram_note(date(2026, 10, 26)))
        self.assertFalse(send_weekly_telegram_note(date(2026, 10, 26)))
        self.assertTrue(send_weekly_telegram_note(date(2026, 11, 2)))
        self.assertEqual(post.call_count, 2)

    @patch('skool.services.requests.post')
    @override_settings(GRCUSTASI_TELEGRAM_BOT_TOKEN='local-test-token', GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID='local-test-chat')
    def test_failed_delivery_can_be_retried(self, post):
        import requests
        WeeklyTelegramSchedule.objects.create(monday='Haftalık hatırlatma')
        post.side_effect = requests.RequestException('network unavailable')
        with self.assertRaises(requests.RequestException):
            send_weekly_telegram_note(date(2026, 10, 26))
        post.side_effect = None
        self.assertTrue(send_weekly_telegram_note(date(2026, 10, 26)))
