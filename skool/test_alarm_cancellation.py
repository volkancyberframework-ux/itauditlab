from datetime import datetime, date
from types import SimpleNamespace
from zoneinfo import ZoneInfo
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import Resolver404, resolve
from .digest import send_daily_meeting_digest


class AlarmCancellationTests(SimpleTestCase):
    @patch('skool.digest.send_telegram',return_value=True)
    @patch('skool.digest.MentorshipRequest.objects.filter')
    @patch('skool.digest.StudentMeetingBooking.objects.filter')
    @patch('skool.digest.MeetingBooking.objects.filter')
    def test_meeting_digest_is_only_original_text(self, skool, student, requests, send):
        zone=ZoneInfo('Europe/Istanbul')
        booking=SimpleNamespace(user=SimpleNamespace(full_name='Test Öğrenci'),slot=SimpleNamespace(start_at_utc=datetime(2026,10,31,19,30,tzinfo=zone),end_at_utc=datetime(2026,10,31,21,tzinfo=zone)))
        skool.return_value.select_related.return_value.order_by.return_value=[booking]
        student.return_value.select_related.return_value.order_by.return_value=[]
        requests.return_value.select_related.return_value=[]
        self.assertTrue(send_daily_meeting_digest(date(2026,10,31)))
        send.assert_called_once_with('☀️ Günaydın Volkan\n\nBugün 1 birebir görüşmen var.\n\n1. Test Öğrenci • Skool\n19:30 – 21:00\nTest: ✅ • Podcast: ✅',idempotency_key='meeting-digest:2026-10-31')

    def test_all_alarm_urls_removed(self):
        for path in ['/admin/skool/gorusme-alarmlari/','/admin/skool/gorusme-alarmlari/otomatik/','/gorusme-alarmlari/kurulum/','/gorusme-alarmlari/test/veri/','/gorusme-alarmlari/otomatik/'+'x'*43+'/veri/']:
            with self.subTest(path=path), self.assertRaises(Resolver404):
                resolve(path)
