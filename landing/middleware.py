import logging
import secrets

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import DailyTrafficMetric, LandingVisit


COOKIE_NAME = 'grc_vid'
TRACKED_URL_NAMES = {'landing:home', 'landing:career_compass', 'landing:corporate'}
BOT_MARKERS = (
    'bot', 'crawler', 'spider', 'slurp', 'headless', 'lighthouse', 'pagespeed',
    'pingdom', 'uptime', 'statuscake', 'curl/', 'wget/', 'python-requests',
    'postmanruntime', 'facebookexternalhit', 'whatsapp', 'telegrambot', 'discordbot',
)
logger = logging.getLogger(__name__)


def _is_bot(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').strip().lower()
    return not user_agent or any(marker in user_agent for marker in BOT_MARKERS)


def _visitor_hash(identifier):
    return salted_hmac('landing-visitor', identifier, secret=settings.SECRET_KEY).hexdigest()


class LandingTrafficMiddleware:
    """Counts anonymous daily browser visits without retaining raw IP addresses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        match = getattr(request, 'resolver_match', None)
        if (
            request.method != 'GET'
            or response.status_code >= 400
            or not match
            or match.view_name not in TRACKED_URL_NAMES
            or not response.get('Content-Type', '').startswith('text/html')
        ):
            return response

        try:
            self._record(request, response)
        except Exception:
            # Ölçüm altyapısı hiçbir koşulda ana sayfayı erişilemez hale getirmemeli.
            logger.exception('GRC Ustası trafik ölçümü atlandı.')
        return response

    def _record(self, request, response):
        today = timezone.localdate()
        if _is_bot(request):
            metric, _ = DailyTrafficMetric.objects.get_or_create(date=today)
            DailyTrafficMetric.objects.filter(pk=metric.pk).update(
                filtered_bot_requests=F('filtered_bot_requests') + 1,
            )
            return

        identifier = request.COOKIES.get(COOKIE_NAME)
        is_new_cookie = not identifier
        if is_new_cookie:
            identifier = secrets.token_urlsafe(32)
        digest = _visitor_hash(identifier)

        metric, _ = DailyTrafficMetric.objects.get_or_create(date=today)
        DailyTrafficMetric.objects.filter(pk=metric.pk).update(page_views=F('page_views') + 1)
        try:
            with transaction.atomic():
                visit, created = LandingVisit.objects.get_or_create(
                    visitor_hash=digest,
                    visit_date=today,
                    defaults={
                        'first_path': request.path[:255],
                        'is_returning': LandingVisit.objects.filter(
                            visitor_hash=digest,
                            visit_date__lt=today,
                        ).exists(),
                    },
                )
                if not created:
                    LandingVisit.objects.filter(pk=visit.pk).update(
                        page_views=F('page_views') + 1,
                        last_seen=timezone.now(),
                    )
        except IntegrityError:
            LandingVisit.objects.filter(visitor_hash=digest, visit_date=today).update(
                page_views=F('page_views') + 1,
                last_seen=timezone.now(),
            )

        if is_new_cookie:
            response.set_cookie(
                COOKIE_NAME,
                identifier,
                max_age=60 * 60 * 24 * 365 * 2,
                httponly=True,
                secure=not settings.DEBUG,
                samesite='Lax',
            )
