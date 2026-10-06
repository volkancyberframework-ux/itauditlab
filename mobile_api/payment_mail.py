"""Retryable payment receipts; first-login passwords are never stored as plaintext."""
import secrets
from django.conf import settings
from django.core.mail import send_mail, get_connection
from django.db import transaction
from django.utils import timezone
from .models import MobilePayment


def send_payment_receipt(pk):
    from django.contrib.auth import get_user_model
    try:
        with transaction.atomic():
            payment = MobilePayment.objects.select_for_update().get(pk=pk)
            if payment.receipt_sent_at:
                return True
            user = get_user_model().objects.select_for_update().get(pk=payment.user_id)
            first = user.mobile_must_change_password and not user.has_usable_password()
            if first:
                password = 'Grc-' + secrets.token_urlsafe(18) + '9!'
                message = f'Hesabınız oluşturuldu ve 1 aylık ücretli mobil erişiminiz açıldı.\n\nE-posta: {user.email}\nİlk giriş şifreniz: {password}\n\nBu e-posta ve ilk giriş şifrenizle mobil uygulamadan giriş yapın. İlk girişte yeni şifrenizi belirlemeniz istenecektir.'
            else:
                message = 'Ödemeniz alındı ve 1 aylık ücretli mobil erişiminiz açıldı.\n\nGRC Ustası hesabınızın mevcut şifresi geçerlidir. Aynı e-posta ve şifreyle mobil uygulamaya giriş yapabilirsiniz.'
            if not user.mobile_email_verified:
                from .email_verification import verification_url
                message += '\n\nGiriş yapmadan önce e-postanızı doğrulayın (24 saat geçerli):\n' + verification_url(user)
            message += f'\n\nÜcret: 2.099 TL\nErişim bitişi: {timezone.localtime(payment.access_until):%d.%m.%Y %H:%M}\nOtomatik yenileme yoktur.\n\nBir sorununuz olursa volkan@grcustasi.com adresine ulaşabilirsiniz.'
            if send_mail('GRC Ustası • Mobil üyeliğiniz aktif', message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False, connection=get_connection(timeout=10)) != 1:
                raise RuntimeError('Mail not accepted')
            if first:
                user.set_password(password)
                user.save(update_fields=['password'])
            payment.receipt_sent_at = timezone.now()
            payment.receipt_error = ''
            payment.save(update_fields=['receipt_sent_at', 'receipt_error'])
            return True
    except Exception:
        MobilePayment.objects.filter(pk=pk, receipt_sent_at=None).update(receipt_error='E-posta gönderilemedi; yönetim panelinden yeniden gönderin.')
        return False
