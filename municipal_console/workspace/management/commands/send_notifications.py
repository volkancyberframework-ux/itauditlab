from django.core.management.base import BaseCommand
from workspace.models import Notification
from workspace.notifications import deliver
class Command(BaseCommand):
    help='Bekleyen Telegram bildirimlerini yeniden gönderir.'
    def handle(self,*args,**options):
        for pk in Notification.objects.filter(delivered_at__isnull=True).order_by('pk').values_list('pk',flat=True)[:100]:
            deliver(pk)
