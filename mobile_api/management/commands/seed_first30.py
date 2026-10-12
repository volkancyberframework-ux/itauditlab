import json
from django.core.management.base import BaseCommand
from mobile_api.first30_content import import_package
class Command(BaseCommand):
    help='Validate or publish the scoped 100-record first-30-days package.'
    def add_arguments(self,p):
        p.add_argument('--path-id',type=int,default=26)
        p.add_argument('--package')
        p.add_argument('--apply',action='store_true',help='Explicitly write and publish; default is dry-run.')
    def handle(self,*a,**o):
        self.stdout.write(json.dumps(import_package(source=o['package'],path_id=o['path_id'],dry_run=not o['apply']),ensure_ascii=False,indent=2))
