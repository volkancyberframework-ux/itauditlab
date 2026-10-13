import json
from django.core.management.base import BaseCommand
from mobile_api.cisa_simulator import seed

class Command(BaseCommand):
    help = 'Yalnız özgün CISA denetçi simülasyonunu idempotent olarak oluşturur.'
    def add_arguments(self, parser):
        parser.add_argument('--apply',action='store_true',help='Yazmayı uygula; varsayılan dry-run.')
    def handle(self,*args,**options):
        self.stdout.write(json.dumps(seed(dry_run=not options['apply']),ensure_ascii=False,indent=2))
