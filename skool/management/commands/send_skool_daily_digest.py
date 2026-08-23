from datetime import timedelta
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone

from skool.models import MeetingBooking, TravelAvailability
from skool.services import send_telegram


class Command(BaseCommand):
    help = "Volkan'ın bulunduğu yerde saat 09:00 ise günlük Skool görüşme özetini Telegram'a yollar."

    def handle(self, *args, **options):
        now = timezone.now()
        candidates = TravelAvailability.objects.filter(
            enabled=True,
            start_date__lte=(now + timedelta(days=1)).date(),
            end_date__gte=(now - timedelta(days=1)).date(),
        )
        for availability in candidates:
            local_now = now.astimezone(ZoneInfo(availability.timezone))
            if not availability.start_date <= local_now.date() <= availability.end_date:
                continue
            if local_now.hour != 9:
                continue
            key = f"skool-digest:{availability.pk}:{local_now.date().isoformat()}"
            bookings = MeetingBooking.objects.filter(
                status="active", slot__availability=availability, slot__local_date=local_now.date()
            ).select_related("user", "slot").order_by("slot__start_at_utc")
            if bookings:
                lines = [f"☀️ Günaydın Volkan\n\nBugün {bookings.count()} Skool görüşmen var.\n"]
                for index, booking in enumerate(bookings, 1):
                    start = booking.slot.start_at_utc.astimezone(ZoneInfo(availability.timezone))
                    end = booking.slot.end_at_utc.astimezone(ZoneInfo(availability.timezone))
                    lines.append(f"{index}. {booking.user.full_name}\n{start:%H:%M} – {end:%H:%M}\nTest: ✅\nPodcast: ✅\n")
                lines.append(f"🔗 Tüm görüşmeler:\n{bookings[0].meeting_url}")
                message = "\n".join(lines)
            else:
                message = "☀️ Bugün planlanmış Skool görüşmesi bulunmuyor."
            if send_telegram(message, idempotency_key=key):
                self.stdout.write(self.style.SUCCESS(f"Özet gönderildi: {availability.location_name}"))
