from django.core.management.base import BaseCommand

from landing.traffic import send_daily_traffic_report


class Command(BaseCommand):
    help = 'Bir önceki günün GRC Ustası trafik özetini Telegram üzerinden gönderir.'

    def handle(self, *args, **options):
        sent = send_daily_traffic_report()
        self.stdout.write(
            self.style.SUCCESS('Trafik raporu gönderildi.')
            if sent else 'Bu gün için trafik raporu daha önce gönderilmiş.'
        )
