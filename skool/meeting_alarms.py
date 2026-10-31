"""Date-scoped signed handoff from Telegram to the owner's iPhone shortcut."""
from datetime import date, datetime, time, timedelta
from urllib.parse import urlencode, quote
from zoneinfo import ZoneInfo
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_safe, require_http_methods
from core.models import StudentMeetingBooking
from .models import MeetingBooking

ZONE = ZoneInfo('Europe/Istanbul')
SALT = 'skool.daily-meeting-alarms.v1'
SHORTCUT_NAME = 'GRC Görüşme Alarmları'
PREFIX = 'GRC-GORUSME-v1-'


def day_bookings(report_date):
    start = datetime.combine(report_date,time.min,tzinfo=ZONE)
    end = start+timedelta(days=1)
    filters = dict(status='active',slot__start_at_utc__gte=start,slot__start_at_utc__lt=end)
    return (
        list(MeetingBooking.objects.filter(**filters).select_related('user','slot').order_by('slot__start_at_utc')),
        list(StudentMeetingBooking.objects.filter(**filters).select_related('user','request__course','slot').order_by('slot__start_at_utc')),
    )


def meeting_alarm_link(report_date):
    token = signing.dumps({'date':report_date.isoformat(),'purpose':'daily-meeting-alarms','version':1},salt=SALT,compress=True)
    return getattr(settings,'PUBLIC_BASE_URL','https://www.grcustasi.com').rstrip('/')+reverse('skool:meeting_alarms',args=[token])


def validate_token(token):
    try:
        payload = signing.loads(token,salt=SALT,max_age=36*60*60)
        if not isinstance(payload,dict):
            raise ValueError
        if payload.get('purpose')!='daily-meeting-alarms' or payload.get('version')!=1:
            raise ValueError
        report_date = date.fromisoformat(payload['date'])
    except (signing.BadSignature, ValueError, KeyError, TypeError):
        raise Http404('Bağlantı geçersiz veya süresi dolmuş.')
    if report_date != timezone.now().astimezone(ZONE).date():
        return None
    return report_date


def alarm_payload(report_date, *, now=None):
    now = now or timezone.now()
    skool, students = day_bookings(report_date)
    alarms = []
    for source, rows in (('S',skool),('N',students)):
        for booking in rows:
            alarm_at = booking.slot.start_at_utc-timedelta(minutes=5)
            if alarm_at<=now:
                continue  # Clock would otherwise interpret a past time as tomorrow.
            name = booking.user.full_name if source=='S' else (booking.user.get_full_name() or booking.user.username)
            name = ' '.join(name.split())[:80]
            key = f'{source}{booking.pk}'
            label = f'{PREFIX}{report_date:%Y%m%d}-{key}-{int(alarm_at.timestamp())} · {name}'
            alarms.append(dict(id=key,name=name,source='Skool' if source=='S' else 'Normal öğrenci',label=label,
                alarm_at=alarm_at.isoformat(),meeting_at=booking.slot.start_at_utc.isoformat(),
                display_alarm=alarm_at.astimezone(ZONE).strftime('%H:%M'),
                display_meeting=booking.slot.start_at_utc.astimezone(ZONE).strftime('%H:%M')))
    alarms.sort(key=lambda row:(row['alarm_at'],row['id']))
    return dict(version=1,date=report_date.isoformat(),timezone='Europe/Istanbul',prefix=PREFIX,alarms=alarms)


def private(response):
    response['Cache-Control']='private, no-store, max-age=0'
    response['Referrer-Policy']='no-referrer'
    response['X-Robots-Tag']='noindex, nofollow, noarchive'
    response['X-Content-Type-Options']='nosniff'
    response['Content-Security-Policy']="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
    return response


@require_safe
def meeting_alarms(request, token):
    report_date=validate_token(token)
    if report_date is None:
        return private(render(request,'skool/meeting_alarms.html',{'expired':True},status=410))
    payload=alarm_payload(report_date)
    data_url=getattr(settings,'PUBLIC_BASE_URL','https://www.grcustasi.com').rstrip('/')+reverse('skool:meeting_alarms_data',args=[token])
    shortcut_url='shortcuts://run-shortcut?'+urlencode({'name':SHORTCUT_NAME,'input':'text','text':data_url},quote_via=quote)
    return private(render(request,'skool/meeting_alarms.html',dict(payload=payload,shortcut_name=SHORTCUT_NAME,shortcut_url=shortcut_url)))


@require_safe
def meeting_alarms_data(request, token):
    report_date=validate_token(token)
    if report_date is None:
        return private(JsonResponse({'error':'Bu bağlantı yalnızca mesajdaki gün için geçerlidir.'},status=410))
    return private(JsonResponse(alarm_payload(report_date),json_dumps_params={'ensure_ascii':False}))


@require_safe
def setup(request):
    response=render(request,'skool/meeting_alarms_setup.html',{'shortcut_name':SHORTCUT_NAME,'prefix':PREFIX,'input_prefix':getattr(settings,'PUBLIC_BASE_URL','https://www.grcustasi.com').rstrip('/')+'/gorusme-alarmlari/'})
    response['Referrer-Policy']='no-referrer'
    return response


@require_safe
def today(request):
    from django.core.exceptions import PermissionDenied
    from django.shortcuts import redirect
    if not request.user.is_authenticated:
        return redirect('/login/?next='+quote(request.path,safe=''))
    if not request.user.is_superuser or request.user.email.strip().casefold() not in {'guler.volkan@yahoo.com','volkancyberframework@gmail.com'}:
        raise PermissionDenied
    return private(redirect(meeting_alarm_link(timezone.now().astimezone(ZONE).date())))


def is_owner(user):
    return user.is_authenticated and user.is_active and user.is_superuser and user.email.strip().casefold() in {'guler.volkan@yahoo.com','volkancyberframework@gmail.com'}


@require_http_methods(['GET','POST'])
def automatic_setup(request):
    from django.core.exceptions import PermissionDenied
    from django.shortcuts import redirect
    from django.db import transaction
    from .models import MeetingAlarmDevice
    import hashlib, secrets
    if not request.user.is_authenticated:
        return redirect('/login/?next='+quote(request.path,safe=''))
    if not is_owner(request.user):
        raise PermissionDenied
    context = {'active_count': MeetingAlarmDevice.objects.filter(owner=request.user,revoked_at__isnull=True,expires_at__gt=timezone.now()).count()}
    if request.method == 'POST':
        action = request.POST.get('action')
        if action not in {'create','revoke'}:
            return private(JsonResponse({'error':'Geçersiz işlem.'},status=400))
        now = timezone.now()
        with transaction.atomic():
            # Serialize provisioning for one owner; replacement invalidates old URLs.
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            MeetingAlarmDevice.objects.filter(owner=request.user,revoked_at__isnull=True).update(revoked_at=now)
            if action == 'create':
                raw = secrets.token_urlsafe(32)
                expires = now+timedelta(days=365)
                MeetingAlarmDevice.objects.create(owner=request.user,token_hash=hashlib.sha256(raw.encode()).hexdigest(),expires_at=expires)
                context['feed_url'] = getattr(settings,'PUBLIC_BASE_URL','https://www.grcustasi.com').rstrip('/')+reverse('skool:meeting_alarms_automatic_data',args=[raw])
                context['expires'] = expires
                context['active_count'] = 1
            else:
                context.update(revoked=True,active_count=0)
    return private(render(request,'skool/meeting_alarms_automatic.html',context))


@require_safe
def automatic_data(request, token):
    import hashlib
    from .models import MeetingAlarmDevice
    if len(token) != 43:
        raise Http404
    device = MeetingAlarmDevice.objects.select_related('owner').filter(token_hash=hashlib.sha256(token.encode()).hexdigest(),revoked_at__isnull=True,expires_at__gt=timezone.now()).first()
    if device is None or not is_owner(device.owner):
        raise Http404
    return private(JsonResponse(alarm_payload(timezone.now().astimezone(ZONE).date()),json_dumps_params={'ensure_ascii':False}))
