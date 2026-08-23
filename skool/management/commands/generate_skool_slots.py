from django.core.management.base import BaseCommand

from skool.services import ensure_upcoming_slots


class Command(BaseCommand):
    help = "Önümüzdeki 60 günün kalıcı Skool görüşme slotlarını üretir."

    def handle(self, *args, **options):
        ensure_upcoming_slots()
        self.stdout.write(self.style.SUCCESS("Skool slotları hazır."))
