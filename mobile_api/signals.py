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


from .models import WorkshopVoice
from django.db.models.signals import post_delete


@receiver(post_save, sender=WorkshopVoice, dispatch_uid='workshop_voice_telegram')
def workshop_voice(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        base = settings.PUBLIC_BASE_URL.rstrip('/')
        queue_alert(f'workshop-voice-{instance.pk}', f'🎙️ Giriş öncesi atölye sesli yanıtı\n\n{instance.email}\nSoru: {instance.question.prompt[:180]}\n\n24 saat içinde inceleyip e-posta geri bildirimi verin.\n{base}/bulamazsinki/mobile_api/workshopvoice/{instance.pk}/change/')


@receiver(post_delete, sender=WorkshopVoice, dispatch_uid='workshop_voice_cleanup')
def workshop_voice_cleanup(sender, instance, **kwargs):
    instance.file.delete(save=False)


from django.db import transaction
from django.db.models.signals import m2m_changed
from .models import LearningPath, Question


def schedule_program_announcements(sender, instance, raw=False, **kwargs):
    if raw:
        return
    from .program_mail import announce_available
    transaction.on_commit(announce_available, robust=True)


post_save.connect(schedule_program_announcements, sender=LearningPath, dispatch_uid='mobile_path_email')
post_save.connect(schedule_program_announcements, sender=Question, dispatch_uid='mobile_question_path_email')


@receiver(m2m_changed, sender=Question.paths.through, dispatch_uid='mobile_path_content_email')
def path_content_email(sender, instance, action, **kwargs):
    if action == 'post_add':
        schedule_program_announcements(sender, instance)
