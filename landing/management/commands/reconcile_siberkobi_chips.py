from django.core.management.base import BaseCommand
from django.db.models import F, Q
from landing.chip_models import ChipParticipationRequest
from landing.chip_requests import notify


class Command(BaseCommand):
    help = 'Bekleyen Siberkobi katılım talebi bildirimlerini dener. Ödeme almaz veya doğrulamaz.'

    def handle(self, *args, **options):
        rows = ChipParticipationRequest.objects.filter(generation=F('round__generation')).filter(Q(email_sent_at=None) | Q(telegram_sent_at=None))
        for pk in rows.values_list('pk', flat=True):
            notify(pk)
        self.stdout.write(f'Bekleyen katılım talebi bildirimi: {rows.count()}')
