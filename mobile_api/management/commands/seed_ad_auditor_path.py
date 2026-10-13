import json
from django.core.management.base import BaseCommand
from mobile_api.ad_auditor import seed
class Command(BaseCommand):
    help='Yalnız web AD denetçi yolunu oluşturur; varsayılan dry-run.'
    def add_arguments(self,p):p.add_argument('--apply',action='store_true')
    def handle(self,*a,**o):self.stdout.write(json.dumps(seed(dry_run=not o['apply']),ensure_ascii=False,indent=2))
