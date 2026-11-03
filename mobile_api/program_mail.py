"""Publication announcements and an explicitly invoked, repeat-safe catalogue campaign."""
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail, get_connection
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import LearningPath, ProgramEmailCampaign, ProgramEmailDelivery

logger = logging.getLogger(__name__)
CATALOGUE_KEY = 'mobile-catalogue-2026-11-03'


def public_paths():
    return LearningPath.objects.filter(published=True, owner=None, questions__published=True).filter(Q(preferences__web_only__isnull=True) | Q(preferences__web_only=False)).distinct()


def recipients():
    return get_user_model().objects.filter(is_active=True, is_mobile=True, mobile_email_verified=True).exclude(email='').filter(Q(mobile_last_date=None) | Q(mobile_last_date__gte=timezone.localdate())).order_by('pk')


def prepare_campaign(key, paths, path=None):
    titles = list(paths.values_list('title', flat=True))
    if not titles:
        return None
    with transaction.atomic():
        campaign, created = ProgramEmailCampaign.objects.get_or_create(key=key, defaults={'path': path, 'titles': titles})
        if created:
            rows = {}
            for user in recipients():
                email = user.email.strip().lower()
                if email:
                    rows.setdefault(email, ProgramEmailDelivery(campaign=campaign, email=email, name=user.first_name.strip()))
            ProgramEmailDelivery.objects.bulk_create(rows.values(), ignore_conflicts=True)
    return campaign


def deliver(pk):
    try:
        with transaction.atomic():
            row = ProgramEmailDelivery.objects.select_for_update().select_related('campaign').get(pk=pk)
            if row.sent_at:
                return False
            # Recheck account eligibility if delivery was delayed.
            if not recipients().filter(email__iexact=row.email).exists():
                row.last_error = 'Alıcı artık aktif ve doğrulanmış bir mobil kullanıcı değil.'
                row.save(update_fields=['last_error'])
                return False
            campaign = row.campaign
            if campaign.key.startswith('path-') and not public_paths().filter(pk=campaign.path_id).exists():
                return False
            new = campaign.key.startswith('path-')
            subject = 'GRC Ustası • Yeni öğrenme programın hazır' if new else 'GRC Ustası • Mobil uygulamadaki öğrenme programlarını keşfet'
            greeting = f'Merhaba {row.name},' if row.name else 'Merhaba,'
            intro = 'Mobil uygulamaya yeni bir öğrenme programı eklendi:' if new else 'GRC Ustası mobil uygulamasında seni bekleyen öğrenme programları:'
            body = greeting + '\n\n' + intro + '\n\n' + '\n'.join('• ' + title for title in campaign.titles)
            body += '\n\nGRC Ustası mobil uygulamasına giriş yap ve Öğrenme Yolları bölümünü aç. Programların erişimi üyeliğine göre değişebilir.\n\nSoruların için volkan@grcustasi.com adresine yazabilirsin.\n\nGRC Ustası'
            if send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [row.email], connection=get_connection(timeout=10)) != 1:
                raise RuntimeError('SMTP did not accept message')
            row.sent_at = timezone.now()
            row.last_error = ''
            row.save(update_fields=['sent_at', 'last_error'])
            return True
    except Exception as exc:
        ProgramEmailDelivery.objects.filter(pk=pk, sent_at=None).update(last_error=type(exc).__name__)
        logger.warning('Mobile program email delivery failed: %s', pk)
        return False


def drain(campaign=None, limit=None):
    qs = ProgramEmailDelivery.objects.filter(sent_at=None)
    if campaign is not None:
        qs = qs.filter(campaign=campaign)
    ids = list(qs.order_by('pk').values_list('pk', flat=True)[:limit])
    return sum(deliver(pk) for pk in ids)


def announce_available():
    for path in public_paths():
        if ProgramEmailCampaign.objects.filter(key=f'path-{path.pk}').exists():
            continue
        campaign = prepare_campaign(f'path-{path.pk}', public_paths().filter(pk=path.pk), path)
        if campaign:
            drain(campaign, limit=5)
