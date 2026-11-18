"""Notify only after a student's enrollment has actually committed."""
import logging
from functools import partial
import requests
from django.conf import settings
from django.db import transaction

logger = logging.getLogger('django.enrollment')


def schedule_notification(enrollment_id, user_id, course_id, using):
    transaction.on_commit(
        partial(send_committed_notification, enrollment_id, user_id, course_id, using),
        using=using,
    )


def send_committed_notification(enrollment_id, user_id, course_id, using):
    from .models import Enrollment
    try:
        enrollment = Enrollment.objects.using(using).select_related('user', 'course').filter(
            pk=enrollment_id, user_id=user_id, course_id=course_id, is_automatic=False, is_archived=False,
        ).first()
        if enrollment is None:
            return
        logger.info('enrollment_committed enrollment_id=%s user_id=%s course_id=%s database=%s',
                    enrollment_id, user_id, course_id, using)
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', '')
        if not token or not chat_id:
            return
        response = requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data={'chat_id': chat_id, 'text': (
                '🎓 Yeni Enrollment\n\n'
                f'👤 Kullanıcı:\n{enrollment.user.email}\n\n'
                f'📚 Kurs:\n{enrollment.course.turkish_name}\n\n'
                f'🆔 Course ID:\n{course_id}\n'
                f'🧾 Enrollment ID: {enrollment_id}\n'
                f'👤 User ID: {user_id}\n\n'
                '✅ Öğrencinin kaydı veritabanına kaydedildi.\n'
                f'https://www.grcustasi.com/bulamazsinki/core/customuser/{user_id}/change/'
            )}, timeout=5,
        )
        response.raise_for_status()
    except Exception:
        # A delivery failure must never undo a committed student enrollment.
        logger.exception('enrollment_notification_failed enrollment_id=%s user_id=%s course_id=%s',
                         enrollment_id, user_id, course_id)
