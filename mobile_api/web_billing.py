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
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST
from rest_framework.response import Response
from .models import MobilePayment, MobileCheckoutRequest
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
@ensure_csrf_cookie
@require_GET
def page(request):
    user = token_user(request.GET.get('token', ''))
    response = render(request, 'mobile_api/membership.html', {
        'email': user.email if user else '', 'token': request.GET.get('token', '') if user else '',
        'cancelled': request.GET.get('cancelled') == '1'})
    response['Referrer-Policy'] = 'no-referrer'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response


@never_cache
@ensure_csrf_cookie
@require_GET
def csrf_token(request):
    return JsonResponse({'token': get_token(request)})


@never_cache
@require_POST
def checkout(request):
    from django.core.cache import cache
    user = token_user(request.POST.get('token', ''))
    email = (user.email if user else request.POST.get('email', '')).strip().casefold()
    try:
        validate_email(email)
        if len(email) > 254:
            raise ValidationError('Invalid')
    except ValidationError:
        return render(request, 'mobile_api/membership.html', {'error': 'Geçerli bir e-posta adresi gir.', 'email': email}, status=400)
    # Only bind an existing account internally. No account details or login tokens are disclosed.
    if not user:
        matches = list(get_user_model().objects.filter(email__iexact=email)[:2])
        if len(matches) > 1 or (matches and not matches[0].is_active):
            return render(request, 'mobile_api/membership.html', {'error': 'Bu e-posta için ödeme başlatılamıyor. volkan@grcustasi.com adresine ulaşın.', 'email': email}, status=400)
        user = matches[0] if matches else None
    if user and user.mobile_last_date and user.mobile_last_date < timezone.localdate():
        return render(request, 'mobile_api/membership.html', {'error': 'Hesabın erişim tarihini güncellemek için volkan@grcustasi.com adresine ulaşın.', 'email': email}, status=400)
    import hashlib
    keys = ['mobile-checkout-ip:' + request.META.get('REMOTE_ADDR', ''), 'mobile-checkout-email:' + hashlib.sha256(email.encode()).hexdigest()]
    if any(cache.get(key, 0) >= 10 for key in keys):
        return render(request, 'mobile_api/membership.html', {'error': 'Çok sayıda deneme yapıldı. 10 dakika sonra tekrar deneyin.', 'email': email}, status=429)
    for key in keys:
        cache.add(key, 0, 600)
        cache.incr(key)
    if not settings.STRIPE_SECRET_KEY or not settings.MOBILE_STRIPE_WEBHOOK_SECRET:
        return render(request, 'mobile_api/membership.html', {'error': 'Ödeme şu anda kullanılamıyor. Lütfen biraz sonra tekrar dene.', 'email': email}, status=503)
    pending = MobileCheckoutRequest.objects.create(email=email, user=user)
    base = settings.PUBLIC_BASE_URL.rstrip('/')
    try:
        session = stripe.checkout.Session.create(
            api_key=settings.STRIPE_SECRET_KEY, mode='payment',
            customer_email=email, client_reference_id=str(pending.pk),
            line_items=[{'price_data': {'currency': 'try', 'unit_amount': AMOUNT,
                'product_data': {'name': 'GRC Ustası • 1 aylık mobil tam erişim'}}, 'quantity': 1}],
            metadata={'product': PRODUCT, 'mobile_checkout_id': str(pending.pk)},
            payment_intent_data={'metadata': {'product': PRODUCT, 'mobile_checkout_id': str(pending.pk)}},
            success_url=base + reverse('landing:mobile_success') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=base + reverse('landing:mobile_membership') + '?cancelled=1',
        )
        pending.checkout_session_id = session.id
        pending.save(update_fields=['checkout_session_id'])
    except stripe.StripeError:
        return render(request, 'mobile_api/membership.html', {'error': 'Ödeme başlatılamadı. Lütfen tekrar dene.', 'email': email}, status=502)
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
            or session.get('client_reference_id') != (metadata.get('mobile_checkout_id') or metadata.get('mobile_user_id'))):
        return JsonResponse({'error': 'Invalid payment'}, status=400)
    try:
        paid_at = datetime.fromtimestamp(event['created'], tz=utc.utc)
        with transaction.atomic():
            existing = MobilePayment.objects.filter(checkout_session_id=session['id']).first()
            if existing:
                from .payment_mail import send_payment_receipt
                transaction.on_commit(lambda: send_payment_receipt(existing.pk))
                return JsonResponse({'received': True})
            User = get_user_model()
            if metadata.get('mobile_checkout_id'):
                pending = MobileCheckoutRequest.objects.select_for_update().get(pk=metadata['mobile_checkout_id'])
                if pending.checkout_session_id and pending.checkout_session_id != session['id']:
                    return JsonResponse({'error': 'Invalid session'}, status=400)
                if pending.user_id:
                    user = User.objects.select_for_update().get(pk=pending.user_id, is_active=True)
                else:
                    import hashlib
                    username = 'mobile_' + hashlib.sha256(pending.email.encode()).hexdigest()[:40]
                    # The deterministic username serializes simultaneous purchases of a new account.
                    matches = list(User.objects.filter(email__iexact=pending.email)[:2])
                    if len(matches) > 1:
                        raise ValueError('Ambiguous account')
                    if matches:
                        user, created = matches[0], False
                    else:
                        user, created = User.objects.get_or_create(username=username, defaults={'email': pending.email, 'first_name': pending.email.split('@')[0][:150], 'is_mobile': True, 'mobile_must_change_password': True, 'mobile_email_verified': False})
                    user = User.objects.select_for_update().get(pk=user.pk, is_active=True)
                    if created:
                        user.set_unusable_password()
                    if user.email.casefold() != pending.email.casefold():
                        raise ValueError('Account mismatch')
                pending.user = user
                pending.checkout_session_id = session['id']
                pending.save(update_fields=['user', 'checkout_session_id'])
            else:
                # Fulfil checkout sessions issued before the email-only change.
                user = User.objects.select_for_update().get(pk=int(metadata['mobile_user_id']), is_mobile=True)
            user.is_mobile = True
            if not user.has_usable_password():
                user.mobile_must_change_password = True
            # Lock the user before evaluating renewal; overlapping payments extend access.
            start = timezone.localtime(max(paid_at, user.mobile_paid_until or paid_at))
            until = add_month(start)
            payment = MobilePayment.objects.create(user=user, checkout_session_id=session['id'],
                payment_intent_id=session['payment_intent'], stripe_event_id=event['id'],
                paid_at=paid_at, access_until=until, amount_minor=AMOUNT)
            user.mobile_paid_until = until
            user.save(update_fields=['mobile_paid_until', 'is_mobile', 'mobile_must_change_password', 'password'])
            from .payment_mail import send_payment_receipt
            transaction.on_commit(lambda: send_payment_receipt(payment.pk))
    except (KeyError, ValueError, TypeError, OverflowError, get_user_model().DoesNotExist, MobileCheckoutRequest.DoesNotExist, ValidationError):
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
