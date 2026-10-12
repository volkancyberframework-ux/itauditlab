import json
from django.core.management.base import BaseCommand
from mobile_api.first30_revision import apply_revision,rollback_revision
class Command(BaseCommand):
    help='Apply the approved roles/variety/lessons/audio revision. No answer or progress deletion.'
    def add_arguments(self,p):p.add_argument('--apply',action='store_true');p.add_argument('--rollback',action='store_true')
    def handle(self,*a,**o):
        if o['rollback']:
            if o['apply']:rollback_revision();self.stdout.write('Revizyon geri alındı; kullanıcı verileri korundu.')
            else:self.stdout.write('Geri almak için --rollback --apply kullan.')
            return
        self.stdout.write(json.dumps(apply_revision(dry_run=not o['apply']),ensure_ascii=False,indent=2))
