"""One calendar month per verified web payment; mobile identity is server-bound."""
import calendar
import json
from datetime import datetime, timezone as utc
from urllib.parse import urlencode
import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.response import Response
from .models import MobilePayment
from .views import MobileView

PRODUCT = 'grcustasi_mobile_month'
AMOUNT = 209900
SALT = 'mobile-payment-identity-v1'


def token_for(user):
    return signing.dumps({'user': user.pk, 'hash': user.get_session_auth_hash()}, salt=SALT)


def token_user(token):
    try:
        data = signing.loads(token, salt=SALT, max_age=1800)
        user = get_user_model().objects.get(pk=data['user'], is_active=True, is_mobile=True)
        if (data['hash'] != user.get_session_auth_hash()
                or (user.mobile_last_date and user.mobile_last_date < timezone.localdate())):
            return None
        return user
    except (signing.BadSignature, KeyError, TypeError, get_user_model().DoesNotExist):
        return None


class PaymentLink(MobileView):
    def post(self, request):
        return Response({'url': settings.PUBLIC_BASE_URL.rstrip('/') + reverse('landing:mobile_membership') + '?' + urlencode({'token': token_for(request.user)})})


@never_cache
def page(request):
    token = request.GET.get('token', '')
    user = token_user(token)
    error = ''
    if request.method == 'POST':
        from django.core.cache import cache
        # Per-address plus per-account throttling protects the website login too.
        keys = ['mobile-pay-login-ip:' + request.META.get('REMOTE_ADDR', ''),
                'mobile-pay-login-email:' + request.POST.get('email', '').strip().casefold()[:254]]
        blocked = any(cache.get(key, 0) >= 10 for key in keys)
        if not blocked:
            for key in keys:
                cache.add(key, 0, 600)
                cache.incr(key)
            matches = list(get_user_model().objects.filter(email__iexact=request.POST.get('email', '').strip(), is_mobile=True, is_active=True)[:2])
            if (len(matches) == 1 and matches[0].check_password(request.POST.get('password', ''))
                    and token_user(token_for(matches[0]))):
                response = redirect(reverse('landing:mobile_membership') + '?' + urlencode({'token': token_for(matches[0])}))
                response['Referrer-Policy'] = 'no-referrer'
                return response
        error = 'E-posta veya şifre hatalı. Çok sayıda deneme yaptıysan 10 dakika sonra tekrar dene.'
    response = render(request, 'mobile_api/membership.html', {'member': user, 'token': token if user else '', 'error': error, 'cancelled': request.GET.get('cancelled') == '1'})
    response['Referrer-Policy'] = 'no-referrer'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response


@never_cache
@require_POST
def checkout(request):
    user = token_user(request.POST.get('token', ''))
    if not user:
        return render(request, 'mobile_api/membership.html', {'error': 'Bağlantının süresi doldu. Mobil hesabınla tekrar giriş yap.'}, status=400)
    if not settings.STRIPE_SECRET_KEY or not settings.MOBILE_STRIPE_WEBHOOK_SECRET:
        return render(request, 'mobile_api/membership.html', {'error': 'Ödeme şu anda kullanılamıyor. Lütfen biraz sonra tekrar dene.'}, status=503)
    base = settings.PUBLIC_BASE_URL.rstrip('/')
    try:
        session = stripe.checkout.Session.create(
            api_key=settings.STRIPE_SECRET_KEY, mode='payment',
            customer_email=user.email, client_reference_id=str(user.pk),
            line_items=[{'price_data': {'currency': 'try', 'unit_amount': AMOUNT,
                'product_data': {'name': 'GRC Ustası • 1 aylık mobil tam erişim'}}, 'quantity': 1}],
            metadata={'product': PRODUCT, 'mobile_user_id': str(user.pk)},
            payment_intent_data={'metadata': {'product': PRODUCT, 'mobile_user_id': str(user.pk)}},
            success_url=base + reverse('landing:mobile_success') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=base + reverse('landing:mobile_membership') + '?' + urlencode({'token': token_for(user), 'cancelled': '1'}),
        )
    except stripe.StripeError:
        return render(request, 'mobile_api/membership.html', {'error': 'Ödeme başlatılamadı. Lütfen tekrar dene.'}, status=502)
    response = redirect(session.url)
    response.status_code = 303
    response['Referrer-Policy'] = 'no-referrer'
    return response


def add_month(value):
    month = value.month % 12 + 1
    year = value.year + (value.month == 12)
    return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))


@csrf_exempt
@require_POST
def webhook(request):
    if not settings.MOBILE_STRIPE_WEBHOOK_SECRET:
        return JsonResponse({'error': 'Unavailable'}, status=503)
    try:
        stripe.Webhook.construct_event(request.body, request.headers.get('Stripe-Signature', ''), settings.MOBILE_STRIPE_WEBHOOK_SECRET)
        event = json.loads(request.body)
    except (ValueError, stripe.SignatureVerificationError):
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    if event['type'] not in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
        return JsonResponse({'received': True})
    session = event['data']['object']
    metadata = session.get('metadata') or {}
    if metadata.get('product') != PRODUCT or session.get('payment_status') != 'paid':
        return JsonResponse({'received': True})
    live = settings.STRIPE_SECRET_KEY.startswith(('sk_live_', 'rk_live_'))
    if (session.get('amount_total') != AMOUNT or session.get('currency') != 'try'
            or session.get('mode') != 'payment' or bool(event.get('livemode')) != live
            or not session.get('id') or not session.get('payment_intent')
            or session.get('client_reference_id') != metadata.get('mobile_user_id')):
        return JsonResponse({'error': 'Invalid payment'}, status=400)
    try:
        paid_at = datetime.fromtimestamp(event['created'], tz=utc.utc)
        with transaction.atomic():
            user = get_user_model().objects.select_for_update().get(pk=int(metadata['mobile_user_id']), is_mobile=True)
            if MobilePayment.objects.filter(checkout_session_id=session['id']).exists():
                return JsonResponse({'received': True})
            # Lock the user before evaluating renewal; overlapping payments extend access.
            start = timezone.localtime(max(paid_at, user.mobile_paid_until or paid_at))
            until = add_month(start)
            MobilePayment.objects.create(user=user, checkout_session_id=session['id'],
                payment_intent_id=session['payment_intent'], stripe_event_id=event['id'],
                paid_at=paid_at, access_until=until, amount_minor=AMOUNT)
            user.mobile_paid_until = until
            user.save(update_fields=['mobile_paid_until'])
    except (KeyError, ValueError, TypeError, OverflowError, get_user_model().DoesNotExist):
        return JsonResponse({'error': 'Unknown mobile account'}, status=400)
    return JsonResponse({'received': True})


@never_cache
def success(request):
    session_id = request.GET.get('session_id', '')
    payment = MobilePayment.objects.filter(checkout_session_id=session_id).first() if session_id.startswith('cs_') and len(session_id) <= 255 else None
    response = render(request, 'mobile_api/payment_success.html', {'confirmed': bool(payment)})
    response['Referrer-Policy'] = 'no-referrer'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response
