"""Isolated refrigerator exercise: no users, sessions, models, or device connections."""
import json
import logging
import math
from datetime import timedelta
from uuid import uuid4
from django.conf import settings
from django.core import signing
from django.core.cache.backends.locmem import LocMemCache
from django.core.mail import get_connection, send_mail
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.template.loader import get_template
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

logger = logging.getLogger(__name__)
_cache = LocMemCache('fridge-demo-only', {})
SALT = 'fridge-demo-v1'


@require_GET
@csrf_protect
def page(request):
    token = signing.dumps({'id': uuid4().hex}, salt=SALT)
    html = get_template('landing/fridge.html').render({'demo_token': token, 'csrf_token': get_token(request)})
    response = HttpResponse(html)
    response['Cache-Control'] = 'no-store'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response


@require_POST
@csrf_protect
def confirm(request):
    if len(request.body) > 4096:
        return JsonResponse({'error': 'İstek çok büyük.'}, status=400)
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError
        signed = signing.loads(data.get('token', ''), salt=SALT, max_age=3600)
        value = data.get('temperature')
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            raise ValueError
        if not math.isfinite(value) or not -30 <= value <= 15 or value == -5:
            raise ValueError
    except (ValueError, TypeError, signing.BadSignature):
        return JsonResponse({'error': 'Geçerli bir sıcaklık seçin. Oturum süresi dolduysa sayfayı yenileyin.'}, status=400)
    if data.get('username') != 'volkanadmin' or data.get('password') != 'volkanseyahat1234':
        return JsonResponse({'error': 'Demo giriş bilgileri geçersiz.'}, status=403)
    ip = request.META.get('HTTP_CF_CONNECTING_IP') or request.META.get('REMOTE_ADDR', '')
    rate_key = 'fridge-rate:' + salted_hmac(SALT, ip).hexdigest()
    _cache.add(rate_key, 0, timeout=60)
    if _cache.incr(rate_key) > 30:
        return JsonResponse({'error': 'Çok fazla deneme yapıldı. Bir dakika sonra tekrar deneyin.'}, status=429)
    key = 'fridge-notified:' + signed['id']
    if not _cache.add(key, True, timeout=3600):
        return JsonResponse({'error': 'Bu demo için bildirim zaten iletildi. Sonuç ekranını kullanabilirsiniz.'}, status=409)
    now = timezone.localtime()
    expires = (now + timedelta(days=10)).strftime('%d.%m.%Y %H:%M')
    try:
        sent = send_mail(
            'GRC Ustası | Buzdolabı simülasyonu tamamlandı',
            f'Bir ziyaretçi /buzdolabi demosunda sıcaklığı değiştirdi ve onayladı.\n'
            f'Demo hesabı: volkanadmin (gerçek kullanıcı değildir)\nÖnceki sıcaklık: -5°C\nYeni sıcaklık: {value:g}°C\n'
            f'Zaman: {now:%d.%m.%Y %H:%M} (Türkiye)\n%60 indirim son tarihi: {expires}\n'
            'Bu yalnızca bir simülasyondur. Gerçek cihaz veya kullanıcı kaydı değiştirilmedi.',
            settings.DEFAULT_FROM_EMAIL, ['volkan@grcustasi.com'], fail_silently=False,
            connection=get_connection(timeout=10),
        )
        if sent != 1:
            raise RuntimeError('Email not accepted')
    except Exception:
        _cache.delete(key)
        logger.warning('Fridge demo email could not be sent; visitor may retry.')
        return JsonResponse({'error': 'Bildirim şu anda iletilemedi. Lütfen tekrar deneyin.'}, status=503)
    return JsonResponse({'ok': True, 'temperature': value, 'expires': expires})


class FridgeDemoMiddleware:
    """Short-circuit before sessions/auth/traffic so even logged-in visits use no DB."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info in ('/buzdolabi', '/buzdolabi/'):
            return page(request)
        if request.path_info == '/buzdolabi/onay':
            return confirm(request)
        return self.get_response(request)
