from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from .views import MobileView
from .models import (AccountDeletionRequest, LearningSession, VoiceSubmission, UserPathProgress,
                     XPTransaction, Subscription, AnalyticsEvent, BillingIdentity, UserLevelReward,
                     MobileCheckoutRequest, MobileAdminAlert, LearningPath)


class RequestDeletion(MobileView):
    allow_initial_password = True

    def post(self, request):
        password = request.data.get('password')
        if request.user.is_staff or request.user.is_superuser:
            raise PermissionDenied('Yönetici hesabını silmek için yönetim panelini kullanın.')
        if not isinstance(password, str) or len(password) > 256 or not request.user.check_password(password):
            raise ValidationError('Hesap silme talebi için mevcut şifreni doğrula.')
        if request.data.get('confirm') is not True:
            raise ValidationError('Hesap silme talebini onaylamalısın.')
        record, _ = AccountDeletionRequest.objects.get_or_create(user=request.user, defaults={'email_to_notify': request.user.email})
        return Response({'detail': 'Hesap silme talebin alındı. Mobil verilerin ve ortak GRC Ustası giriş hesabın en geç 7 gün içinde silinecek. Tamamlanana kadar hesabını kullanabilirsin.', 'requested_at': record.requested_at}, status=202)


def complete_deletion(pk):
    from .storage import PrivateVoiceStorage
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
    from skool.models import NotificationLog
    import secrets
    with transaction.atomic():
        record = AccountDeletionRequest.objects.select_for_update().get(pk=pk)
        user = get_user_model().objects.select_for_update().get(pk=record.user_id)
        if user.is_staff or user.is_superuser:
            raise ValueError('Administrator account cannot be erased here')
        if not record.erased_at:
            voices = VoiceSubmission.objects.filter(attempt__session__user=user)
            record.pending_files = list(voices.values_list('file', flat=True))
            keys = [f'signup-{user.pk}'] + [f'voice-{value}' for value in voices.values_list('pk', flat=True)]
            MobileAdminAlert.objects.filter(key__in=keys).delete()
            NotificationLog.objects.filter(key__in=['mobile-alert-' + value for value in keys]).delete()
            XPTransaction.objects.filter(user=user).delete()
            LearningSession.objects.filter(user=user).delete()
            for model in [UserPathProgress, XPTransaction, Subscription, AnalyticsEvent, BillingIdentity, UserLevelReward, MobileCheckoutRequest]:
                model.objects.filter(user=user).delete()
            LearningPath.objects.filter(owner=user).delete()
            for token in OutstandingToken.objects.filter(user=user, expires_at__gt=timezone.now()):
                BlacklistedToken.objects.get_or_create(token=token)
            # Retain a non-loginable anonymous identifier for mandatory payment audit records.
            user.username = f'deleted_mobile_{user.pk}_{secrets.token_hex(8)}'
            user.email = user.first_name = user.last_name = ''
            user.is_active = user.is_mobile = user.mobile_full_access = user.mobile_must_change_password = user.mobile_email_verified = False
            user.mobile_paid_until = user.mobile_last_date = None
            user.set_unusable_password()
            user.save()
            user.allowed_tests.clear()
            user.groups.clear()
            user.user_permissions.clear()
            record.erased_at = timezone.now()
            record.save(update_fields=['erased_at', 'pending_files'])
    remaining = []
    for name in record.pending_files:
        try:
            PrivateVoiceStorage().delete(name)
        except Exception:
            remaining.append(name)
    with transaction.atomic():
        record = AccountDeletionRequest.objects.select_for_update().get(pk=pk)
        record.pending_files = remaining
        if not remaining:
            record.completed_at = timezone.now()
        record.save(update_fields=['pending_files', 'completed_at'])
    if remaining:
        return False
    return send_deletion_confirmation(pk)


def send_deletion_confirmation(pk):
    from django.core.mail import send_mail, get_connection
    from django.conf import settings
    try:
        with transaction.atomic():
            record = AccountDeletionRequest.objects.select_for_update().get(pk=pk)
            if record.confirmation_sent_at:
                return True
            if send_mail('GRC Ustası • Hesabın silindi', 'Hesabın ve mobil öğrenme verilerin silindi. Ortak GRC Ustası giriş hesabın artık kullanılamaz. Yasal olarak saklanması gereken mali kayıtlar hariçtir.\n\nDestek: volkan@grcustasi.com', settings.DEFAULT_FROM_EMAIL, [record.email_to_notify], connection=get_connection(timeout=10)) != 1:
                return False
            record.email_to_notify = ''
            record.confirmation_sent_at = timezone.now()
            record.save(update_fields=['email_to_notify', 'confirmation_sent_at'])
            return True
    except Exception:
        return False
