import json
from datetime import datetime, time, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from core.tests import StudentCourseInterfaceTests
from core.models import StudentMeetingBooking, MentorshipRequest
from skool.models import TravelAvailability, MeetingSlot
from skool.services import earliest_repeat_booking_date


class StudentMeetingIntervalTests(TestCase):
    def setUp(self):
        StudentCourseInterfaceTests.setUp(self)
        self.zone = ZoneInfo('Europe/Istanbul')
        self.today = timezone.localdate(timezone=self.zone)
        self.availability = TravelAvailability.objects.create(
            location_name='Test', timezone='Europe/Istanbul',
            start_date=self.today-timedelta(days=60), end_date=self.today+timedelta(days=60),
            local_available_start=time(9), local_available_end=time(18))
        self.item = self.request()

    def request(self):
        return MentorshipRequest.objects.create(user=self.user,course=self.course,request_type='meeting',reason='Test görüşmesi')

    def slot(self, day):
        start = datetime.combine(day,time(12),tzinfo=self.zone)
        return MeetingSlot.objects.create(availability=self.availability,local_date=day,start_at_utc=start,end_at_utc=start+timedelta(minutes=90))

    def previous(self, days_ago=1, status='completed'):
        return StudentMeetingBooking.objects.create(user=self.user,request=self.request(),slot=self.slot(self.today-timedelta(days=days_ago)),status=status,meeting_url='https://example.com')

    def test_latest_meeting_controls_all_course_requests_and_cancelled_is_ignored(self):
        self.previous(days_ago=8)
        self.previous(days_ago=2)
        self.previous(days_ago=1,status='cancelled')
        self.assertEqual(earliest_repeat_booking_date(self.user,booking_model=StudentMeetingBooking),self.today+timedelta(days=12))

    def test_expired_active_booking_counts_without_opening_calendar(self):
        self.previous(status='active')
        self.assertEqual(earliest_repeat_booking_date(self.user,booking_model=StudentMeetingBooking),self.today+timedelta(days=13))

    @patch('skool.services.send_telegram')
    @patch('skool.services.validate_bookable_slot')
    def test_direct_booking_rejects_day_13_and_accepts_day_14(self, validate, notify):
        self.previous()
        early=self.slot(self.today+timedelta(days=12))
        allowed=self.slot(self.today+timedelta(days=13))
        url=reverse('student_meeting_book',args=[self.item.pk])
        response=self.client.post(url,json.dumps({'slot_id':early.pk}),content_type='application/json')
        self.assertEqual(response.status_code,409)
        self.assertIn('14 gün',response.json()['error'])
        self.assertFalse(StudentMeetingBooking.objects.filter(request=self.item).exists())
        response=self.client.post(url,json.dumps({'slot_id':allowed.pk}),content_type='application/json')
        self.assertEqual(response.status_code,200)

    @patch('skool.services.ensure_upcoming_slots')
    @patch('skool.services.published_slots',return_value=[])
    def test_slots_api_applies_interval_and_calendar_explains_it(self,published,ensure):
        self.previous()
        response=self.client.get(reverse('student_meeting_slots',args=[self.item.pk]))
        self.assertEqual(response.status_code,200)
        published.assert_called_once_with(first_date=self.today+timedelta(days=13))
        self.assertContains(self.client.get(reverse('student_meeting_calendar',args=[self.item.pk])),'en az 14 gün')

    def test_first_booking_and_old_history_start_tomorrow(self):
        self.assertEqual(earliest_repeat_booking_date(self.user,booking_model=StudentMeetingBooking),self.today+timedelta(days=1))
        self.previous(days_ago=30)
        self.assertEqual(earliest_repeat_booking_date(self.user,booking_model=StudentMeetingBooking),self.today+timedelta(days=1))
