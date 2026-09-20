from django.core.management.base import BaseCommand
from workspace.models import Notification, ControlEmail
from workspace.notifications import deliver, deliver_email
class Command(BaseCommand):
    help='Bekleyen Telegram bildirimlerini yeniden gönderir.'
    def handle(self,*args,**options):
        for pk in Notification.objects.filter(delivered_at__isnull=True).order_by('pk').values_list('pk',flat=True)[:100]:
            deliver(pk)

        for pk in ControlEmail.objects.filter(delivered_at__isnull=True).order_by('pk').values_list('pk',flat=True)[:100]:
            deliver_email(pk)
