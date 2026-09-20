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
    queue((request.tenant.name if getattr(request,'tenant',None) else 'Denetim Konsolu')+' · Başarılı giriş\n'+user.email)

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

from .models import Control, ControlEmail, Membership
from django.core.mail import send_mail

@receiver(post_save,sender=Control)
def new_control_email(sender,instance,created,raw=False,**kwargs):
    if raw:return
    if not created:
        from .models import Evaluation
        Evaluation.objects.filter(control=instance,verified=True).update(verified=False)
        return
    if instance.audit.phase!='completed':return
    audit=instance.audit
    org=audit.organization
    url=f'https://{org.subdomain}.{settings.TENANT_BASE_DOMAIN}/console/{audit.pk}/controls/{instance.pk}/' if org.subdomain else 'Kurum denetim konsolunuzdan kontrolü açın.'
    body=f'''{org.name} denetimine yeni kontrol eklendi.

Denetim: {audit.title}
Kontrol: {instance.code} · {instance.title}
Çerçeve: {instance.framework}
Risk: {instance.get_risk_display()}

Kontrol açıklaması:
{instance.description}

Beklenen kanıtlar / test rehberi:
{instance.evidence_guidance}

BT yanıtınızı kaydetmek için:
{url}
'''
    for membership in Membership.objects.filter(audit=audit,role='it',user__is_active=True).select_related('user'):
        item,new=ControlEmail.objects.get_or_create(control=instance,recipient=membership.user,defaults={'email':membership.user.email,'subject':('Yeni kontrol: '+instance.code+' · '+instance.title).replace('\n',' ').replace('\r',' ')[:250],'body':body})
        if new:transaction.on_commit(lambda pk=item.pk:deliver_email(pk),robust=True)

def deliver_email(pk):
    with transaction.atomic():
        item=ControlEmail.objects.select_for_update().select_related('control__audit','recipient').get(pk=pk)
        if item.delivered_at:return
        if not item.recipient.is_active or not Membership.objects.filter(user=item.recipient,audit=item.control.audit,role='it').exists():return
        if settings.EMAIL_BACKEND.endswith('smtp.EmailBackend') and not settings.EMAIL_HOST:return
        item.attempts+=1
        try:
            if send_mail(item.subject,item.body,settings.DEFAULT_FROM_EMAIL,[item.recipient.email],fail_silently=False):item.delivered_at=timezone.now()
        except Exception:logger.warning('Kontrol e-postası gönderilemedi; yeniden denenecek.')
        item.save(update_fields=['attempts','delivered_at'])
