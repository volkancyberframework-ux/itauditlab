from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from workspace.models import Audit, Control, Organization, Suggestion
from .seed_workspace import CONTROLS
class Command(BaseCommand):
    help='Prepare a fresh, unanswered demo; archive previous demo audit without deleting history.'
    @transaction.atomic
    def handle(self,*args,**kwargs):
        if not settings.DEBUG:raise CommandError('Yalnızca geliştirme ortamında çalışır.')
        org,_=Organization.objects.get_or_create(slug='torbali-belediyesi',defaults={'name':'Torbalı Belediyesi','subdomain':'torbalibld'})
        audit,created=Audit.objects.get_or_create(organization=org,title='2026 Kurumsal Bilgi Güvenliği Denetimi',defaults={'is_demo':True})
        Audit.objects.filter(is_demo=True).exclude(pk=audit.pk).update(archived=True)
        if created:
            for index,(_,title,theme,risk,description,evidence) in enumerate(CONTROLS,1):
                Control.objects.create(audit=audit,code=f'GRC-{index:03d}',title=title,description=description,evidence_guidance=evidence,framework='ISO/IEC 27001:2022' if index<=12 else 'NIST CSF 2.0',theme=theme,risk=risk,intern_visible=True)
        admin=get_user_model().objects.filter(is_superuser=True,email__startswith='demo@').first()
        if admin:
            admin.email='demo@grcustasi.local';admin.save(update_fields=['email'])
        self.stdout.write(f'{audit.controls.count()} kontrol. Yeni kontroller Başlanmadı durumunda; önceki geçmiş arşivlendi.')
