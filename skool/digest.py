from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from core.models import MentorshipRequest, StudentMeetingBooking
from skool.models import MeetingBooking
from skool.services import send_telegram


def send_daily_meeting_digest(report_date=None):
    """Skool ve normal öğrenci görüşmelerini tek günlük Telegram özetinde birleştirir."""
    report_timezone = ZoneInfo("Europe/Istanbul")
    report_date = report_date or timezone.now().astimezone(report_timezone).date()
    start = datetime.combine(report_date, time.min, tzinfo=report_timezone)
    end = start + timedelta(days=1)
    key = f"meeting-digest:{report_date.isoformat()}"

    skool_bookings = list(MeetingBooking.objects.filter(
        status="active", slot__start_at_utc__gte=start, slot__start_at_utc__lt=end,
    ).select_related("user", "slot").order_by("slot__start_at_utc"))
    student_bookings = list(StudentMeetingBooking.objects.filter(
        status="active", slot__start_at_utc__gte=start, slot__start_at_utc__lt=end,
    ).select_related("user", "request", "slot").order_by("slot__start_at_utc"))

    total = len(skool_bookings) + len(student_bookings)
    if total:
        lines = [f"☀️ Günaydın Volkan\n\nBugün {total} birebir görüşmen var."]
        position = 1
        for booking in skool_bookings:
            booking_start = booking.slot.start_at_utc.astimezone(report_timezone)
            booking_end = booking.slot.end_at_utc.astimezone(report_timezone)
            lines.append(
                f"\n{position}. {booking.user.full_name} • Skool\n"
                f"{booking_start:%H:%M} – {booking_end:%H:%M}\n"
                f"Test: ✅ • Podcast: ✅"
            )
            position += 1
        for booking in student_bookings:
            booking_start = booking.slot.start_at_utc.astimezone(report_timezone)
            booking_end = booking.slot.end_at_utc.astimezone(report_timezone)
            course_name = booking.request.course.turkish_name or booking.request.course.english_name
            lines.append(
                f"\n{position}. {booking.user.get_full_name() or booking.user.username} • Normal öğrenci\n"
                f"📧 {booking.user.email}\n{booking_start:%H:%M} – {booking_end:%H:%M}\n"
                f"📚 {course_name}\n📝 {booking.request.reason}"
            )
            position += 1
        message = "\n".join(lines)
    else:
        message = "☀️ Günaydın Volkan\n\nBugün planlanmış birebir görüşmen yok."

    requests = MentorshipRequest.objects.filter(
        created_at__date=report_date - timedelta(days=1)
    ).select_related("user")
    if requests:
        lines = [message, "", f"📨 Dün gelen {requests.count()} öğrenci talebi:"]
        for item in requests[:20]:
            lines.append(
                f"• {item.user.get_full_name() or item.user.username} — {item.get_request_type_display()}\n"
                f"  📧 {item.user.email}\n"
                f"  {item.course.turkish_name or item.course.english_name}: {item.reason}"
            )
        message = "\n".join(lines)

    return send_telegram(message, idempotency_key=key)
