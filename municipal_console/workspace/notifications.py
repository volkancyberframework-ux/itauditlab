import json
import logging
from urllib.request import Request, urlopen
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import Activity, Notification
from django.utils import timezone
logger=logging.getLogger(__name__)

def send(message):
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False
    payload=json.dumps({'chat_id':settings.TELEGRAM_CHAT_ID,'text':message[:4000]}).encode()
    try:
        req=Request('https://api.telegram.org/bot'+settings.TELEGRAM_BOT_TOKEN+'/sendMessage',data=payload,headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=4) as result:
            return bool(json.load(result).get('ok'))
    except Exception:
        # Never log the URL containing the bot secret or private audit content.
        logger.warning('Telegram bildirimi gönderilemedi.')
        return False

@receiver(user_logged_in)
def login_notification(sender,request,user,**kwargs):
    queue('Torbalı Belediyesi · Başarılı giriş\n'+user.email)

@receiver(post_save,sender=Activity)
def activity_notification(sender,instance,created,**kwargs):
    if created:
        message=f'{instance.audit.organization.name} · {instance.action}\nDenetim: {instance.audit.title}\nRol: {instance.role}\nKullanıcı: {instance.actor.email if instance.actor else "Sistem"}'
        queue(message)

def deliver(notification_id):
    with transaction.atomic():
        item=Notification.objects.select_for_update().get(pk=notification_id)
        if item.delivered_at: return
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID: return
        item.attempts+=1
        if send(item.message): item.delivered_at=timezone.now()
        item.save(update_fields=['attempts','delivered_at'])

def queue(message):
    item=Notification.objects.create(message=message)
    transaction.on_commit(lambda: deliver(item.pk), robust=True)
