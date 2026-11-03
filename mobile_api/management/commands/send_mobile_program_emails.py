from django.core.management.base import BaseCommand
from mobile_api.program_mail import CATALOGUE_KEY, public_paths, recipients, prepare_campaign, drain
from mobile_api.models import ProgramEmailDelivery


class Command(BaseCommand):
    help = 'Mobil program e-postaları: --catalogue mevcut programları tek seferlik duyurur; varsayılan yalnızca önizlemedir.'

    def add_arguments(self, parser):
        parser.add_argument('--catalogue', action='store_true')
        parser.add_argument('--send', action='store_true')

    def handle(self, *args, **options):
        for title in public_paths().values_list('title', flat=True):
            self.stdout.write(title)
        self.stdout.write(f'Uygun mobil hesap: {recipients().count()}')
        if not options['send']:
            self.stdout.write('Önizleme; e-posta gönderilmedi.')
            return
        campaign = prepare_campaign(CATALOGUE_KEY, public_paths()) if options['catalogue'] else None
        if options['catalogue'] and campaign is None:
            self.stdout.write('Duyurulacak program yok.')
            return
        sent = drain(campaign)
        pending = ProgramEmailDelivery.objects.filter(sent_at=None)
        if campaign:
            pending = pending.filter(campaign=campaign)
        self.stdout.write(f'SMTP kabul edilen: {sent}; bekleyen: {pending.count()}')
