import itertools
import logging
import secrets
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from .models import (
    AvailabilityException, BookingHistory, MeetingBooking, MeetingSlot, NotificationLog,
    OnboardingEvent, SkoolSettings, TravelAvailability,
)

logger = logging.getLogger(__name__)


def finalize_expired_bookings(user=None):
    """Süresi biten randevuları geçmişe alır; tamamlanan hazırlık yeniden istenmez."""
    bookings = MeetingBooking.objects.filter(status="active", slot__end_at_utc__lte=timezone.now())
    if user is not None:
        bookings = bookings.filter(user=user)
    user_ids = list(bookings.values_list("user_id", flat=True))
    updated = bookings.update(status="completed")
    if user_ids:
        from .models import SkoolUser
        SkoolUser.objects.filter(
            pk__in=user_ids,
            test_completed_at__isnull=False,
            audio_completed_at__isnull=False,
        ).update(state="READY_TO_BOOK")
    return updated


def send_telegram(text, *, idempotency_key=None):
    reserved_log = None
    if idempotency_key:
        reserved_log, created = NotificationLog.objects.get_or_create(
            key=idempotency_key, defaults={"notification_type": "telegram", "detail": {"status": "sending"}}
        )
        if not created:
            return False
    token = getattr(settings, "GRCUSTASI_TELEGRAM_BOT_TOKEN", "") or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = (
        getattr(settings, "GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID", "")
        or getattr(settings, "TELEGRAM_ADMIN_CHAT_ID", "")
        or getattr(settings, "TELEGRAM_CHAT_ID", "")
    )
    if not token or not chat_id:
        logger.warning("Skool Telegram bildirimi atlandı: yapılandırma eksik")
        if reserved_log:
            reserved_log.delete()
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text, "disable_web_page_preview": True}, timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException:
        if reserved_log:
            reserved_log.delete()
        raise
    if reserved_log:
        reserved_log.detail = {"status": "sent"}
        reserved_log.save(update_fields=("detail",))
    return True


def admin_user_url(user):
    base = getattr(settings, "PUBLIC_BASE_URL", "https://grcustasi.com").rstrip("/")
    return f"{base}{reverse('skool:admin_user', args=[user.pk])}"


def generate_slots(availability, local_date):
    """Persist three random non-overlapping slots once; all future reads reuse them."""
    if not availability.enabled or not (availability.start_date <= local_date <= availability.end_date):
        return []
    if AvailabilityException.objects.filter(
        Q(availability=availability) | Q(availability__isnull=True),
        start_date__lte=local_date, end_date__gte=local_date,
    ).exists():
        return []
    with transaction.atomic():
        locked = TravelAvailability.objects.select_for_update().get(pk=availability.pk)
        existing = list(locked.slots.filter(local_date=local_date).order_by("start_at_utc"))
        if existing:
            return existing
        config = SkoolSettings.load()
        duration = config.meeting_duration_minutes
        start_min = locked.local_available_start.hour * 60 + locked.local_available_start.minute
        end_min = locked.local_available_end.hour * 60 + locked.local_available_end.minute
        starts = list(range(start_min, end_min - duration + 1, 15))
        chosen = None
        for gap in range(config.minimum_gap_minutes, -1, -5):
            viable = [combo for combo in itertools.combinations(starts, config.daily_slot_count)
                      if all(b >= a + duration + gap for a, b in zip(combo, combo[1:]))]
            if viable:
                chosen = secrets.choice(viable)
                break
        if not chosen:
            raise ValueError("Uygunluk aralığından gerekli slotlar üretilemiyor.")
        zone = ZoneInfo(locked.timezone)
        slots = []
        for minute in chosen:
            local_start = datetime.combine(local_date, time(minute // 60, minute % 60), tzinfo=zone)
            utc_start = local_start.astimezone(ZoneInfo("UTC"))
            slots.append(MeetingSlot.objects.create(
                availability=locked, local_date=local_date, start_at_utc=utc_start,
                end_at_utc=utc_start + timedelta(minutes=duration),
            ))
        return slots


def ensure_upcoming_slots(days=60):
    today = timezone.localdate()
    availabilities = TravelAvailability.objects.filter(enabled=True, end_date__gte=today)
    if not availabilities.exists():
        latest = TravelAvailability.objects.filter(enabled=True).order_by("-end_date").first()
        if latest:
            latest = TravelAvailability.objects.create(
                location_name=latest.location_name,
                timezone=latest.timezone,
                start_date=today + timedelta(days=1),
                end_date=today + timedelta(days=days),
                local_available_start=latest.local_available_start,
                local_available_end=latest.local_available_end,
                enabled=True,
            )
            availabilities = TravelAvailability.objects.filter(pk=latest.pk)
    for availability in availabilities:
        start = max(today + timedelta(days=1), availability.start_date)
        end = min(today + timedelta(days=days), availability.end_date)
        current = start
        while current <= end:
            generate_slots(availability, current)
            current += timedelta(days=1)


def reserve_slot(user, slot_id):
    finalize_expired_bookings(user)
    tomorrow = timezone.localdate(timezone=ZoneInfo("Europe/Istanbul")) + timedelta(days=1)
    with transaction.atomic():
        if MeetingBooking.objects.select_for_update().filter(user=user, status="active").exists():
            raise ValueError("Zaten aktif bir görüşmeniz var.")
        slot = MeetingSlot.objects.select_for_update().select_related("availability").get(pk=slot_id)
        if slot.status != "available" or slot.local_date < tomorrow:
            raise ValueError("Bu görüşme saati artık müsait değil.")
        if AvailabilityException.objects.filter(
            Q(availability=slot.availability) | Q(availability__isnull=True),
            start_date__lte=slot.local_date, end_date__gte=slot.local_date,
        ).exists():
            raise ValueError("Bu tarih rezervasyona kapalı.")
        config = SkoolSettings.load()
        booking = MeetingBooking.objects.create(user=user, slot=slot, meeting_url=config.meet_url)
        slot.status = "booked"
        slot.save(update_fields=("status",))
        user.state = "BOOKED"
        user.save(update_fields=("state", "updated_at"))
        OnboardingEvent.objects.create(user=user, event_type="meeting_booked", detail={"slot": slot.pk})
    return booking


def reschedule_booking(user, new_slot_id):
    with transaction.atomic():
        booking = MeetingBooking.objects.select_for_update().select_related("slot").get(user=user, status="active")
        if booking.slot.start_at_utc <= timezone.now() + timedelta(hours=24):
            raise ValueError("Görüşmenize 24 saatten az kaldığı için sistem üzerinden değişiklik yapılamıyor.")
        new_slot = MeetingSlot.objects.select_for_update().get(pk=new_slot_id)
        if new_slot.status != "available":
            raise ValueError("Yeni görüşme saati artık müsait değil.")
        old_slot = MeetingSlot.objects.select_for_update().get(pk=booking.slot_id)
        new_slot.status = "booked"
        new_slot.save(update_fields=("status",))
        booking.slot = new_slot
        booking.save(update_fields=("slot", "updated_at"))
        old_slot.status = "available"
        old_slot.save(update_fields=("status",))
        BookingHistory.objects.create(booking=booking, old_slot=old_slot, new_slot=new_slot)
        OnboardingEvent.objects.create(user=user, event_type="meeting_rescheduled", detail={"old": old_slot.pk, "new": new_slot.pk})
    return booking, old_slot


def local_booking_lines(booking):
    config = SkoolSettings.load()
    ist = ZoneInfo(config.display_timezone)
    local_zone = ZoneInfo(booking.slot.availability.timezone)
    tr_start, tr_end = booking.slot.start_at_utc.astimezone(ist), booking.slot.end_at_utc.astimezone(ist)
    host_start, host_end = booking.slot.start_at_utc.astimezone(local_zone), booking.slot.end_at_utc.astimezone(local_zone)
    return tr_start, tr_end, host_start, host_end


def booking_notification(booking):
    tr_start, tr_end, host_start, host_end = local_booking_lines(booking)
    send_telegram(
        "📅 Yeni Skool Görüşmesi\n\n"
        f"👤 {booking.user.full_name}\n\n🇹🇷 Türkiye Saati:\n{tr_start:%d.%m.%Y}\n{tr_start:%H:%M} – {tr_end:%H:%M}\n\n"
        f"📍 Volkan'ın bulunduğu yer: {booking.slot.availability.location_name}\n"
        f"Lokal Saat: {host_start:%d.%m.%Y} {host_start:%H:%M} – {host_end:%H:%M}\n\n"
        f"🧠 Test: Tamamlandı\n🎧 Podcast: Tamamlandı\n\n🔗 Meet: {booking.meeting_url}\n👤 Profil: {admin_user_url(booking.user)}",
        idempotency_key=f"booking:{booking.pk}",
    )


# Imported late to keep the model module dependency graph simple.
from django.db.models import Q  # noqa: E402
