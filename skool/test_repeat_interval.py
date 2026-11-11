from datetime import datetime, time, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo
from django.test import TestCase
from django.utils import timezone
from skool.tests import BookingTests
from skool.models import MeetingBooking, MeetingSlot
from skool.services import reschedule_booking

class RepeatRescheduleTests(TestCase):
    def setUp(self):
        BookingTests.setUp(self)

    @patch('skool.services.validate_bookable_slot')
    def test_reschedule_cannot_bypass_fourteen_days(self, validate):
        today=timezone.localdate(timezone=ZoneInfo('Europe/Istanbul'))
        def slot(day):
            start=datetime.combine(day,time(12),tzinfo=ZoneInfo('Europe/Istanbul'))
            return MeetingSlot.objects.create(availability=self.availability,local_date=day,start_at_utc=start,end_at_utc=start+timedelta(minutes=90))
        MeetingBooking.objects.create(user=self.user,slot=slot(today-timedelta(days=1)),status='completed',meeting_url='https://example.com')
        booked=MeetingBooking.objects.create(user=self.user,slot=slot(today+timedelta(days=14)),status='active',meeting_url='https://example.com')
        early=slot(today+timedelta(days=12))
        with self.assertRaisesMessage(ValueError,'en erken 14 gün'):
            reschedule_booking(self.user,early.pk)
        booked.refresh_from_db()
        self.assertNotEqual(booked.slot_id,early.pk)
        allowed=slot(today+timedelta(days=13))
        updated,_=reschedule_booking(self.user,allowed.pk)
        self.assertEqual(updated.slot_id,allowed.pk)
