from datetime import time, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from skool.models import SkoolInvitation, SkoolSettings, TravelAvailability
from skool.services import ensure_upcoming_slots


class Command(BaseCommand):
    help = "Yalnızca development için örnek Skool daveti ve Vietnam uygunluğu oluşturur."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Production ortamında örnek veri oluşturulamaz.")
        availability, _ = TravelAvailability.objects.get_or_create(
            location_name="Vietnam Demo", start_date=timezone.localdate() + timedelta(days=1),
            defaults={"timezone": "Asia/Ho_Chi_Minh", "end_date": timezone.localdate() + timedelta(days=15), "local_available_start": time(12), "local_available_end": time(20)},
        )
        invitation, raw = SkoolInvitation.create_invitation("Volkan Güler")
        SkoolSettings.load()
        ensure_upcoming_slots(15)
        self.stdout.write(self.style.SUCCESS(f"Demo daveti: http://127.0.0.1:8000/skooltoplulugu?invite={raw}"))
