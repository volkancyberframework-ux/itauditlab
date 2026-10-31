"""Durable per-page Telegram delivery for the 09:00 account inactivity check."""
from zoneinfo import ZoneInfo
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import AccountInactivityRun


def local_date(value):
    timestamp = parse_datetime(value) if value else None
    if timestamp is None:
        return 'kayıt yok'
    return timestamp.astimezone(ZoneInfo('Europe/Istanbul')).strftime('%d.%m.%Y %H:%M')


def report_parts(run):
    rows = run.disabled_accounts
    if not rows and run.disabled_user_ids:
        # Compatibility with a check completed before this reporting feature.
        users = {u.pk:u for u in get_user_model().objects.filter(pk__in=run.disabled_user_ids)}
        rows = []
        for pk in run.disabled_user_ids:
            u = users.get(pk)
            latest = max(v for v in (u.last_account_access_at, u.last_login, u.date_joined) if v) if u else None
            rows.append({'email':u.email if u else f'Silinmiş hesap #{pk}',
                         'last_access_at': latest.isoformat() if latest and latest <= run.completed_at else None,
                         'legacy':True})
    blocks = []
    for row in rows:
        email = row['email'].replace('\r',' ').replace('\n',' ')
        if row.get('last_access_at'):
            detail = 'Son erişim: ' + local_date(row['last_access_at']) + ' (Türkiye)'
        elif row.get('legacy'):
            detail = 'Kontrol anındaki son erişim tarihi kaydedilmemiş.'
        else:
            detail = 'Son erişim: giriş kaydı yok\nHesap açılışı: ' + local_date(row.get('account_created_at')) + ' (Türkiye)'
        blocks.append(f'• {email}\n{detail}')
    if not blocks:
        blocks = ['✅ Bugün hareketsizlik nedeniyle pasife alınan hesap yok.']
    pages, current = [], ''
    for block in blocks:
        if current and len(current) + len(block) + 2 > 3200:
            pages.append(current); current = ''
        current += ('\n\n' if current else '') + block
    if current:
        pages.append(current)
    header = (f'⏰ GRC Ustası · 09.00 hesap kontrolü\n📅 {run.reporting_date:%d.%m.%Y} (Türkiye)\n'
              f'⛔ Pasife alınan hesap: {len(run.disabled_user_ids)}\n')
    return [header + (f'Bölüm {i}/{len(pages)}\n' if len(pages)>1 else '') + '\n' + body
            for i, body in enumerate(pages,1)]


def send_report(run_id):
    token = getattr(settings,'GRCUSTASI_TELEGRAM_BOT_TOKEN','') or settings.TELEGRAM_BOT_TOKEN
    chat_id = getattr(settings,'GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID','') or settings.TELEGRAM_CHAT_ID
    while True:
        # Commit each acknowledged page separately so a failed later page resumes
        # without resending the earlier pages. HTTP timeouts can still be ambiguous.
        with transaction.atomic():
            run = AccountInactivityRun.objects.select_for_update().get(pk=run_id)
            if run.telegram_sent_at:
                return True
            if not run.completed_at:
                return False
            parts = report_parts(run)
            if not token or not chat_id:
                run.telegram_error = 'Telegram ayarları eksik'
                run.save(update_fields=['telegram_error'])
                return False
            if run.telegram_parts_sent >= len(parts):
                run.telegram_sent_at = timezone.now(); run.telegram_error = ''
                run.save(update_fields=['telegram_sent_at','telegram_error'])
                return True
            try:
                response = requests.post(f'https://api.telegram.org/bot{token}/sendMessage',
                    data={'chat_id':chat_id, 'text':parts[run.telegram_parts_sent], 'disable_web_page_preview':True},timeout=10)
                response.raise_for_status()
                if response.json().get('ok') is not True:
                    raise ValueError('Telegram did not acknowledge delivery')
            except (requests.RequestException,ValueError) as exc:
                run.telegram_error = type(exc).__name__
                run.save(update_fields=['telegram_error'])
                return False
            run.telegram_parts_sent += 1
            run.telegram_error = ''
            if run.telegram_parts_sent == len(parts):
                run.telegram_sent_at = timezone.now()
            run.save(update_fields=['telegram_parts_sent','telegram_error','telegram_sent_at'])
            if run.telegram_sent_at:
                return True


def send_pending_reports():
    ids = list(AccountInactivityRun.objects.filter(completed_at__isnull=False,telegram_sent_at__isnull=True)
               .order_by('reporting_date').values_list('pk',flat=True))
    success = True
    for pk in ids:
        if not send_report(pk):
            success = False
    return success
