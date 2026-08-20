from datetime import timedelta

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
import requests

from .models import DailyTrafficMetric, DailyTrafficReport, LandingVisit


def traffic_stats(day):
    visits = LandingVisit.objects.filter(visit_date=day)
    metric = DailyTrafficMetric.objects.filter(date=day).first()
    return {
        'date': day,
        'unique_visitors': visits.count(),
        'new_visitors': visits.filter(is_returning=False).count(),
        'returning_visitors': visits.filter(is_returning=True).count(),
        'page_views': metric.page_views if metric else 0,
        'filtered_bots': metric.filtered_bot_requests if metric else 0,
    }


def period_unique_visitors(start_date, end_date):
    return LandingVisit.objects.filter(
        visit_date__range=(start_date, end_date),
    ).values('visitor_hash').distinct().count()


def period_page_views(start_date, end_date):
    return DailyTrafficMetric.objects.filter(
        date__range=(start_date, end_date),
    ).aggregate(total=Sum('page_views'))['total'] or 0


def send_daily_traffic_report(report_date=None):
    report_date = report_date or timezone.localdate() - timedelta(days=1)
    if DailyTrafficReport.objects.filter(report_date=report_date).exists():
        return False
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        raise RuntimeError('Telegram trafik raporu için TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID gerekli.')

    stats = traffic_stats(report_date)
    message = (
        '📊 GRC Ustası günlük trafik raporu\n'
        f'📅 {report_date:%d.%m.%Y}\n'
        f'👤 Tekil ziyaretçi: {stats["unique_visitors"]}\n'
        f'🆕 İlk kez görülen: {stats["new_visitors"]}\n'
        f'🔁 Geri dönen: {stats["returning_visitors"]}\n'
        f'👁 Sayfa görüntüleme: {stats["page_views"]}\n'
        f'🤖 Filtrelenen bot isteği: {stats["filtered_bots"]}'
    )
    response = requests.post(
        f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage',
        data={'chat_id': settings.TELEGRAM_CHAT_ID, 'text': message},
        timeout=10,
    )
    response.raise_for_status()
    DailyTrafficReport.objects.create(report_date=report_date)
    return True
