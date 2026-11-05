from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
import stripe
from landing.chip import key_for, fulfil, notify, PRODUCT, stripe_data
from landing.chip_models import ChipCampaign, ChipPurchase


class Command(BaseCommand):
    help = 'Siberkobi bekleyen ödemelerini Stripe ile doğrular; bildirimleri yeniden dener. Yeni tahsilat başlatmaz.'

    def handle(self, *args, **options):
        checked = 0
        pending = ChipPurchase.objects.select_related('campaign').filter(state='pending', generation=F('campaign__generation'))
        for purchase in pending.iterator():
            key = key_for(purchase.campaign.mode)
            if not key:
                continue
            try:
                if purchase.stripe_session:
                    session = stripe_data(stripe.checkout.Session.retrieve(purchase.stripe_session, api_key=key))
                else:
                    # Recover an accepted create request whose HTTP response was lost.
                    # Never free a reservation just because a local timer expired.
                    if timezone.now() < purchase.expires_at + timedelta(minutes=5):
                        continue
                    session = next((stripe_data(s) for s in stripe.checkout.Session.list(api_key=key, limit=100,
                        created={'gte': int(purchase.created_at.timestamp()) - 60,
                                 'lte': int(purchase.expires_at.timestamp()) + 60}).auto_paging_iter()
                        if (stripe_data(s).get('metadata') or {}).get('chip_id') == str(purchase.pk)
                        and (stripe_data(s).get('metadata') or {}).get('product') == PRODUCT
                        and stripe_data(s).get('client_reference_id') == str(purchase.pk)), None)
                    if session:
                        ChipPurchase.objects.filter(pk=purchase.pk, stripe_session=None).update(stripe_session=session['id'])
                if session and session.get('payment_status') == 'paid':
                    fulfil(session)
                elif session is None or session.get('status') == 'expired':
                    with transaction.atomic():
                        ChipCampaign.objects.select_for_update().get(pk=purchase.campaign_id)
                        ChipPurchase.objects.filter(pk=purchase.pk, state='pending').update(state='expired')
                checked += 1
            except (stripe.StripeError, ValidationError):
                self.stderr.write(f'Ödeme kontrolü bekliyor: {purchase.pk}')
        rows = ChipPurchase.objects.filter(state='paid', generation=F('campaign__generation')).filter(Q(email_sent_at=None) | Q(telegram_sent_at=None))
        for pk in rows.values_list('pk', flat=True):
            notify(pk)
        self.stdout.write(f'Kontrol edilen ödeme: {checked}; bekleyen bildirim: {rows.count()}')
