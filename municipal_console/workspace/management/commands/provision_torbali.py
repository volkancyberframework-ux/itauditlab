from django.core.management.base import BaseCommand
from workspace.models import Organization,Audit
class Command(BaseCommand):
    help='Torbalı kurumunu ve boş gerçek denetimini oluşturur; demo hesabı oluşturmaz.'
    def handle(self,*args,**options):
        org,_=Organization.objects.get_or_create(slug='torbali-belediyesi',defaults={'name':'Torbalı Belediyesi','subdomain':'torbalibld'})
        Audit.objects.get_or_create(organization=org,archived=False,is_demo=False,defaults={'title':'Kurumsal Bilgi Güvenliği Denetimi'})
        self.stdout.write('Kurum hazır. createsuperuser ile bağımsız yönetici oluşturun; /admin/ üzerinden kontrolleri ve üyelikleri ekleyin.')
