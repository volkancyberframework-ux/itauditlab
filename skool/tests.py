import json
from datetime import date, time, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    AvailabilityException, CareerTestAnswer, MeetingBooking, MeetingSlot, NotificationLog,
    SkoolInvitation, SkoolSettings, SkoolUser, TravelAvailability,
)
from .questions import QUESTIONS
from .admin import AvailabilityExceptionForm, TravelAvailabilityForm
from .services import generate_slots, reserve_slot, reschedule_booking
from .views import bunny_embed_url, youtube_video_id


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class SkoolFlowTests(TestCase):
    def setUp(self):
        self.invitation, self.raw_token = SkoolInvitation.create_invitation("Volkan Güler")

    def claim(self, name="Volkan Güler"):
        self.client.get(reverse("skool:onboarding") + f"?invite={self.raw_token}")
        return self.client.post(reverse("skool:onboarding"), {"full_name": name})

    def test_unauthorized_person_cannot_enter(self):
        response = self.client.post(reverse("skool:onboarding"), {"full_name": "Başka Kişi"})
        self.assertContains(response, "aktif bir Skool", status_code=200)
        self.assertFalse(SkoolUser.objects.exists())

    def test_invitation_token_cannot_be_claimed_by_other_name(self):
        response = self.claim("Başka Kişi")
        self.assertEqual(response.status_code, 200)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, "invited")

    def test_turkish_name_matching_is_case_insensitive_and_trimmed(self):
        response = self.claim("  VOLKAN   GÜLER ")
        self.assertRedirects(response, reverse("skool:journey"))
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, "claimed")

    def test_claimed_invitation_link_resumes_existing_user(self):
        self.claim()
        other = Client()
        other.get(reverse("skool:onboarding") + f"?invite={self.raw_token}")
        response = other.post(reverse("skool:onboarding"), {"full_name": "Volkan Güler"})
        self.assertRedirects(response, reverse("skool:journey"))
        self.assertEqual(SkoolUser.objects.count(), 1)

    def test_session_resumes_progress(self):
        self.claim()
        user = SkoolUser.objects.get()
        user.current_question = 7
        user.save()
        response = self.client.get(reverse("skool:journey"))
        self.assertContains(response, "current:7")

    def test_cannot_skip_questions(self):
        self.claim()
        response = self.client.post(reverse("skool:save_answer"), json.dumps({"question_id": 2, "selected_option": "Evet"}), content_type="application/json")
        self.assertEqual(response.status_code, 409)

    @patch("skool.views.send_telegram")
    def test_all_answers_complete_test_and_notify_once(self, notify):
        self.claim()
        for number, text, help_text, options, section in QUESTIONS:
            response = self.client.post(reverse("skool:save_answer"), json.dumps({"question_id": number, "selected_option": options[0]}), content_type="application/json")
            self.assertEqual(response.status_code, 200)
        user = SkoolUser.objects.get()
        self.assertEqual(user.answers.count(), 24)
        self.assertEqual(user.state, "TEST_COMPLETED")
        self.assertEqual(user.foundation_result, "strong")
        notify.assert_called_once()

    def test_completed_test_answer_cannot_change(self):
        self.claim()
        user = SkoolUser.objects.get()
        user.test_completed_at = timezone.now()
        user.save()
        response = self.client.post(reverse("skool:save_answer"), json.dumps({"question_id": 1, "selected_option": "Evet"}), content_type="application/json")
        self.assertEqual(response.status_code, 409)

    def test_audio_requires_completed_test(self):
        self.claim()
        response = self.client.post(reverse("skool:audio_progress"), json.dumps({"position": 20, "duration": 100}), content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_audio_cannot_complete_under_eighty_percent(self):
        self.claim()
        user = SkoolUser.objects.get()
        user.test_completed_at = timezone.now()
        user.audio_duration_seconds = 100
        user.audio_listened_seconds = 79
        user.save()
        response = self.client.post(reverse("skool:complete_audio"))
        self.assertEqual(response.status_code, 409)

    def test_audio_completes_at_eighty_percent(self):
        self.claim()
        user = SkoolUser.objects.get()
        user.test_completed_at = timezone.now()
        user.audio_duration_seconds = 100
        user.audio_listened_seconds = 80
        user.save()
        response = self.client.post(reverse("skool:complete_audio"))
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.state, "READY_TO_BOOK")

    @patch("skool.views.send_telegram")
    def test_audio_can_be_skipped_with_warning_event(self, notify):
        self.claim()
        user = SkoolUser.objects.get()
        user.test_completed_at = timezone.now()
        user.save(update_fields=("test_completed_at",))
        response = self.client.post(reverse("skool:skip_audio"))
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.state, "READY_TO_BOOK")
        self.assertTrue(user.events.filter(event_type="audio_skipped").exists())
        notify.assert_called_once()

    def test_youtube_links_are_rendered_by_video_id(self):
        self.assertEqual(youtube_video_id("https://youtu.be/dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ")
        self.assertEqual(youtube_video_id("https://example.com/video.mp4"), "")

    def test_bunny_stream_iframe_link_is_accepted(self):
        url = "https://iframe.mediadelivery.net/play/478437/cb866163-57ae-4fad-9c95-4a727852b9b0"
        self.assertEqual(bunny_embed_url(url), url)
        self.assertEqual(bunny_embed_url("https://example.com/play/478437/video"), "")

    def test_bunny_stream_link_renders_as_iframe_not_html_video(self):
        self.claim()
        user = SkoolUser.objects.get()
        user.test_completed_at = timezone.now()
        user.state = "TEST_COMPLETED"
        user.save(update_fields=("test_completed_at", "state"))
        config = SkoolSettings.load()
        config.audio_url = ""
        config.video_url = "https://iframe.mediadelivery.net/play/478437/cb866163-57ae-4fad-9c95-4a727852b9b0"
        config.save(update_fields=("audio_url", "video_url"))

        response = self.client.get(reverse("skool:journey"))
        self.assertContains(response, 'id="bunny-player"')
        self.assertContains(response, config.video_url)
        self.assertNotContains(response, 'id="career-media"')

    def test_bunny_stream_link_in_audio_field_renders_as_iframe(self):
        self.claim()
        user = SkoolUser.objects.get()
        user.test_completed_at = timezone.now()
        user.state = "TEST_COMPLETED"
        user.save(update_fields=("test_completed_at", "state"))
        config = SkoolSettings.load()
        config.audio_url = "https://iframe.mediadelivery.net/play/478437/cb866163-57ae-4fad-9c95-4a727852b9b0"
        config.video_url = ""
        config.save(update_fields=("audio_url", "video_url"))

        response = self.client.get(reverse("skool:journey"))
        self.assertContains(response, 'id="bunny-player"')
        self.assertContains(response, config.audio_url)
        self.assertNotContains(response, 'id="career-media"')


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class BookingTests(TestCase):
    def setUp(self):
        invitation, _ = SkoolInvitation.create_invitation("Ada Test")
        invitation.status = "claimed"
        invitation.save()
        self.user = SkoolUser.objects.create(invitation=invitation, full_name="Ada Test", state="READY_TO_BOOK", test_completed_at=timezone.now(), audio_completed_at=timezone.now())
        self.availability = TravelAvailability.objects.create(
            location_name="Vietnam", timezone="Asia/Ho_Chi_Minh",
            start_date=timezone.localdate() + timedelta(days=1), end_date=timezone.localdate() + timedelta(days=10),
            local_available_start=time(12), local_available_end=time(20),
        )

    def test_three_slots_are_persisted_and_stable(self):
        target = timezone.localdate() + timedelta(days=2)
        first = generate_slots(self.availability, target)
        second = generate_slots(self.availability, target)
        self.assertEqual(len(first), 3)
        self.assertEqual([x.pk for x in first], [x.pk for x in second])

    def test_slots_do_not_overlap(self):
        slots = generate_slots(self.availability, timezone.localdate() + timedelta(days=2))
        self.assertTrue(all(a.end_at_utc <= b.start_at_utc for a, b in zip(slots, slots[1:])))

    def test_timezone_conversion_uses_iana_zone(self):
        slot = generate_slots(self.availability, timezone.localdate() + timedelta(days=2))[0]
        local = slot.start_at_utc.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
        self.assertGreaterEqual(local.hour, 12)
        self.assertLess(local.hour, 20)

    def test_dst_timezone_generation(self):
        belgium = TravelAvailability.objects.create(location_name="Belçika", timezone="Europe/Brussels", start_date=date(2026, 10, 24), end_date=date(2026, 10, 26), local_available_start=time(9), local_available_end=time(17))
        before = generate_slots(belgium, date(2026, 10, 24))[0].start_at_utc.astimezone(ZoneInfo("Europe/Brussels"))
        after = generate_slots(belgium, date(2026, 10, 26))[0].start_at_utc.astimezone(ZoneInfo("Europe/Brussels"))
        self.assertEqual(before.date(), date(2026, 10, 24))
        self.assertEqual(after.date(), date(2026, 10, 26))

    def test_today_cannot_be_booked(self):
        slot = MeetingSlot.objects.create(availability=self.availability, local_date=timezone.localdate(), start_at_utc=timezone.now() + timedelta(hours=2), end_at_utc=timezone.now() + timedelta(hours=3, minutes=30))
        with self.assertRaises(ValueError):
            reserve_slot(self.user, slot.pk)

    def test_tomorrow_can_be_booked(self):
        slot = generate_slots(self.availability, timezone.localdate() + timedelta(days=1))[0]
        booking = reserve_slot(self.user, slot.pk)
        self.assertEqual(booking.status, "active")

    def test_booked_slot_cannot_be_booked_twice(self):
        slot = generate_slots(self.availability, timezone.localdate() + timedelta(days=1))[0]
        reserve_slot(self.user, slot.pk)
        invitation, _ = SkoolInvitation.create_invitation("İkinci Kişi")
        invitation.status = "claimed"; invitation.save()
        second = SkoolUser.objects.create(invitation=invitation, full_name="İkinci Kişi", audio_completed_at=timezone.now())
        with self.assertRaises(ValueError):
            reserve_slot(second, slot.pk)

    def test_user_cannot_have_two_active_bookings(self):
        slots = generate_slots(self.availability, timezone.localdate() + timedelta(days=1))
        reserve_slot(self.user, slots[0].pk)
        with self.assertRaises(ValueError):
            reserve_slot(self.user, slots[1].pk)

    def test_disabled_date_cannot_be_booked(self):
        target = timezone.localdate() + timedelta(days=1)
        slot = generate_slots(self.availability, target)[0]
        AvailabilityException.objects.create(start_date=target, end_date=target, reason="Seyahat")
        with self.assertRaises(ValueError):
            reserve_slot(self.user, slot.pk)

    def test_reschedule_over_24_hours_keeps_one_booking(self):
        target = timezone.localdate() + timedelta(days=3)
        slots = generate_slots(self.availability, target)
        booking = reserve_slot(self.user, slots[0].pk)
        updated, old = reschedule_booking(self.user, slots[1].pk)
        self.assertEqual(updated.slot_id, slots[1].pk)
        self.assertEqual(MeetingBooking.objects.filter(user=self.user, status="active").count(), 1)
        old.refresh_from_db(); self.assertEqual(old.status, "available")

    def test_reschedule_under_24_hours_is_blocked(self):
        slot = MeetingSlot.objects.create(availability=self.availability, local_date=timezone.localdate() + timedelta(days=1), start_at_utc=timezone.now() + timedelta(hours=23), end_at_utc=timezone.now() + timedelta(hours=24, minutes=30), status="booked")
        MeetingBooking.objects.create(user=self.user, slot=slot, meeting_url="https://meet.google.com/test")
        new_slot = generate_slots(self.availability, timezone.localdate() + timedelta(days=2))[0]
        with self.assertRaises(ValueError):
            reschedule_booking(self.user, new_slot.pk)

    def test_finished_booking_returns_prepared_user_to_calendar(self):
        past_slot = MeetingSlot.objects.create(
            availability=self.availability,
            local_date=timezone.localdate() - timedelta(days=1),
            start_at_utc=timezone.now() - timedelta(hours=3),
            end_at_utc=timezone.now() - timedelta(hours=1, minutes=30),
            status="booked",
        )
        booking = MeetingBooking.objects.create(
            user=self.user, slot=past_slot, meeting_url="https://meet.google.com/test"
        )
        self.user.state = "BOOKED"
        self.user.save(update_fields=("state",))

        session = self.client.session
        session["skool_user_id"] = self.user.pk
        session.save()
        response = self.client.get(reverse("skool:journey"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["booking"])
        self.assertContains(response, "Volkan ile 90 Dakikalık Görüşmeni Planla")
        self.assertNotContains(response, "Görüşmeniz planlandı")
        booking.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(booking.status, "completed")
        self.assertEqual(self.user.state, "READY_TO_BOOK")


class AvailabilityAdminFormTests(TestCase):
    def test_travel_availability_can_be_single_day(self):
        form = TravelAvailabilityForm(data={
            "location_name": "İstanbul", "timezone": "Europe/Istanbul",
            "start_date": "2026-09-01", "end_date": "",
            "local_available_start": "09:00", "local_available_end": "17:00",
            "enabled": True,
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["end_date"], date(2026, 9, 1))

    def test_exception_can_be_single_day_or_range(self):
        single = AvailabilityExceptionForm(data={
            "start_date": "2026-09-02", "end_date": "", "reason": "Tek gün"
        })
        ranged = AvailabilityExceptionForm(data={
            "start_date": "2026-09-03", "end_date": "2026-09-05", "reason": "Aralık"
        })
        self.assertTrue(single.is_valid(), single.errors)
        self.assertTrue(ranged.is_valid(), ranged.errors)
        self.assertEqual(single.cleaned_data["end_date"], date(2026, 9, 2))
        self.assertEqual(ranged.cleaned_data["end_date"], date(2026, 9, 5))


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class AdminAndTelegramTests(TestCase):
    def test_admin_dashboard_requires_authentication(self):
        response = self.client.get(reverse("skool:admin_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_view_private_answers(self):
        staff = get_user_model().objects.create_user(username="admin", email="admin@example.com", password="pass", is_staff=True)
        invitation, _ = SkoolInvitation.create_invitation("Test Kişi")
        invitation.status = "claimed"; invitation.save()
        user = SkoolUser.objects.create(invitation=invitation, full_name="Test Kişi")
        CareerTestAnswer.objects.create(user=user, question_id=1, question_text=QUESTIONS[0][1], selected_option="Evet")
        self.client.force_login(staff)
        response = self.client.get(reverse("skool:admin_user", args=[user.pk]))
        self.assertContains(response, "Üniversite mezunu")
        self.assertContains(response, "Cevap: <strong>Evet</strong>", html=True)

    @override_settings(TELEGRAM_ADMIN_CHAT_ID="123", TELEGRAM_WEBHOOK_SECRET="secret")
    @patch("skool.views.send_telegram")
    def test_telegram_create_only_accepts_admin_and_creates_hashed_token(self, notify):
        payload = {"message": {"chat": {"id": 123}, "text": "/create Ayşe Kaya"}}
        response = self.client.post(reverse("skool:telegram_webhook"), json.dumps(payload), content_type="application/json", HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="secret")
        self.assertEqual(response.status_code, 200)
        invitation = SkoolInvitation.objects.get(full_name="Ayşe Kaya")
        self.assertEqual(len(invitation.token_hash), 64)
        self.assertNotIn("Ayşe", invitation.token_hash)
        notify.assert_called_once()

    @override_settings(TELEGRAM_ADMIN_CHAT_ID="123", TELEGRAM_WEBHOOK_SECRET="secret")
    @patch("skool.views.send_telegram")
    def test_telegram_grcustasi_create_alias(self, notify):
        payload = {"message": {"chat": {"id": 123}, "text": "grcustasi create Volkan Güler"}}
        response = self.client.post(reverse("skool:telegram_webhook"), json.dumps(payload), content_type="application/json", HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="secret")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SkoolInvitation.objects.filter(full_name="Volkan Güler").exists())
        notify.assert_called_once()

    def test_admin_can_create_multiple_invitations_without_token_collision(self):
        admin = get_user_model().objects.create_superuser(username="root", email="root@example.com", password="pass")
        self.client.force_login(admin)
        url = reverse("admin:skool_skoolinvitation_add")
        self.assertEqual(self.client.post(url, {"full_name": "Birinci Kişi", "status": "invited", "_save": "Kaydet"}).status_code, 302)
        self.assertEqual(self.client.post(url, {"full_name": "İkinci Kişi", "status": "invited", "_save": "Kaydet"}).status_code, 302)
        self.assertEqual(SkoolInvitation.objects.count(), 2)
        self.assertTrue(all(len(value) == 64 for value in SkoolInvitation.objects.values_list("token_hash", flat=True)))

    @override_settings(TELEGRAM_ADMIN_CHAT_ID="123", TELEGRAM_WEBHOOK_SECRET="secret")
    def test_telegram_rejects_bad_webhook_secret(self):
        response = self.client.post(reverse("skool:telegram_webhook"), "{}", content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_notification_log_key_is_unique(self):
        NotificationLog.objects.create(key="same", notification_type="telegram")
        with self.assertRaises(IntegrityError):
            NotificationLog.objects.create(key="same", notification_type="telegram")
