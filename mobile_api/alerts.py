import logging
from django.db import transaction
from django.utils import timezone
from .models import MobileAdminAlert

logger = logging.getLogger(__name__)


def queue_alert(key, text):
    alert, _ = MobileAdminAlert.objects.get_or_create(key=key, defaults={'text': text})
    transaction.on_commit(lambda: deliver_alert(alert.pk))


def deliver_alert(pk):
    from skool.services import send_telegram
    from skool.models import NotificationLog
    with transaction.atomic():
        alert = MobileAdminAlert.objects.select_for_update().get(pk=pk)
        if alert.sent_at:
            return True
        try:
            sent = send_telegram(alert.text, idempotency_key='mobile-alert-' + alert.key)
            sent = sent or NotificationLog.objects.filter(key='mobile-alert-' + alert.key, detail__status='sent').exists()
            if not sent:
                alert.last_error = 'Telegram yapılandırmasını kontrol edin; bildirim bekliyor.'
            else:
                alert.sent_at = timezone.now()
                alert.last_error = ''
        except Exception:
            alert.last_error = 'Telegram bağlantısı başarısız; yeniden gönderilebilir.'
            logger.warning('Mobile Telegram alert pending: %s', pk)
        alert.save(update_fields=['sent_at', 'last_error'])
        return bool(alert.sent_at)
