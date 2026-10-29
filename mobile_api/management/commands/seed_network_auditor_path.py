import json
from django.core.management.base import BaseCommand
from mobile_api.network_auditor import seed,assign_paid
from mobile_api.models import LearningPath
class Command(BaseCommand):
    help='55 görselli ağ sorusunu yayınlar ve ücretli üyelere atar; varsayılan dry-run.'
    def add_arguments(self,p):p.add_argument('--apply',action='store_true')
    def handle(self,*a,**o):
        result=seed(dry_run=not o['apply'])
        if o['apply']:result['assigned']=assign_paid(LearningPath.objects.get(pk=result['path_id']))
        self.stdout.write(json.dumps(result,ensure_ascii=False))
