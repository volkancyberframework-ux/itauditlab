from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone

from skool.models import MeetingBooking
from skool.services import send_telegram
from core.models import MentorshipRequest


class Command(BaseCommand):
    help = "Türkiye saati 09:00'da günlük Skool görüşme özetini Telegram'a yollar."

    def handle(self, *args, **options):
        report_timezone = ZoneInfo("Europe/Istanbul")
        local_now = timezone.now().astimezone(report_timezone)
        if local_now.hour != 9:
            return

        report_date = local_now.date()
        start = datetime.combine(report_date, time.min, tzinfo=report_timezone)
        end = start + timedelta(days=1)
        key = f"skool-digest:{report_date.isoformat()}"
        bookings = MeetingBooking.objects.filter(
            status="active", slot__start_at_utc__gte=start, slot__start_at_utc__lt=end
        ).select_related("user", "slot").order_by("slot__start_at_utc")
        if bookings:
            lines = [f"☀️ Günaydın Volkan\n\nBugün {bookings.count()} Skool görüşmen var.\n"]
            for index, booking in enumerate(bookings, 1):
                booking_start = booking.slot.start_at_utc.astimezone(report_timezone)
                booking_end = booking.slot.end_at_utc.astimezone(report_timezone)
                lines.append(f"{index}. {booking.user.full_name}\n{booking_start:%H:%M} – {booking_end:%H:%M}\nTest: ✅\nPodcast: ✅\n")
            lines.append(f"🔗 Tüm görüşmeler:\n{bookings[0].meeting_url}")
            message = "\n".join(lines)
        else:
            message = "☀️ Bugün planlanmış Skool görüşmesi bulunmuyor."
        requests = MentorshipRequest.objects.filter(
            created_at__date=report_date - timedelta(days=1)
        ).select_related("user", "course")
        if requests:
            lines = [message, "", f"📨 Dün gelen {requests.count()} öğrenci talebi:"]
            for item in requests[:20]:
                lines.append(
                    f"• {item.user.get_full_name() or item.user.username} — {item.get_request_type_display()}\n"
                    f"  {item.course.turkish_name or item.course.english_name}: {item.reason}"
                )
            message = "\n".join(lines)
        if send_telegram(message, idempotency_key=key):
            self.stdout.write(self.style.SUCCESS("Günlük Skool görüşme özeti gönderildi."))
