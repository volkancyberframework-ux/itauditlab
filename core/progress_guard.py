"""Opt-in progression guard. Automated releases and unknown completion never trigger sanctions."""
import logging
import uuid
from datetime import datetime, time
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import (CustomUser, LessonEvidence, ProgramEnrollment, ProgramProgressViolation)

logger = logging.getLogger(__name__)
WARNING_VERSION = '2026-10-30-v1'
SALT = 'core.program-progress-confirmation'


def warning_enrollments(user):
    if not user.is_authenticated or user.is_staff or user.is_superuser or not user.is_active:
        return ProgramEnrollment.objects.none()
    return ProgramEnrollment.objects.filter(user=user, is_active=True, program__is_active=True,
                                             progress_warning_enabled=True).select_related('program')


def blockers(user, course):
    # Existing work must remain accessible so the student can finish it.
    if not user.is_authenticated or user.is_staff or user.is_superuser:
        return []
    if LessonEvidence.objects.filter(user=user, course=course, first_accessed_at__isnull=False).exists():
        return []
    now = timezone.now()
    incomplete = set(LessonEvidence.objects.filter(user=user, completion_known=True,
                                                   completed_at__isnull=True).values_list('course_id', flat=True))
    if not incomplete:
        return []
    result = []
    for enrollment in warning_enrollments(user).filter(program__steps__course=course).distinct():
        steps = list(enrollment.program.steps.select_related('course').all())
        target = next((s for s in steps if s.course_id == course.pk), None)
        if target is None:
            continue
        opened = set(enrollment.releases.filter(access_granted_at__lte=now).values_list('step_id', flat=True))
        if target.pk not in opened:
            continue
        exempt = set(enrollment.monitoring_overrides.filter(Q(exempt=True) | Q(required=False)).values_list('step_id', flat=True))
        missing = []
        for step in steps:
            if (step.day_offset, step.order, step.pk) >= (target.day_offset, target.order, target.pk):
                continue
            if step.pk in opened and step.pk not in exempt and step.course_id in incomplete:
                missing.append({'course_id': step.course_id, 'title': str(step.course)})
        if missing:
            result.append({'enrollment_id': enrollment.pk, 'program': enrollment.program.name,
                           'incomplete': missing})
    return result


def issue_confirmation(user, course, findings):
    return signing.dumps({'user': user.pk, 'course': course.pk, 'findings': findings,
                          'nonce': str(uuid.uuid4()), 'version': WARNING_VERSION}, salt=SALT)


def disable_after_confirmation(user, course, token):
    payload = signing.loads(token, salt=SALT, max_age=1800)
    if payload.get('user') != user.pk or payload.get('course') != course.pk or payload.get('version') != WARNING_VERSION:
        raise signing.BadSignature('Yanlış kullanıcı veya ders.')
    with transaction.atomic():
        locked = CustomUser.objects.select_for_update().get(pk=user.pk)
        if not locked.is_active:
            return None
        findings = blockers(locked, course)
        # If evidence or the selected program flag changed, request a fresh decision.
        if not findings or findings != payload.get('findings'):
            return None
        event, created = ProgramProgressViolation.objects.get_or_create(
            confirmation_id=payload['nonce'], defaults={'user': locked, 'email': locked.email,
                'course_id_snapshot': course.pk, 'course_title': str(course), 'programs': findings,
                'warning_version': WARNING_VERSION})
        if not created:
            return None
        locked.is_active = False
        locked.save(update_fields=['is_active'])
        # Revokes refresh credentials too; standard session/JWT auth checks is_active on each request.
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
        for outstanding in OutstandingToken.objects.filter(user=locked):
            BlacklistedToken.objects.get_or_create(token=outstanding)
        transaction.on_commit(lambda: deliver_instant(event.pk), robust=True)
        return event


def telegram(text):
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False
    try:
        with requests.post(f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage',
                           data={'chat_id': settings.TELEGRAM_CHAT_ID, 'text': text[:4000]}, timeout=(3, 8)) as response:
            response.raise_for_status()
            return response.json().get('ok') is True
    except Exception:
        logger.warning('İlerleme ihlali Telegram bildirimi gönderilemedi; sabah yeniden denenecek.')
        return False


def event_message(event, morning=False):
    details = '\n'.join(f"• {p['program']} (Program kaydı #{p['enrollment_id']})\n" +
                        '\n'.join(f"  Course ID: {c['course_id']} — {c['title']}" for c in p['incomplete'])
                        for p in event.programs)
    when = timezone.localtime(event.created_at, ZoneInfo('Europe/Istanbul')).strftime('%d.%m.%Y %H:%M')
    return (f"🚨 ALARM ALARM ALARM — {'Sabah ihlal bildirimi' if morning else 'ANLIK PROGRAM İHLALİ'}\n"
            f"👤 {event.email}\n🕒 {when} (Türkiye)\n"
            f"📚 Katılmak istediği ders: {event.course_id_snapshot} — {event.course_title}\n"
            f"📋 Tamamlanmadığı doğrulanmış önceki dersler:\n{details}\n"
            f"⛔ Öğrenci ikinci uyarıyı onayladı; ana hesabı ilk ihlalde devre dışı bırakıldı.\n"
            f"İhlal kaydı #{event.pk}")


def deliver_instant(event_id):
    with transaction.atomic():
        event = ProgramProgressViolation.objects.select_for_update().get(pk=event_id)
        if event.instant_sent_at:
            return True
        if telegram(event_message(event)):
            event.instant_sent_at = timezone.now()
            event.save(update_fields=['instant_sent_at'])
            return True
    return False


def send_morning_violations(run_date):
    cutoff = datetime.combine(run_date, time.min, tzinfo=ZoneInfo('Europe/Istanbul'))
    ids = list(ProgramProgressViolation.objects.filter(created_at__lt=cutoff, morning_sent_at__isnull=True).values_list('pk', flat=True))
    sent = 0
    for pk in ids:
        deliver_instant(pk)  # Durable retry of a failed instant alert.
        with transaction.atomic():
            event = ProgramProgressViolation.objects.select_for_update().get(pk=pk)
            if not event.morning_sent_at and telegram(event_message(event, morning=True)):
                event.morning_sent_at = timezone.now()
                event.save(update_fields=['morning_sent_at'])
                sent += 1
    return sent


def entry_context(request):
    if request.path != '/dashboard-student/' and not request.path.startswith('/course-single/'):
        return {}
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}
    enrollments = list(warning_enrollments(request.user))
    seen = set(request.session.get('program_progress_ack', []))
    return {'progress_warning_programs': enrollments,
            'show_progress_entry_warning': any(e.pk not in seen for e in enrollments)}
