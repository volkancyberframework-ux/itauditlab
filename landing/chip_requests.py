"""Self-reported requests: no charge, payment verification, or real share allocation."""
import hashlib
import uuid
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .chip import share_percent, percent_text, protected, mask_email
from .chip_models import ChipRequestRound, ChipParticipationRequest

CAPACITY = 43


def get_round(mode):
    if mode not in ('live', 'test'):
        raise Http404
    return ChipRequestRound.objects.get_or_create(mode=mode)[0]


def context(request, mode, **extra):
    round = get_round(mode)
    nonce = str(uuid.uuid4())
    # Several tabs may coexist. Only nonces issued to this browser may submit.
    nonces = request.session.get('chip_request_nonces', [])[-19:] + [nonce]
    request.session['chip_request_nonces'] = nonces
    return {'round': round, 'test': mode == 'test', 'remaining': CAPACITY - round.requested_units,
        'submit_url': reverse('landing:chip_request_submit', args=[mode]), 'nonce': nonce, **extra}


@never_cache
@require_GET
def page(request, mode='live'):
    return protected(render(request, 'landing/chip.html', context(request, mode)))


def invalid(request, mode, message, status=400):
    return protected(render(request, 'landing/chip.html', context(request, mode,
        error=message, email=request.POST.get('email', '')[:254]), status=status))


@never_cache
@require_POST
def submit(request, mode):
    round = get_round(mode)
    email = request.POST.get('email', '').strip().lower()
    try:
        validate_email(email)
        quantity_raw = request.POST.get('quantity', '1')
        if len(email) > 254 or len(quantity_raw) > 2:
            raise ValueError
        quantity = int(quantity_raw)
        if not 1 <= quantity <= CAPACITY:
            raise ValueError
        nonce = uuid.UUID(request.POST.get('nonce', ''))
        generation = uuid.UUID(request.POST.get('generation', ''))
        if generation != round.generation:
            raise ValueError
        if str(nonce) not in request.session.get('chip_request_nonces', []):
            raise ValueError
    except (ValidationError, ValueError, TypeError, AttributeError):
        return invalid(request, mode, 'Geçerli e-posta ve 1–43 arasında çip adedi gir. Sayfa eskiyse yenileyip tekrar dene.')
    existing = round.requests.filter(generation=round.generation, nonce=nonce).first()
    if existing:
        return redirect('landing:chip_receipt', token=existing.pk)
    for value in ('ip:' + request.META.get('REMOTE_ADDR', ''), 'email:' + email):
        key = 'chip-request:' + hashlib.sha256(value.encode()).hexdigest()
        cache.add(key, 0, 3600)
        if cache.incr(key) > 10:
            return invalid(request, mode, 'Çok sayıda talep oluşturuldu. Daha sonra tekrar dene.', status=429)
    with transaction.atomic():
        round = ChipRequestRound.objects.select_for_update().get(pk=round.pk)
        if generation != round.generation:
            return invalid(request, mode, 'Talep dönemi değişti. Sayfayı yenileyip yeniden gönder.', status=409)
        existing = round.requests.filter(generation=round.generation, nonce=nonce).first()
        if existing:
            return redirect('landing:chip_receipt', token=existing.pk)
        if not round.enabled:
            return invalid(request, mode, 'Talep formu şu anda kapalı.', status=403)
        if round.requested_units + quantity > CAPACITY:
            return invalid(request, mode, f'Bu dönemde kalan talep adedi: {CAPACITY - round.requested_units}.', status=409)
        first = round.requested_units + 1
        item = round.requests.create(generation=round.generation, nonce=nonce, email=email, quantity=quantity,
            start_position=first, provisional_percent=sum((share_percent(n) for n in range(first, first+quantity)), Decimal('0')))
        round.requested_units += quantity
        round.save(update_fields=['requested_units'])
        transaction.on_commit(lambda: notify(item.pk), robust=True)
    return redirect('landing:chip_receipt', token=item.pk)


def item_data(item):
    if item.generation != item.round.generation:
        return {'archived': True}
    rows = []
    previous = item.round.requests.filter(generation=item.generation, start_position__lte=item.start_position).order_by('start_position')
    for other in previous:
        for position in range(other.start_position, other.end_position + 1):
            rows.append({'position': position, 'email': item.email if other.pk == item.pk else mask_email(other.email),
                'share': percent_text(share_percent(position)), 'self': other.pk == item.pk})
    return {'archived': False, 'quantity': item.quantity, 'first': item.start_position, 'last': item.end_position,
        'share': percent_text(item.provisional_percent), 'email': item.email, 'rows': rows, 'payment_verified': False}


@never_cache
@require_GET
def receipt(request, token):
    item = get_object_or_404(ChipParticipationRequest.objects.select_related('round'), pk=token)
    return protected(render(request, 'landing/chip_request_receipt.html', {'item': item, 'data': item_data(item),
        'back_url': reverse('landing:chip_test' if item.round.mode == 'test' else 'landing:chip_page')}))


@never_cache
@require_GET
def status(request, token):
    item = get_object_or_404(ChipParticipationRequest.objects.select_related('round'), pk=token)
    return protected(JsonResponse(item_data(item)))


@require_http_methods(['GET', 'POST'])
def removed_payment(request, mode):
    return protected(JsonResponse({'message': 'Bu sayfadan ödeme alma işlemi kaldırıldı.'}, status=410))


def notify(pk):
    from django.core.mail import send_mail, get_connection
    from skool.services import send_telegram
    from skool.models import NotificationLog
    with transaction.atomic():
        item = ChipParticipationRequest.objects.select_for_update().select_related('round').get(pk=pk)
        if item.generation != item.round.generation:
            return
        label = '[TEST] ' if item.round.mode == 'test' else ''
        rank = str(item.start_position) if item.quantity == 1 else f'{item.start_position}–{item.end_position}'
        link = settings.PUBLIC_BASE_URL.rstrip('/') + reverse('landing:chip_receipt', args=[item.pk])
        text = (f'{label}Siberkobi katılım talebin alındı.\n\nE-posta: {item.email}\nÇip adedi: {item.quantity}\n'
            f'Talep sıran: {rank}\nHesaplanan geçici pay: %{percent_text(item.provisional_percent)}\n\n'
            'Bu kayıt ödeme onayı değildir. Talep sırası ödeme sırası değildir; kesin ortaklık veya kâr payı hakkı oluşturmaz.\n\n'
            f'Talebini gör: {link}')
        errors = []
        if not item.email_sent_at:
            try:
                if send_mail(label + 'Siberkobi • Katılım talebin', text, settings.DEFAULT_FROM_EMAIL,
                        [item.email], connection=get_connection(timeout=10)) != 1:
                    raise RuntimeError
                item.email_sent_at = timezone.now()
            except Exception:
                errors.append('E-posta bekliyor')
        if not item.telegram_sent_at:
            key = f'chip-request-{item.pk}'
            try:
                sent = send_telegram(f'{label}📝 Siberkobi katılım talebi — ÖDEME DOĞRULANMADI\n{item.email}\n'
                    f'Adet: {item.quantity}\nTalep sırası: {rank}\nGeçici pay: %{percent_text(item.provisional_percent)}', idempotency_key=key)
                if not sent and not NotificationLog.objects.filter(key=key, detail__status='sent').exists():
                    raise RuntimeError
                item.telegram_sent_at = timezone.now()
            except Exception:
                errors.append('Telegram bekliyor')
        item.notification_error = '; '.join(errors)
        item.save(update_fields=['email_sent_at', 'telegram_sent_at', 'notification_error'])


def archive_round(mode):
    with transaction.atomic():
        round = ChipRequestRound.objects.select_for_update().get(mode=mode)
        round.generation = uuid.uuid4()
        round.requested_units = 0
        round.save(update_fields=['generation', 'requested_units'])
