"""Closed-day mobile/web learning KPIs for the existing owner's morning report."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db.models import Count, F, IntegerField, Q, Sum, Value
from django.db.models.functions import Least
from django.utils import timezone

from .models import AnalyticsEvent, LearningSession, MobileDailyKPI, QuestionAttempt, Subscription, VoiceSubmission

ZONE = ZoneInfo('Europe/Istanbul')
AUTO_GRADED = ('choice', 'multi_select', 'fill_blank', 'image', 'audio', 'scenario', 'sentence_order', 'drag_select')
SECONDS = Least(F('duration_seconds'), Value(600), output_field=IntegerField())


def students():
    return get_user_model().objects.filter(is_mobile=True, is_staff=False, is_superuser=False)


def bounds(day):
    start = datetime.combine(day, time.min, tzinfo=ZONE)
    return start, start + timedelta(days=1)


def active_ids(start, end, user_ids):
    """Only actual records, never assigned paths / auto_now progress timestamps."""
    ids = set(AnalyticsEvent.objects.filter(user_id__in=user_ids, created_at__gte=start, created_at__lt=end).values_list('user_id', flat=True).distinct())
    sessions = LearningSession.objects.filter(user_id__in=user_ids)
    ids.update(sessions.filter(created_at__gte=start, created_at__lt=end).values_list('user_id', flat=True).distinct())
    ids.update(sessions.filter(completed_at__gte=start, completed_at__lt=end).values_list('user_id', flat=True).distinct())
    attempts = QuestionAttempt.objects.filter(session__user_id__in=user_ids)
    ids.update(attempts.filter(created_at__gte=start, created_at__lt=end).values_list('session__user_id', flat=True).distinct())
    ids.update(VoiceSubmission.objects.filter(attempt__session__user_id__in=user_ids, created_at__gte=start, created_at__lt=end).values_list('attempt__session__user_id', flat=True).distinct())
    return ids


def daily_metrics(day, user_ids):
    start, end = bounds(day)
    all_attempts = QuestionAttempt.objects.filter(session__user_id__in=user_ids, created_at__gte=start, created_at__lt=end)
    answers = all_attempts.exclude(question__kind='info')
    graded = Q(question__kind__in=AUTO_GRADED)
    sums = answers.aggregate(answers=Count('pk'), graded=Count('pk', filter=graded),
                             correct=Count('pk', filter=graded & Q(is_correct=True)), seconds=Sum(SECONDS))
    return {
        'date': day.isoformat(),
        'new_accounts': students().filter(pk__in=user_ids, date_joined__gte=start, date_joined__lt=end).count(),
        'active': len(active_ids(start, end, user_ids)),
        'learners': answers.values('session__user_id').distinct().count(),
        'answers': sums['answers'],
        'correct': sums['correct'], 'graded': sums['graded'],
        'accuracy': round(sums['correct'] / sums['graded'] * 100, 1) if sums['graded'] else None,
        'seconds': sums['seconds'] or 0,
        'cards': all_attempts.filter(question__kind='info').count(),
        'voices': VoiceSubmission.objects.filter(attempt__session__user_id__in=user_ids, created_at__gte=start, created_at__lt=end).count(),
        'sessions_completed': LearningSession.objects.filter(user_id__in=user_ids, completed_at__gte=start, completed_at__lt=end).count(),
        'net_xp': all_attempts.aggregate(total=Sum('xp_change'))['total'] or 0,
    }


def build_payload(report_date, now=None):
    now = now or timezone.now()
    day = report_date - timedelta(days=1)
    previous_day = day - timedelta(days=1)
    users = students().filter(date_joined__lte=now)
    user_ids = users.values('pk')
    start, end = bounds(day)
    enabled = users.filter(is_active=True)
    subscribed = Subscription.objects.filter(status__in=['active', 'trial', 'grace_period'], expires_at__gt=now).values('user_id')
    full = enabled.filter(Q(mobile_last_date=None) | Q(mobile_last_date__gte=report_date)).filter(
        Q(mobile_full_access=True) | Q(mobile_paid_until__gt=now) | Q(pk__in=subscribed)).count()
    previous_snapshot = MobileDailyKPI.objects.filter(report_date=report_date-timedelta(days=1)).first()
    previous = (previous_snapshot.payload.get('current') if previous_snapshot else None)
    if not previous or previous.get('date') != previous_day.isoformat():
        previous = daily_metrics(previous_day, user_ids)
    current = daily_metrics(day, user_ids)
    previous_total = previous_snapshot.payload['accounts']['total'] if previous_snapshot else None
    today_active = active_ids(start, end, user_ids)
    prior_start, _ = bounds(previous_day)
    prior_active = (set(previous_snapshot.payload['active_user_ids'])
                    if previous_snapshot and 'active_user_ids' in previous_snapshot.payload
                    else active_ids(prior_start, start, user_ids))
    week_start, _ = bounds(day - timedelta(days=6))
    weekly_active = active_ids(week_start, end, user_ids)
    old_enabled = set(enabled.filter(date_joined__lt=week_start).values_list('pk', flat=True))
    answers = QuestionAttempt.objects.filter(session__user_id__in=user_ids, created_at__gte=start, created_at__lt=end).exclude(question__kind='info')
    graded = Q(question__kind__in=AUTO_GRADED)
    leaders = list(answers.values('session__user_id').annotate(
        unique_questions=Count('question_id', distinct=True), answers=Count('pk'),
        graded=Count('pk', filter=graded), correct=Count('pk', filter=graded & Q(is_correct=True)),
        seconds=Sum(SECONDS), net_xp=Sum('xp_change'), sessions=Count('session_id', distinct=True),
    ).order_by('-unique_questions', '-answers', 'session__user_id')[:5])
    for row in leaders:
        row['user_id'] = row.pop('session__user_id')
        row['accuracy'] = round(row['correct'] / row['graded'] * 100, 1) if row['graded'] else None
    popular = list(answers.values('session__path_id', 'session__path__title').annotate(
        students=Count('session__user_id', distinct=True), answers=Count('pk'),
    ).order_by('-students', '-answers', 'session__path_id')[:3])
    for row in popular:
        row['path_id'] = row.pop('session__path_id'); row['title'] = row.pop('session__path__title')
    return {
        'report_date': report_date.isoformat(), 'captured_at': now.astimezone(ZONE).isoformat(),
        'accounts': {'total': users.count(), 'enabled': enabled.count(), 'disabled': users.filter(is_active=False).count(),
                     'full_access': full, 'standard_access': enabled.filter(Q(mobile_last_date=None) | Q(mobile_last_date__gte=report_date)).count()-full,
                     'expired_access': enabled.filter(mobile_last_date__lt=report_date).count(),
                     'verification_pending': enabled.filter(mobile_email_verified=False).count(),
                     'previous_total': previous_total},
        'current': current, 'previous': previous,
        'active_user_ids': sorted(today_active),
        'weekly_active': len(weekly_active), 'quiet_7d': len(old_enabled-weekly_active),
        'returned': len(today_active & prior_active), 'return_base': len(prior_active),
        'newly_active': len(today_active-prior_active), 'lost_active': len(prior_active-today_active),
        'leaders': leaders, 'popular_paths': popular,
    }


def capture_report(report_date=None):
    report_date = report_date or timezone.now().astimezone(ZONE).date()
    existing = MobileDailyKPI.objects.filter(report_date=report_date).first()
    if existing:
        return existing, False
    payload = build_payload(report_date)
    return MobileDailyKPI.objects.get_or_create(report_date=report_date, defaults={'payload': payload})


def delta(current, previous):
    if previous is None:
        return 'ilk ölçüm'
    difference = round(current-previous, 1)
    return f'↑{number(difference)}' if difference > 0 else f'↓{number(abs(difference))}' if difference < 0 else '→0'


def number(value):
    return str(int(value)) if float(value).is_integer() else f'{value:.1f}'.replace('.', ',')


def rate(value):
    return f'%{number(value)}' if value is not None else '—'


def format_report(payload):
    current, previous, accounts = payload['current'], payload['previous'], payload['accounts']
    day = datetime.fromisoformat(current['date']).strftime('%d.%m.%Y')
    prior = datetime.fromisoformat(previous['date']).strftime('%d.%m.%Y')
    captured = datetime.fromisoformat(payload['captured_at']).strftime('%d.%m.%Y %H:%M')
    accuracy_delta = (f"{delta(current['accuracy'], previous['accuracy'])} puan"
                      if current['accuracy'] is not None and previous['accuracy'] is not None else 'karşılaştırma yok')
    lines = [
        '📱 GRC USTASI MOBİL — GÜNLÜK KPI',
        f'🕒 Hesap sayımı: {captured} • İstanbul',
        f"👥 Kayıtlı mobil öğrenci: {accounts['total']} ({delta(accounts['total'], accounts['previous_total'])}; önceki rapora göre)",
        f"✅ Açık hesap: {accounts['enabled']} | Kapalı: {accounts['disabled']}",
        f"💎 Tam erişim hakkı: {accounts['full_access']} | Standart: {accounts['standard_access']}",
        f"⏳ Erişim süresi dolmuş: {accounts['expired_access']} | 📧 Doğrulama bekleyen: {accounts['verification_pending']}",
        f'📅 Aktivite: {day} ↔ {prior} • 00:00–24:00 İstanbul',
        f"📱 Aktif öğrenci: {current['active']} ({delta(current['active'], previous['active'])})",
        f"🆕 Yeni hesap: {current['new_accounts']} ({delta(current['new_accounts'], previous['new_accounts'])})",
        f"✍️ Soru çözen öğrenci: {current['learners']} ({delta(current['learners'], previous['learners'])})",
        f"📝 Soru yanıtı: {current['answers']} ({delta(current['answers'], previous['answers'])}; tekrarlar dahil",
        f"🎯 Otomatik değerlendirmede doğruluk: {rate(current['accuracy'])} ({accuracy_delta})",
        f"⏱️ Tahmini soru süresi: {number(round(current['seconds']/60, 1))} dk ({delta(round(current['seconds']/60, 1), round(previous['seconds']/60, 1))} dk)",
        f"🏁 Tamamlanan çalışma oturumu: {current['sessions_completed']} ({delta(current['sessions_completed'], previous['sessions_completed'])})",
        f"📖 Bilgi kartı: {current['cards']} ({delta(current['cards'], previous['cards'])}) | 🎙️ Sesli yanıt: {current['voices']} ({delta(current['voices'], previous['voices'])})",
        f"✨ Net XP: {current['net_xp']} ({delta(current['net_xp'], previous['net_xp'])})",
        f"📆 Son 7 günde aktif: {payload['weekly_active']} | 7 gündür etkinliksiz eski hesap: {payload['quiet_7d']}",
        ('↩️ Önceki gün aktif olup dönen: '+f"{payload['returned']}/{payload['return_base']} ({rate(round(payload['returned']/payload['return_base']*100,1))})"
         if payload['return_base'] else '↩️ Geri dönüş: önceki gün kayıtlı aktivite yok'),
        f"🔄 Önceki güne göre yeni aktif: {payload['newly_active']} | Etkinliği kesilen: {payload['lost_active']}",
        '', '🏆 En aktif 5 öğrenci — farklı soru sayısına göre',
    ]
    names = {u.pk: u.get_full_name().strip() for u in get_user_model().objects.filter(pk__in=[r['user_id'] for r in payload['leaders']])}
    if not payload['leaders']:
        lines.append('Rapor gününde kayıtlı soru yanıtı yok.')
    for i, row in enumerate(payload['leaders'], 1):
        name = ' '.join(names.get(row['user_id'], '').split())
        name = name[:50] if name and '@' not in name else 'Öğrenci'
        lines.append(f"{i}. {name} (#{row['user_id']}): {row['unique_questions']} farklı soru / {row['answers']} yanıt • {rate(row['accuracy'])} doğru • {number(round(row['seconds']/60, 1))} dk • {row['sessions']} oturum • {row['net_xp']} XP")
    if payload['popular_paths']:
        lines.extend(['', '📚 En çok çalışılan yollar'])
        for row in payload['popular_paths']:
            title = ' '.join(row['title'].split())[:90]
            lines.append(f"• {title}: {row['students']} öğrenci, {row['answers']} yanıt")
    lines.append('Not: Mobil + web kayıtları; yönetici hesapları hariç. Süre tahminidir (en fazla 10 dk/soru); sesli/serbest metin doğruluk oranına dahil değil. Aktif = kayıtlı etkinliği olan.')
    return '\n'.join(lines)
