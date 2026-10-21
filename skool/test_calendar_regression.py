from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo
from django.test import TestCase
from .models import TravelAvailability, MeetingSlot, SkoolSettings, AvailabilityException
from .services import ensure_upcoming_slots, published_slots, validate_bookable_slot


class CalendarRegressionTests(TestCase):
    def setUp(self):
        self.clock = patch('django.utils.timezone.now', return_value=datetime(2026, 10, 21, 8, tzinfo=dt_timezone.utc))
        self.clock.start()
        self.addCleanup(self.clock.stop)
        SkoolSettings.objects.create(pk=1, daily_slot_count=3, display_timezone='Europe/Istanbul', meeting_duration_minutes=90)
        self.vietnam = TravelAvailability.objects.create(location_name='Vietnam', timezone='Asia/Ho_Chi_Minh', start_date=date(2026,9,1), end_date=date(2026,10,13), local_available_start=time(9), local_available_end=time(16))
        self.ankara = TravelAvailability.objects.create(location_name='Türkiye Ankara', timezone='Europe/Istanbul', start_date=date(2026,10,18), end_date=date(2026,11,4), local_available_start=time(11), local_available_end=time(22))
        # Production regression: cached Vietnamese rows survived a date-range edit.
        self.stale = []
        for hour in (3, 5, 7):
            start=datetime(2026,10,22,hour,tzinfo=dt_timezone.utc)
            self.stale.append(MeetingSlot.objects.create(availability=self.vietnam, local_date=date(2026,10,22), start_at_utc=start, end_at_utc=start+timedelta(minutes=90)))

    def test_requested_dates_and_rolling_horizon(self):
        ensure_upcoming_slots()
        slots = published_slots()
        for day in (date(2026,10,21), date(2026,11,8), date(2026,11,9), date(2026,11,15), date(2026,12,1)):
            with self.subTest(day=day):
                daily=[s for s in slots if s.start_at_utc.astimezone(ZoneInfo('Europe/Istanbul')).date()==day]
                self.assertEqual(len(daily), 0 if day==date(2026,10,21) else 3)
                for slot in daily:
                    start=slot.start_at_utc.astimezone(ZoneInfo('Europe/Istanbul'))
                    end=slot.end_at_utc.astimezone(ZoneInfo('Europe/Istanbul'))
                    self.assertEqual(start.utcoffset(), timedelta(hours=3))
                    self.assertGreaterEqual(start.time(), time(11))
                    self.assertLessEqual(end.time(), time(22))
                    self.assertEqual(end-start, timedelta(minutes=90))
        oct22=[s for s in slots if s.local_date==date(2026,10,22)]
        self.assertEqual(len(oct22), 3)
        self.assertTrue(all(s.availability_id==self.ankara.pk for s in oct22))
        self.assertEqual(MeetingSlot.objects.filter(pk__in=[s.pk for s in self.stale]).count(),3)
        for stale in self.stale:
            with self.assertRaises(ValueError): validate_bookable_slot(stale)
        ids=[s.pk for s in slots]
        ensure_upcoming_slots()
        self.assertEqual(ids,[s.pk for s in published_slots()])

    def test_exceptions_and_disabled_slots_survive(self):
        day=date(2026,11,9)
        AvailabilityException.objects.create(start_date=day,end_date=day,reason='İzin')
        ensure_upcoming_slots()
        self.assertFalse(any(s.local_date==day for s in published_slots()))
        slot=next(s for s in published_slots() if s.local_date==date(2026,10,22))
        slot.status='disabled'; slot.save()
        ensure_upcoming_slots()
        slot.refresh_from_db()
        self.assertEqual(slot.status,'disabled')
        with self.assertRaises(ValueError): validate_bookable_slot(slot)

    def test_display_locale_does_not_change_instants(self):
        from django.utils import timezone, translation
        ensure_upcoming_slots(days=2)
        expected=[(s.pk,s.start_at_utc) for s in published_slots()]
        for language in ('tr','en','fr','es','ja','zh-hans','vi','ar'):
            with translation.override(language), timezone.override('America/New_York'):
                self.assertEqual(expected,[(s.pk,s.start_at_utc) for s in published_slots()])
