from zoneinfo import ZoneInfo

from django.utils import timezone

from core.models import WeeklyTelegramSchedule
from skool.services import send_telegram


WEEKDAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')


def send_weekly_telegram_note(report_date=None):
    report_date = report_date or timezone.now().astimezone(ZoneInfo('Europe/Istanbul')).date()
    schedule = WeeklyTelegramSchedule.objects.filter(pk=1).first()
    if schedule is None:
        return False
    field = WEEKDAYS[report_date.weekday()]
    note = getattr(schedule, field).strip()
    if not note:
        return False
    day = schedule._meta.get_field(field).verbose_name
    return send_telegram(
        f'📅 {day} — {report_date:%d.%m.%Y}\n\n{note}',
        idempotency_key=f'weekly-note:{report_date.isoformat()}',
    )
