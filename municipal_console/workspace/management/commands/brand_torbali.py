from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from workspace.models import Audit
class Command(BaseCommand):
    help='Apply Torbali demo branding without resetting responses, phases or findings.'
    @transaction.atomic
    def handle(self,*args,**kwargs):
        if not settings.DEBUG:raise CommandError('Demo markalama yalnızca geliştirme ortamında çalışır.')
        audit=Audit.objects.filter(archived=False,is_demo=True).select_related('organization').first()
        if not audit:raise CommandError('Önce demo denetimi oluşturun.')
        org=audit.organization;org.name='Torbalı Belediyesi';org.slug='torbali-belediyesi';org.save(update_fields=['name','slug'])
        audit.title='2026 Kurumsal Bilgi Güvenliği Denetimi';audit.save(update_fields=['title'])
        self.stdout.write('Torbalı Belediyesi markası uygulandı; denetim verileri korundu.')
