"""09:00 Istanbul inactivity policy for the main platform's web/mobile accounts."""
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

OWNERS = ('guler.volkan@yahoo.com', 'volkancyberframework@gmail.com')
INACTIVITY_MESSAGE = (
    'Hesabınız 20 günden fazla kullanılmadığı veya programa uzun süre erişim '
    'sağlanmadığı için pasife alınmıştır. Erişim talebinizin nedenini ve açıklamanızı '
    'volkan@grcustasi.com adresine e-posta ile gönderiniz. Talebiniz 1 gün içinde '
    'değerlendirilecektir.'
)


def inactivity_message(user):
    return INACTIVITY_MESSAGE if user and not user.is_active and user.inactivity_disabled_at else None


def touch_access(user, *, now=None, force=False):
    """Never record failed authentication or revive a disabled account."""
    now = now or timezone.now()
    qs = get_user_model().objects.filter(pk=user.pk, is_active=True)
    if not force:
        qs = qs.filter(Q(last_account_access_at__isnull=True) | Q(last_account_access_at__lt=now-timedelta(minutes=5)))
    updated = qs.update(last_account_access_at=now)
    if updated:
        user.last_account_access_at = now
    return bool(updated)


class AccountAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated or not request.user.is_active:
            return None
        # JWT endpoints record authenticated access through their permission class.
        if request.path_info.startswith(('/api/', '/web-api/', '/static/', '/media/', '/healthz/')):
            return None
        if request.resolver_match.view_name in {'heartbeat', 'logout', 'login'}:
            return None
        touch_access(request.user)
        return None


@transaction.atomic
def run_due_check(*, now=None):
    """One atomic, durable run/day, at or after 09:00; late restarts catch up."""
    from .models import AccountInactivityRun
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
    now = now or timezone.now()
    local = now.astimezone(ZoneInfo('Europe/Istanbul'))
    if local.hour < 9:
        return None
    run, _ = AccountInactivityRun.objects.get_or_create(reporting_date=local.date())
    run = AccountInactivityRun.objects.select_for_update().get(pk=run.pk)
    if run.completed_at:
        return run
    users = get_user_model().objects.select_for_update().filter(is_active=True).exclude(
        Q(email__iexact=OWNERS[0]) | Q(email__iexact=OWNERS[1]))
    disabled = []
    accounts = []
    cutoff = now - timedelta(days=20)
    for user in users:
        run.checked_count += 1
        latest = max(t for t in (user.last_account_access_at, user.last_login, user.date_joined) if t)
        if latest >= cutoff:
            continue
        # Row locks serialize a successful login/access update with this decision.
        get_user_model().objects.filter(pk=user.pk, is_active=True).update(
            is_active=False, inactivity_disabled_at=now)
        for token in OutstandingToken.objects.filter(user=user, expires_at__gt=now):
            BlacklistedToken.objects.get_or_create(token=token)
        disabled.append(user.pk)
        no_access = user.last_login is None and user.last_account_access_at in (None, user.date_joined)
        accounts.append({'user_id': user.pk, 'email': user.email,
                         'last_access_at': None if no_access else latest.isoformat(),
                         'account_created_at': user.date_joined.isoformat()})
    run.disabled_user_ids = disabled
    run.disabled_accounts = accounts
    run.completed_at = now
    run.save(update_fields=['checked_count', 'disabled_user_ids', 'disabled_accounts', 'completed_at'])
    return run
