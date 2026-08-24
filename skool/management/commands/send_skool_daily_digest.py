from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone

from skool.digest import send_daily_meeting_digest


class Command(BaseCommand):
    help = "Türkiye saati 09:00'da günlük Skool görüşme özetini Telegram'a yollar."

    def handle(self, *args, **options):
        report_timezone = ZoneInfo("Europe/Istanbul")
        local_now = timezone.now().astimezone(report_timezone)
        if local_now.hour != 9:
            return

        if send_daily_meeting_digest(local_now.date()):
            self.stdout.write(self.style.SUCCESS("Günlük Skool görüşme özeti gönderildi."))
