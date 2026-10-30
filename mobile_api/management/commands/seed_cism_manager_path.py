import json
from django.core.management.base import BaseCommand
from mobile_api.cism_manager import seed
from mobile_api.grc_bootcamp import assign_paid
from mobile_api.models import LearningPath
class Command(BaseCommand):
    help='Yeni ücretli öğrenme yolunu doğrular; --apply ile yayınlar ve ücretli mobil üyelere atar.'
    def add_arguments(self, parser): parser.add_argument('--apply',action='store_true')
    def handle(self,*args,**options):
        result=seed(dry_run=not options['apply'])
        if options['apply']: result['assigned']=assign_paid(LearningPath.objects.get(pk=result['path_id']))
        self.stdout.write(json.dumps(result,ensure_ascii=False))
