from django.core.management.base import BaseCommand
from landing.models import TravelRegistration
from landing.travel import notify_registration


class Command(BaseCommand):
    help = 'Retry pending Travel Bootcamp Telegram notifications safely.'

    def handle(self, *args, **options):
        pending = TravelRegistration.objects.filter(telegram_sent_at__isnull=True)
        for record_id in pending.values_list('pk', flat=True).iterator():
            notify_registration(record_id)
        self.stdout.write('Pending Travel Bootcamp notifications processed.')
