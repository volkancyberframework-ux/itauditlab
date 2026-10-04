"""Travel checkout: price is server-owned; only signed webhooks enroll users."""
import logging
import json
from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

import stripe
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .models import TravelPayment, TravelRegistration

logger = logging.getLogger(__name__)
PRODUCT = 'travel_bootcamp'
AMOUNT = 24900
CURRENCY = 'usd'
ISTANBUL = ZoneInfo('Europe/Istanbul')
MONTHS = ('Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık')
PROGRAM = (
    ('Seyahatin görünmeyen sistemi', 'Statü, mil, segment ve havayolu ittifakları.'),
    ('Elite → Elite Plus yolun', 'Uçuşlarını maliyet ve statü hedefine göre planla.'),
    ('Ekonomi bütçesiyle Business Class', 'Rota, tarih ve başlangıç noktasının etkisini öğren.'),
    ('Mil sistemini çöz', 'Ödül bilet ve upgrade için milin değerini hesapla.'),
    ('Fırsatları bul', 'Tarih, havalimanı ve fiyatları karşılaştır.'),
    ('Elite yolcunun avantajları', 'Lounge, bagaj, fast track ve öncelikleri tanı.'),
    ('Kendi seyahat sistemin', 'Bütçene uygun 12 aylık kişisel planını oluştur.'),
)


def next_monday(at=None):
    day = (at or timezone.now()).astimezone(ISTANBUL).date()
    return day + timedelta(days=(7 - day.weekday()) % 7 or 7)


def display_date(day):
    return f'{day.day} {MONTHS[day.month - 1]} {day.year}'


def page(request):
    return render(request, 'landing/travel.html', {
        'next_monday': display_date(next_monday()), 'program': PROGRAM,
        'canonical': settings.PUBLIC_BASE_URL.rstrip('/') + reverse('landing:travel_bootcamp'),
        'cancelled': request.GET.get('cancelled') == '1',
        'payment_link': settings.TRAVEL_BOOTCAMP_PAYMENT_LINK or reverse('landing:travel_checkout'),
    })


@never_cache
@require_http_methods(['GET', 'POST'])
def checkout(request):
    # The same local endpoint is used by every CTA. No hand-made Payment Link needed.
    if settings.TRAVEL_BOOTCAMP_PAYMENT_LINK:
        response = redirect(settings.TRAVEL_BOOTCAMP_PAYMENT_LINK)
        response.status_code = 303
        return response
    if not settings.STRIPE_SECRET_KEY:
        return render(request, 'landing/travel_success.html', {'unavailable': True}, status=503)
    base = settings.PUBLIC_BASE_URL.rstrip('/')
    try:
        session = stripe.checkout.Session.create(
            api_key=settings.STRIPE_SECRET_KEY,
            mode='payment', payment_method_types=['card'], customer_creation='always',
            phone_number_collection={'enabled': True},
            billing_address_collection='required',
            line_items=[{'price_data': {
                'currency': CURRENCY, 'unit_amount': AMOUNT,
                'product_data': {'name': 'Travel Bootcamp', 'description': '7 günlük / 7+ saat eğitim, ömür boyu video erişimi ve 6 ay birebir WhatsApp desteği.'},
            }, 'quantity': 1}],
            metadata={'product': PRODUCT},
            payment_intent_data={'metadata': {'product': PRODUCT}},
            success_url=base + reverse('landing:travel_success') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=base + reverse('landing:travel_bootcamp') + '?cancelled=1',
        )
    except stripe.StripeError as exc:
        logger.warning('Travel Checkout oluşturulamadı.')
        response = render(request, 'landing/travel_success.html', {'unavailable': True}, status=502)
        response['X-Payment-Error'] = type(exc).__name__
        response['X-Payment-Code'] = str(getattr(exc, 'code', '') or '')[:80]
        response['X-Payment-Param'] = str(getattr(exc, 'param', '') or '')[:80]
        if getattr(exc, 'param', '') == 'payment_method_types':
            from urllib.parse import quote
            response['X-Payment-Detail'] = quote(getattr(exc, 'user_message', '') or '')[:1500]
        return response
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'url': session.url})
    response = redirect(session.url)
    response.status_code = 303
    return response


def notify_registration(registration_id):
    """Persist failures for retry; notifications never roll back a paid registration."""
    from skool.services import send_telegram
    try:
        with transaction.atomic():
            record = TravelRegistration.objects.select_for_update().get(pk=registration_id)
            if record.telegram_sent_at:
                return
            message = (
                f'✈️ YENİ TRAVEL BOOTCAMP KAYDI!\n\n👤 {record.name}\n📧 {record.email}\n'
                f'💰 $249\n📅 {display_date(record.registered_at.astimezone(ISTANBUL).date())}\n'
                f'🚀 Başlangıç: {display_date(record.starts_on)} Pazartesi\n\n🌍 Travel Bootcamp'
            )
            if send_telegram(message, idempotency_key=f'travel-registration-{record.pk}'):
                record.telegram_sent_at = timezone.now()
                record.save(update_fields=['telegram_sent_at'])
    except Exception:
        # Do not log request exceptions: their URL can contain the Telegram bot token.
        logger.warning('Travel Telegram bildirimi bekliyor; kayıt no: %s', registration_id)


@csrf_exempt
@require_POST
def webhook(request):
    secret = settings.TRAVEL_BOOTCAMP_WEBHOOK_SECRET
    if not secret:
        return JsonResponse({'error': 'Webhook unavailable'}, status=503)
    try:
        stripe.Webhook.construct_event(request.body, request.headers.get('Stripe-Signature', ''), secret)
        event = json.loads(request.body)
    except (ValueError, stripe.SignatureVerificationError):
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    if event['type'] not in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
        return JsonResponse({'received': True})
    session = event['data']['object']
    if (session.get('metadata') or {}).get('product') != PRODUCT or session.get('payment_status') != 'paid':
        return JsonResponse({'received': True})
    if (session.get('mode') != 'payment' or session.get('amount_total') != AMOUNT
            or session.get('currency') != CURRENCY):
        return JsonResponse({'error': 'Unexpected product amount or currency'}, status=400)
    if settings.STRIPE_SECRET_KEY:
        live = settings.STRIPE_SECRET_KEY.startswith(('sk_live_', 'rk_live_'))
        if bool(event.get('livemode')) != live:
            return JsonResponse({'error': 'Wrong Stripe mode'}, status=400)
    details = session.get('customer_details') or {}
    email = (details.get('email') or '').strip().lower()
    try:
        validate_email(email)
        if not session.get('id') or not session.get('payment_intent'):
            raise ValueError('Missing transaction identifier')
        paid_at = datetime.fromtimestamp(event['created'], tz=dt_timezone.utc)
    except (ValidationError, ValueError, KeyError, TypeError, OverflowError):
        return JsonResponse({'error': 'Incomplete checkout data'}, status=400)
    # Unique constraints are the final guard for concurrent deliveries. DB errors
    # intentionally return 500 so Stripe retries instead of silently losing orders.
    with transaction.atomic():
        payment = TravelPayment.objects.filter(
            Q(checkout_session_id=session['id']) | Q(payment_intent_id=session['payment_intent'])
        ).first()
        if payment:
            registration = payment.registration
        else:
            registration, _ = TravelRegistration.objects.get_or_create(email=email, defaults={
                'name': (details.get('name') or '')[:255],
                'phone': (details.get('phone') or '')[:80],
                'registered_at': paid_at, 'starts_on': next_monday(paid_at),
            })
            TravelPayment.objects.get_or_create(
                payment_intent_id=session['payment_intent'], defaults={
                    'registration': registration, 'checkout_session_id': session['id'],
                    'customer_id': session.get('customer') or '', 'stripe_event_id': event['id'],
                    'amount_minor': session['amount_total'], 'currency': session['currency'], 'paid_at': paid_at,
                },
            )
        transaction.on_commit(lambda: notify_registration(registration.pk))
    return JsonResponse({'received': True})


def _confirmed_payment(request):
    session_id = request.GET.get('session_id', '')
    if not session_id.startswith('cs_') or len(session_id) > 255:
        return None
    return TravelPayment.objects.select_related('registration').filter(checkout_session_id=session_id).first()


@never_cache
@require_GET
def success(request):
    payment = _confirmed_payment(request)
    response = render(request, 'landing/travel_success.html', {
        'confirmed': bool(payment),
        'starts_on': display_date(payment.registration.starts_on) if payment else '',
        'pending': not payment and bool(request.GET.get('session_id')),
    })
    response['Referrer-Policy'] = 'no-referrer'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response


@never_cache
@require_GET
def status(request):
    payment = _confirmed_payment(request)
    # Deliberately expose no name/email/customer IDs through this bearer URL.
    return JsonResponse({'confirmed': bool(payment)})
