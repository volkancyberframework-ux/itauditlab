import itertools
import json
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
REPEAT_BOOKING_WAIT_DAYS = 14


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


def earliest_repeat_booking_date(user, display_zone=None):
    """Return the first selectable Istanbul date after the latest completed meeting."""
    latest = (
        MeetingBooking.objects.filter(user=user, status="completed")
        .select_related("slot")
        .order_by("-slot__start_at_utc")
        .first()
    )
    if latest is None:
        return None
    zone = display_zone or ZoneInfo(SkoolSettings.load().display_timezone)
    return latest.slot.start_at_utc.astimezone(zone).date() + timedelta(days=REPEAT_BOOKING_WAIT_DAYS)


def send_telegram(text, *, idempotency_key=None, reply_markup=None):
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
    data={"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if reply_markup is not None:
        data["reply_markup"]=json.dumps(reply_markup,ensure_ascii=False)
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data, timeout=10,
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
    base = getattr(settings, "PUBLIC_BASE_URL", "https://www.grcustasi.com").rstrip("/")
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
        occupied = list(MeetingSlot.objects.filter(local_date=local_date).exclude(availability=locked)) + existing
        valid = [slot for slot in existing if slot_is_current(slot)]
        if len(valid) >= 3:
            return valid[:3]
        config = SkoolSettings.load()
        duration = config.meeting_duration_minutes
        start_min = locked.local_available_start.hour * 60 + locked.local_available_start.minute
        end_min = locked.local_available_end.hour * 60 + locked.local_available_end.minute
        starts = list(range(start_min, end_min - duration + 1, 15))
        chosen = None
        for gap in range(config.minimum_gap_minutes, -1, -5):
            viable = [combo for combo in itertools.combinations(starts, 3 - len(valid))
                      if all(b >= a + duration + gap for a, b in zip(combo, combo[1:]))
                      and all(not (datetime.combine(local_date, time(m // 60, m % 60), tzinfo=ZoneInfo(locked.timezone)) < old.end_at_utc
                                   and datetime.combine(local_date, time(m // 60, m % 60), tzinfo=ZoneInfo(locked.timezone)) + timedelta(minutes=duration) > old.start_at_utc)
                              for m in combo for old in occupied)]
            if viable:
                chosen = secrets.choice(viable)
                break
        if not chosen:
            # Closed slots and real reservations take precedence over filling a quota.
            return valid
        zone = ZoneInfo(locked.timezone)
        slots = []
        for minute in chosen:
            local_start = datetime.combine(local_date, time(minute // 60, minute % 60), tzinfo=zone)
            utc_start = local_start.astimezone(ZoneInfo("UTC"))
            slots.append(MeetingSlot.objects.create(
                availability=locked, local_date=local_date, start_at_utc=utc_start,
                end_at_utc=utc_start + timedelta(minutes=duration),
            ))
        return valid + slots


ISTANBUL = ZoneInfo("Europe/Istanbul")
BOOKING_HORIZON_DAYS = 60


def slot_is_current(slot):
    """Validate cached slots against today's schedule, never mutate reservations."""
    a = slot.availability
    start = slot.start_at_utc.astimezone(ZoneInfo(a.timezone))
    end = slot.end_at_utc.astimezone(ZoneInfo(a.timezone))
    return (a.enabled and a.start_date <= start.date() <= a.end_date
            and slot.local_date == start.date() == end.date()
            and a.local_available_start <= start.time().replace(tzinfo=None)
            and end.time().replace(tzinfo=None) <= a.local_available_end)


def ensure_upcoming_slots(days=BOOKING_HORIZON_DAYS):
    today = timezone.localdate(timezone=ISTANBUL)
    horizon = today + timedelta(days=days)
    # Continue the last host schedule within the existing rolling 60-day horizon.
    # Historical travel rows and their reservations remain intact.
    with transaction.atomic():
        latest = TravelAvailability.objects.select_for_update().filter(enabled=True).order_by("-end_date", "-pk").first()
        if latest and latest.end_date < horizon:
            continuation = TravelAvailability.objects.create(
                location_name=latest.location_name, timezone=latest.timezone,
                start_date=max(today + timedelta(days=1), latest.end_date + timedelta(days=1)),
                end_date=horizon, local_available_start=latest.local_available_start,
                local_available_end=latest.local_available_end, enabled=True,
            )
            for exception in latest.exceptions.filter(end_date__gte=continuation.start_date):
                AvailabilityException.objects.create(availability=continuation,
                    start_date=exception.start_date, end_date=exception.end_date, reason=exception.reason)
    availabilities = list(TravelAvailability.objects.filter(enabled=True, end_date__gte=today).order_by("-start_date", "-pk"))
    for offset in range(1, days + 1):
        day = today + timedelta(days=offset)
        active = next((a for a in availabilities if a.start_date <= day <= a.end_date), None)
        if active:
            generate_slots(active, day)


def published_slots(first_date=None):
    """One authoritative schedule per date; no stale travel slots or duplicate days."""
    today = timezone.localdate(timezone=ISTANBUL)
    first_date = max(first_date or today, today + timedelta(days=1))
    schedules = list(TravelAvailability.objects.filter(enabled=True).order_by("-start_date", "-pk"))
    exceptions = list(AvailabilityException.objects.all())
    counts = {}
    occupied = list(MeetingSlot.objects.filter(status="booked", start_at_utc__gt=timezone.now()))
    result = []
    for slot in MeetingSlot.objects.filter(start_at_utc__gt=timezone.now(),
            local_date__gte=first_date, local_date__lte=today + timedelta(days=BOOKING_HORIZON_DAYS)
            ).select_related("availability").order_by("start_at_utc"):
        day = slot.start_at_utc.astimezone(ISTANBUL).date()
        active = next((a for a in schedules if a.start_date <= slot.local_date <= a.end_date), None)
        if day < first_date or not active or active.pk != slot.availability_id or not slot_is_current(slot):
            continue
        if any(e.start_date <= slot.local_date <= e.end_date and
               e.availability_id in (None, slot.availability_id) for e in exceptions):
            continue
        if slot.status == "available" and any(other.pk != slot.pk and other.start_at_utc < slot.end_at_utc
                and other.end_at_utc > slot.start_at_utc for other in occupied):
            continue
        if counts.get(day, 0) >= 3:
            continue
        counts[day] = counts.get(day, 0) + 1
        result.append(slot)
    return result


def validate_bookable_slot(slot):
    if slot.status != "available" or not any(s.pk == slot.pk for s in published_slots()):
        raise ValueError("Bu görüşme saati artık müsait değil.")


def reserve_slot(user, slot_id):
    finalize_expired_bookings(user)
    with transaction.atomic():
        if MeetingBooking.objects.select_for_update().filter(user=user, status="active").exists():
            raise ValueError("Zaten aktif bir görüşmeniz var.")
        slot = MeetingSlot.objects.select_for_update().select_related("availability").get(pk=slot_id)
        display_zone = ZoneInfo("Europe/Istanbul")
        earliest_repeat_date = earliest_repeat_booking_date(user, display_zone)
        slot_display_date = slot.start_at_utc.astimezone(display_zone).date()
        if earliest_repeat_date and slot_display_date < earliest_repeat_date:
            raise ValueError(
                "İkinci ve sonraki görüşmeler, önceki görüşmeden en erken 14 gün sonrasına planlanabilir."
            )
        validate_bookable_slot(slot)
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
        validate_bookable_slot(new_slot)
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
