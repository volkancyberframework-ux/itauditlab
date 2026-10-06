from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from .models import VoiceSubmission


def send_voice_feedback(submission_id):
    """Send a reviewed recording's feedback once; failures remain retryable."""
    with transaction.atomic():
        submission = VoiceSubmission.objects.select_for_update().select_related('attempt__session__user', 'attempt__question').get(pk=submission_id)
        if submission.feedback_sent_at:
            return False
        if submission.review_status != 'reviewed' or not submission.feedback.strip():
            raise ValueError('Önce geri bildirimi yazıp kaydı incelendi olarak işaretleyin.')
        user = submission.attempt.session.user
        count = send_mail(
            'GRC Ustası • Sesli yanıtına geri bildirim',
            f'Merhaba {user.first_name or user.username},\n\n'
            f'Görev: {submission.attempt.question.prompt}\n\n'
            f'Geri bildirimin:\n{submission.feedback.strip()}\n\nGRC Ustası',
            settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False,
        )
        if count != 1:
            raise ValueError('E-posta gönderilemedi; tekrar deneyin.')
        submission.feedback_sent_at = timezone.now()
        submission.save(update_fields=['feedback_sent_at'])
        return True
