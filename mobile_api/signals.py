from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import VoiceSubmission
from .alerts import queue_alert


@receiver(post_save, sender=get_user_model(), dispatch_uid='mobile_signup_telegram')
def mobile_signup(sender, instance, created, raw=False, **kwargs):
    if created and not raw and instance.is_mobile:
        base = settings.PUBLIC_BASE_URL.rstrip('/')
        queue_alert(f'signup-{instance.pk}', f'📱 Yeni mobil hesap\n\n{instance.get_full_name() or instance.username}\n{instance.email}\n\nHesap: {base}/bulamazsinki/core/customuser/{instance.pk}/change/')


@receiver(post_save, sender=VoiceSubmission, dispatch_uid='mobile_voice_telegram')
def mobile_voice(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        user = instance.attempt.session.user
        base = settings.PUBLIC_BASE_URL.rstrip('/')
        queue_alert(f'voice-{instance.pk}', f'🎙️ İnceleme bekleyen mobil sesli yanıt\n\n{user.get_full_name() or user.username}\n{user.email}\nYol: {instance.attempt.session.path.title}\nSoru: {instance.attempt.question.prompt[:180]}\n\n24 saat içinde inceleyip e-posta geri bildirimi verin.\n{base}/bulamazsinki/mobile_api/voicesubmission/{instance.pk}/change/')
