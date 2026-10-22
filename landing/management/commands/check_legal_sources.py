import json
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.utils import timezone
from landing.models import LegalRegulation
from landing.legal_sources import fingerprint

class Command(BaseCommand):
    help='Report stale/broken/possibly changed official sources without publishing any legal changes.'
    def add_arguments(self,parser):
        parser.add_argument('--country')
        parser.add_argument('--limit',type=int,default=100)
    def handle(self,*args,**options):
        qs=LegalRegulation.objects.all()
        if options['country']: qs=qs.filter(country_code=options['country'].upper())
        rows=list(qs[:max(0,min(options['limit'],100))])
        def inspect(row):
            try:
                digest=fingerprint(row.official_source_url)
                result='changed: editorial review required' if row.source_hash and row.source_hash!=digest else 'reachable: content is not legally re-verified'
                return row,digest,result
            except Exception as exc:
                return row,'','unreachable: '+str(exc)[:160]
        with ThreadPoolExecutor(max_workers=4) as executor:
            for row,digest,result in executor.map(inspect,rows):
                # Keep the first baseline until an editor explicitly clears it.
                changes={'checked_at':timezone.now(),'link_status':result}
                if digest and not row.source_hash:changes['source_hash']=digest
                LegalRegulation.objects.filter(pk=row.pk).update(**changes)
                age=(timezone.localdate()-row.last_verified_at).days if row.last_verified_at else None
                self.stdout.write(json.dumps({'id':row.pk,'result':result,'age_days':age,'stale':age is None or age>90},ensure_ascii=False))
