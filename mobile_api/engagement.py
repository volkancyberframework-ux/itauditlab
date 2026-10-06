from datetime import timedelta, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .views import MobileView
from .models import QuestionAttempt, MobileSettings, MotivationMessage


def device_zone(request):
    try:
        return ZoneInfo(request.query_params.get('timezone', 'Europe/Istanbul'))
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise ValidationError('Saat dilimi geçersiz.')


class Activity(MobileView):
    def get(self, request):
        zone = device_zone(request)
        today = timezone.now().astimezone(zone).date()
        start = today - timedelta(days=27)
        records = QuestionAttempt.objects.filter(session__user=request.user, created_at__gte=datetime.combine(start, time.min, tzinfo=zone), created_at__lt=datetime.combine(today + timedelta(days=1), time.min, tzinfo=zone)).annotate(day=TruncDate('created_at', tzinfo=zone)).values('day').annotate(tasks=Count('pk'), xp=Sum('xp_change'))
        lookup = {row['day']: row for row in records}
        days = [{'date': str(start + timedelta(days=i)), 'tasks': lookup.get(start + timedelta(days=i), {}).get('tasks', 0), 'xp': lookup.get(start + timedelta(days=i), {}).get('xp', 0)} for i in range(28)]
        active = set(QuestionAttempt.objects.filter(session__user=request.user).annotate(day=TruncDate('created_at', tzinfo=zone)).values_list('day', flat=True).distinct())
        cursor = today if today in active else today - timedelta(days=1)
        streak = 0
        while cursor in active:
            streak += 1
            cursor -= timedelta(days=1)
        return Response({'days': days, 'active_days': sum(day['tasks'] > 0 for day in days), 'streak': streak, 'today_tasks': days[-1]['tasks']})


class NotificationPlan(MobileView):
    def get(self, request):
        zone = device_zone(request)
        today = timezone.now().astimezone(zone).date()
        config = MobileSettings.objects.filter(pk=1).first()
        if config and not config.notifications_enabled:
            return Response({'enabled': False, 'days': []})
        messages = list(MotivationMessage.objects.filter(published=True, day=None))
        special = {message.day: message for message in MotivationMessage.objects.filter(published=True, day__gte=today, day__lte=today + timedelta(days=59))}
        days = []
        for i in range(60):
            day = today + timedelta(days=i)
            message = special.get(day) or (messages[day.toordinal() % len(messages)] if messages else None)
            if message:
                days.append({'date': str(day), 'title': message.title, 'body': message.body})
        return Response({'enabled': True, 'hour': config.notification_hour if config else 19, 'days': days})
