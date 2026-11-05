"""399 EUR, 43 places. Only verified paid Stripe sessions can allocate a rank."""
import logging
import uuid
from datetime import datetime, timedelta, timezone as utc
from decimal import Decimal, localcontext
import stripe
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from .chip_models import ChipCampaign, ChipPurchase

logger = logging.getLogger(__name__)
AMOUNT = 39900
CAPACITY = 43
PRODUCT = 'siberkobi_chip_equity_participation'
PRODUCT_NAME = 'Skool Topluluğuna Özel Siberkobi Çip Satın Alımı'
PRODUCT_DESCRIPTION = 'Siberkobi hisse/kâr payı katılımı. Haklar ilgili sözleşme ve hukuki işlemler tamamlandıktan sonra kesinleşir.'
TERMS_VERSION = 'chip-disclosure-v1'


def stripe_data(value):
    # Stripe SDK 16 resources expose to_dict(), not dict.get().
    return value.to_dict() if hasattr(value, 'to_dict') else value


def share_percent(position):
    if not 1 <= position <= CAPACITY:
        raise ValueError('Invalid position')
    if position <= 3:
        return Decimal('0.50') if position == 1 else Decimal('0.25')
    with localcontext() as ctx:
        ctx.prec = 50
        unit = Decimal('0.00000000000000000001')
        if position == 43:
            return Decimal('1') - sum(share_percent(n) for n in range(4, 43))
        return (Decimal('.1') * Decimal('.9') ** (position - 4) / (1 - Decimal('.9') ** 40)).quantize(unit)


def percent_text(value):
    return f'{value:.8f}'.replace('.', ',')


def key_for(mode):
    if mode == 'live':
        if not settings.CHIP_LIVE_PAYMENTS_ENABLED:
            return ''
        key = settings.CHIP_STRIPE_LIVE_KEY
        return key if key.startswith(('sk_live_', 'rk_live_')) else ''
    key = settings.CHIP_STRIPE_TEST_KEY
    return key if key.startswith(('sk_test_', 'rk_test_')) else ''


def campaign_for(mode):
    if mode not in ('test', 'live'):
        raise Http404
    return ChipCampaign.objects.get_or_create(mode=mode)[0]


def base_url():
    return settings.PUBLIC_BASE_URL.rstrip('/')


def receipt_url(purchase):
    return base_url() + reverse('landing:chip_receipt', args=[purchase.pk])


def protected(response):
    response['Referrer-Policy'] = 'no-referrer'
    response['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
    response['Cache-Control'] = 'private, no-store'
    return response


@never_cache
@require_GET
def page(request, mode='live'):
    campaign = campaign_for(mode)
    pending = campaign.purchases.filter(generation=campaign.generation, state='pending').count()
    return protected(render(request, 'landing/chip.html', {
        'campaign': campaign, 'test': mode == 'test',
        'available': campaign.enabled and bool(key_for(mode)) and bool(getattr(settings, f'CHIP_STRIPE_{mode.upper()}_WEBHOOK_SECRET')) and campaign.confirmed_count + pending < CAPACITY,
        'pending': pending, 'remaining': max(0, CAPACITY - campaign.confirmed_count - pending),
        'next_share': percent_text(share_percent(campaign.confirmed_count + 1)) if campaign.confirmed_count < CAPACITY else None,
        'checkout_url': reverse('landing:chip_checkout', args=[mode]),
        'formula_rows': [(n, percent_text(share_percent(n))) for n in range(1, 44)],
        'cancelled': request.GET.get('cancelled') == '1',
    }))


def checkout_arguments(purchase):
    campaign = purchase.campaign
    return dict(
        mode='payment', payment_method_types=['card'], customer_creation='always',
        line_items=[{'price_data': {'currency': 'eur', 'unit_amount': AMOUNT,
            'product_data': {'name': PRODUCT_NAME, 'description': PRODUCT_DESCRIPTION}}, 'quantity': 1}],
        client_reference_id=str(purchase.pk),
        metadata={'product': PRODUCT, 'chip_id': str(purchase.pk), 'generation': str(purchase.generation)},
        payment_intent_data={'metadata': {'product': PRODUCT, 'chip_id': str(purchase.pk)}},
        expires_at=int(purchase.expires_at.timestamp()),
        success_url=receipt_url(purchase),
        cancel_url=base_url() + reverse('landing:chip_test' if campaign.mode == 'test' else 'landing:chip_page') + '?cancelled=1',
    )


def create_stripe_session(purchase):
    session = stripe.checkout.Session.create(
        **checkout_arguments(purchase), api_key=key_for(purchase.campaign.mode),
        idempotency_key=f'chip-checkout-{purchase.pk}',
    )
    session = stripe_data(session)
    ChipPurchase.objects.filter(pk=purchase.pk, stripe_session=None).update(stripe_session=session['id'])
    return session


@never_cache
@require_POST
def checkout(request, mode):
    campaign = campaign_for(mode)
    secret = getattr(settings, f'CHIP_STRIPE_{mode.upper()}_WEBHOOK_SECRET')
    if not campaign.enabled or not key_for(mode) or not secret:
        return protected(render(request, 'landing/chip_notice.html', {'message': 'Bu ödeme bağlantısı şu anda kapalı.'}, status=403))
    if request.POST.get('acknowledge') != TERMS_VERSION:
        return protected(render(request, 'landing/chip_notice.html', {'message': 'Katılım açıklamasını okuyup onayla.'}, status=400))
    # One reservation per browser. It does not allocate a rank or promise a rate.
    from django.core.cache import cache
    import hashlib
    throttle = 'chip-checkout:' + hashlib.sha256(request.META.get('REMOTE_ADDR', '').encode()).hexdigest()
    cache.add(throttle, 0, 600)
    if cache.incr(throttle) > 15:
        return JsonResponse({'error': 'Çok sayıda deneme. Biraz sonra tekrar dene.'}, status=429)
    with transaction.atomic():
        campaign = ChipCampaign.objects.select_for_update().get(pk=campaign.pk)
        if not campaign.enabled:
            return JsonResponse({'error': 'Bağlantı kapalı.'}, status=403)
        purchase = None
        token = request.session.get('chip_pending_' + mode)
        if token:
            purchase = campaign.purchases.filter(pk=token, generation=campaign.generation, state='pending').first()
        if not purchase:
            reserved = campaign.purchases.filter(generation=campaign.generation, state='pending').count()
            if campaign.confirmed_count + reserved >= CAPACITY:
                return protected(render(request, 'landing/chip_notice.html', {'message': '43 kontenjan dolu veya ödeme aşamasında. Daha sonra tekrar kontrol edebilirsin.'}, status=409))
            purchase = campaign.purchases.create(generation=campaign.generation, expires_at=timezone.now() + timedelta(minutes=31))
            request.session['chip_pending_' + mode] = str(purchase.pk)
    try:
        if purchase.stripe_session:
            session = stripe_data(stripe.checkout.Session.retrieve(purchase.stripe_session, api_key=key_for(mode)))
        else:
            session = create_stripe_session(purchase)
        if session.get('status') == 'expired':
            with transaction.atomic():
                ChipCampaign.objects.select_for_update().get(pk=campaign.pk)
                ChipPurchase.objects.filter(pk=purchase.pk, state='pending').update(state='expired')
            return protected(render(request, 'landing/chip_notice.html', {'message': 'Ödeme oturumunun süresi doldu. Katılım sayfasından yeni bir ödeme başlatabilirsin.'}, status=409))
        if not session.get('url'):
            return redirect(receipt_url(purchase))
    except stripe.StripeError:
        logger.warning('Chip checkout pending for reconciliation: %s', purchase.pk)
        return protected(render(request, 'landing/chip_notice.html', {'message': 'Stripe bağlantısı kurulamadı. Aynı tarayıcıdan yeniden dene; kontenjan kaydın korunuyor.'}, status=502))
    response = redirect(session['url'])
    response.status_code = 303
    return protected(response)


def fulfil(session):
    """Both signed webhooks and server-to-server retrieval may call this function."""
    session = stripe_data(session)
    metadata = session.get('metadata') or {}
    if metadata.get('product') != PRODUCT or session.get('payment_status') != 'paid':
        return None
    try:
        purchase = ChipPurchase.objects.select_related('campaign').get(pk=uuid.UUID(metadata['chip_id']))
    except (ChipPurchase.DoesNotExist, ValueError, KeyError, TypeError, AttributeError):
        raise ValidationError('Unknown chip checkout')
    details = session.get('customer_details') or {}
    email = (details.get('email') or '').strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        raise ValidationError('Missing payer email')
    live = purchase.campaign.mode == 'live'
    if (session.get('amount_total') != AMOUNT or session.get('currency') != 'eur'
            or session.get('mode') != 'payment' or session.get('livemode') is not live
            or session.get('client_reference_id') != str(purchase.pk)
            or metadata.get('generation') != str(purchase.generation)
            or not session.get('id') or not session.get('payment_intent')
            or len(email) > 254):
        raise ValidationError('Invalid payment')
    with transaction.atomic():
        campaign = ChipCampaign.objects.select_for_update().get(pk=purchase.campaign_id)
        purchase = ChipPurchase.objects.select_for_update().get(pk=purchase.pk)
        if purchase.generation != campaign.generation:
            # Reset only affects test generations; late test callbacks cannot reappear.
            return None
        if purchase.stripe_session and purchase.stripe_session != session['id']:
            raise ValidationError('Wrong session')
        if purchase.state == 'paid':
            if purchase.payment_intent != session['payment_intent']:
                raise ValidationError('Wrong payment intent')
        else:
            if purchase.state != 'pending' or campaign.confirmed_count >= CAPACITY:
                raise ValidationError('Payment requires reconciliation')
            campaign.confirmed_count += 1
            purchase.position = campaign.confirmed_count
            purchase.share_percent = share_percent(purchase.position)
            purchase.stripe_session = session['id']
            purchase.payment_intent = session['payment_intent']
            purchase.email = email
            purchase.name = (details.get('name') or '')[:255]
            purchase.state = 'paid'
            purchase.paid_at = timezone.now()
            purchase.save()
            campaign.save(update_fields=['confirmed_count'])
        transaction.on_commit(lambda: notify(purchase.pk), robust=True)
    return purchase


@csrf_exempt
@require_POST
def webhook(request, mode):
    if mode not in ('test', 'live'):
        raise Http404
    secret = getattr(settings, f'CHIP_STRIPE_{mode.upper()}_WEBHOOK_SECRET')
    if not secret:
        return JsonResponse({'error': 'Webhook unavailable'}, status=503)
    try:
        event = stripe_data(stripe.Webhook.construct_event(request.body, request.headers.get('Stripe-Signature', ''), secret))
    except (ValueError, stripe.SignatureVerificationError):
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    if event.get('livemode') is not (mode == 'live'):
        return JsonResponse({'error': 'Wrong Stripe mode'}, status=400)
    session = event.get('data', {}).get('object', {})
    if (session.get('metadata') or {}).get('product') != PRODUCT:
        return JsonResponse({'received': True})
    try:
        if event['type'] in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
            fulfil(session)
        elif event['type'] == 'checkout.session.expired':
            with transaction.atomic():
                campaign = campaign_for(mode)
                ChipCampaign.objects.select_for_update().get(pk=campaign.pk)
                ChipPurchase.objects.filter(campaign=campaign, stripe_session=session.get('id'), state='pending').update(state='expired')
    except ValidationError:
        return JsonResponse({'error': 'Payment requires reconciliation'}, status=400)
    return JsonResponse({'received': True})


def mask(value):
    return ' '.join(part[0] + '***' for part in value.split()) if value else 'Katılımcı'


def mask_email(email):
    local, _, domain = email.partition('@')
    host, dot, suffix = domain.rpartition('.')
    return f'{local[:1]}***@{host[:1]}***{dot}{suffix}'


def purchase_data(purchase):
    campaign = purchase.campaign
    if purchase.generation != campaign.generation:
        return {'state': 'archived', 'message': 'Bu test dönemi sıfırlandı. Yeni denemeye baştan başlayabilirsin.'}
    if purchase.state != 'paid':
        return {'state': purchase.state}
    previous = campaign.purchases.filter(generation=campaign.generation, state='paid', position__lte=purchase.position).order_by('position')
    return {'state': 'paid', 'position': purchase.position, 'email': purchase.email,
        'share': percent_text(purchase.share_percent), 'test': campaign.mode == 'test',
        'participants': [{'position': p.position, 'name': mask(p.name),
            'email': purchase.email if p.pk == purchase.pk else mask_email(p.email),
            'share': percent_text(p.share_percent), 'self': p.pk == purchase.pk} for p in previous]}


@never_cache
@require_GET
def receipt(request, token):
    purchase = get_object_or_404(ChipPurchase.objects.select_related('campaign'), pk=token)
    return protected(render(request, 'landing/chip_receipt.html', {'purchase': purchase, 'data': purchase_data(purchase), 'status_url': reverse('landing:chip_status', args=[token])}))


@never_cache
@require_GET
def status(request, token):
    purchase = get_object_or_404(ChipPurchase.objects.select_related('campaign'), pk=token)
    # The payer can return before Stripe's webhook. Verify with Stripe, never query parameters.
    if purchase.state == 'pending' and purchase.generation == purchase.campaign.generation and purchase.stripe_session and key_for(purchase.campaign.mode):
        try:
            session = stripe.checkout.Session.retrieve(purchase.stripe_session, api_key=key_for(purchase.campaign.mode))
            fulfil(session)
            purchase.refresh_from_db()
        except stripe.StripeError:
            pass
        except ValidationError:
            logger.warning('Chip status needs reconciliation: %s', purchase.pk)
    return protected(JsonResponse(purchase_data(purchase)))


def notify(pk):
    from django.core.mail import send_mail, get_connection
    from skool.services import send_telegram
    errors = []
    # Serialize notification retries; a repeated event never allocates or emails twice.
    with transaction.atomic():
        purchase = ChipPurchase.objects.select_for_update().select_related('campaign').get(pk=pk)
        if purchase.state != 'paid' or purchase.generation != purchase.campaign.generation:
            return
        test = purchase.campaign.mode == 'test'
        label = '[TEST — gerçek ödeme/hak yok] ' if test else ''
        text = (f'{label}Siberkobi çip katılımın kaydedildi.\\n\\n'
            f'E-posta: {purchase.email}\\nKatılım sıran: {purchase.position}.\\n'
            f'Hesaplanan şirket payın: %{percent_text(purchase.share_percent)}\\n'
            f'Tutar: 399 EUR\\n\\nSıranı ve önceki katılımcıları gör: {receipt_url(purchase)}\\n\\n'
            'Gösterilen oran hesaplanan katılım payıdır. Gerçek hisse veya kâr paylaşımı hakları ilgili sözleşmeler ve gerekli hukuki işlemler tamamlandıktan sonra kesinleşir. Yatırım getirisi garanti değildir.').replace('\\n', '\n')
        if not purchase.email_sent_at:
            try:
                if send_mail(label + 'Siberkobi • Katılım sıran ve payın', text, settings.DEFAULT_FROM_EMAIL,
                        [purchase.email], connection=get_connection(timeout=10)) != 1:
                    raise RuntimeError('SMTP not accepted')
                purchase.email_sent_at = timezone.now()
            except Exception:
                errors.append('E-posta bekliyor')
        if not purchase.telegram_sent_at:
            try:
                if not send_telegram(f'{label}💳 Siberkobi çip ödemesi\\n{purchase.name}\\n{purchase.email}\\nSıra: {purchase.position}/43\\nPay: %{percent_text(purchase.share_percent)}\\nTutar: 399 EUR'.replace('\\n', '\n'), idempotency_key=f'chip-paid-{purchase.pk}'):
                    from skool.models import NotificationLog
                    if not NotificationLog.objects.filter(key=f'chip-paid-{purchase.pk}', detail__status='sent').exists():
                        raise RuntimeError('Telegram not accepted')
                purchase.telegram_sent_at = timezone.now()
            except Exception:
                errors.append('Telegram bekliyor')
        purchase.notification_error = '; '.join(errors)
        purchase.save(update_fields=['email_sent_at', 'telegram_sent_at', 'notification_error'])


def reset_test():
    """Archive, do not delete. No live ledger, Stripe charge, or refund is touched."""
    with transaction.atomic():
        campaign = ChipCampaign.objects.select_for_update().get(mode='test')
        campaign.generation = uuid.uuid4()
        campaign.confirmed_count = 0
        campaign.enabled = False
        campaign.save(update_fields=['generation', 'confirmed_count', 'enabled'])
