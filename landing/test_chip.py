import hashlib
import hmac
import json
import time
import stripe
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from .chip import share_percent, fulfil, PRODUCT, TERMS_VERSION, reset_test, notify, purchase_data
from .chip_models import ChipCampaign, ChipPurchase


@override_settings(CHIP_STRIPE_TEST_KEY='sk_test_demo', CHIP_STRIPE_TEST_WEBHOOK_SECRET='whsec_test', CHIP_LIVE_PAYMENTS_ENABLED=False)
class ChipTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.campaign = ChipCampaign.objects.get(mode='test')
        self.campaign.enabled = True
        self.campaign.save()

    def purchase(self, campaign=None):
        campaign = campaign or self.campaign
        return ChipPurchase.objects.create(campaign=campaign, generation=campaign.generation,
            expires_at=timezone.now() + timedelta(minutes=31))

    def payment(self, purchase, **overrides):
        data = {'id': 'cs_test_' + purchase.pk.hex, 'payment_intent': 'pi_' + purchase.pk.hex,
            'mode': 'payment', 'livemode': purchase.campaign.mode == 'live', 'payment_status': 'paid',
            'amount_total': 39900, 'currency': 'eur', 'client_reference_id': str(purchase.pk),
            'metadata': {'product': PRODUCT, 'chip_id': str(purchase.pk), 'generation': str(purchase.generation)},
            'customer_details': {'email': 'payer@example.com', 'name': 'Ayşe Örnek'}}
        data.update(overrides)
        return data

    def webhook(self, payment, mode='test', signed=True, kind='checkout.session.completed'):
        body = json.dumps({'id': 'evt_test', 'livemode': False, 'type': kind, 'data': {'object': payment}}).encode()
        stamp = int(time.time())
        signature = hmac.new(b'whsec_test', str(stamp).encode() + b'.' + body, hashlib.sha256).hexdigest()
        return self.client.post(reverse('landing:chip_webhook', args=[mode]), body, content_type='application/json',
            HTTP_STRIPE_SIGNATURE=f't={stamp},v1={signature}' if signed else 'invalid')

    def test_formula_matches_image_and_totals_two_percent(self):
        self.assertEqual(share_percent(1), Decimal('.5'))
        self.assertEqual(share_percent(2), Decimal('.25'))
        self.assertEqual(share_percent(3), Decimal('.25'))
        self.assertEqual(f'{share_percent(4):.8f}', '0.10150026')
        self.assertEqual(f'{share_percent(43):.8f}', '0.00166696')
        self.assertEqual(sum(share_percent(n) for n in range(1, 44)), Decimal('2'))
        for n in range(5, 43):
            self.assertLess(abs(share_percent(n) - share_percent(n-1) * Decimal('.9')), Decimal('1e-20'))

    def test_checkout_price_metadata_and_disclosure_are_server_owned(self):
        with patch('landing.chip.stripe.checkout.Session.create', return_value=stripe.checkout.Session.construct_from({'id': 'cs_test_checkout', 'url': 'https://checkout.stripe.com/test'}, 'sk_test_demo')) as create:
            response = self.client.post(reverse('landing:chip_checkout', args=['test']), {'acknowledge': TERMS_VERSION, 'amount': '1'})
        self.assertEqual(response.status_code, 303)
        args = create.call_args.kwargs
        self.assertEqual(args['line_items'][0]['price_data']['unit_amount'], 39900)
        self.assertEqual(args['line_items'][0]['price_data']['currency'], 'eur')
        self.assertIn('hisse/kâr payı', args['line_items'][0]['price_data']['product_data']['description'])
        self.assertEqual(args['payment_method_types'], ['card'])
        self.assertEqual(args['metadata']['product'], PRODUCT)
        self.assertEqual(self.campaign.purchases.count(), 1)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.confirmed_count, 0)

    def test_closed_live_and_unacknowledged_payments_do_not_create_sessions(self):
        live = ChipCampaign.objects.get(mode='live'); live.enabled = True; live.save()
        with patch('landing.chip.stripe.checkout.Session.create') as create:
            self.assertEqual(self.client.post(reverse('landing:chip_checkout', args=['live']), {'acknowledge': TERMS_VERSION}).status_code, 403)
            self.assertEqual(self.client.post(reverse('landing:chip_checkout', args=['test'])).status_code, 400)
            self.campaign.enabled = False; self.campaign.save()
            self.assertEqual(self.client.post(reverse('landing:chip_checkout', args=['test']), {'acknowledge': TERMS_VERSION}).status_code, 403)
            create.assert_not_called()

    def test_payment_validates_amount_currency_mode_and_status(self):
        p = self.purchase()
        self.assertIsNone(fulfil(self.payment(p, payment_status='unpaid')))
        for overrides in ({'amount_total': 39800}, {'currency': 'usd'}, {'livemode': True}, {'client_reference_id': 'other'}, {'payment_intent': ''}):
            with self.subTest(overrides=overrides), self.assertRaisesMessage(Exception, 'Invalid payment'):
                fulfil(self.payment(p, **overrides))
        p.refresh_from_db(); self.assertIsNone(p.position)

    def test_signed_duplicate_webhook_allocates_and_notifies_once(self):
        p = self.purchase(); payment = self.payment(p)
        self.assertEqual(self.webhook(payment, signed=False).status_code, 400)
        with patch('skool.services.send_telegram', return_value=True) as telegram:
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.webhook(payment).status_code, 200)
                self.assertEqual(self.webhook(payment).status_code, 200)
        p.refresh_from_db(); self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.confirmed_count, 1)
        self.assertEqual(p.position, 1)
        self.assertEqual(p.share_percent, Decimal('.5'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('[TEST', mail.outbox[0].subject)
        self.assertIn('payer@example.com', mail.outbox[0].body)
        self.assertIn('Sıra: 1/43', telegram.call_args.args[0])
        self.assertEqual(telegram.call_count, 1)

    def test_capacity_reservations_block_44th_checkout(self):
        for _ in range(43): self.purchase()
        with patch('landing.chip.stripe.checkout.Session.create') as create:
            response = self.client.post(reverse('landing:chip_checkout', args=['test']), {'acknowledge': TERMS_VERSION})
        self.assertEqual(response.status_code, 409); create.assert_not_called()
        for p in self.campaign.purchases.all(): fulfil(self.payment(p))
        self.campaign.refresh_from_db(); self.assertEqual(self.campaign.confirmed_count, 43)
        self.assertAlmostEqual(sum(self.campaign.purchases.values_list('share_percent', flat=True)), Decimal('2'), delta=Decimal('1e-14')) # SQLite stores decimals as floats; production PostgreSQL uses NUMERIC.
        with self.assertRaises(IntegrityError), transaction.atomic():
            ChipCampaign.objects.filter(pk=self.campaign.pk).update(confirmed_count=44)

    def test_private_receipt_masks_predecessors_and_hides_later_payers(self):
        first = self.purchase(); fulfil(self.payment(first, customer_details={'email': 'earlier@example.com', 'name': 'Önceki Kişi'}))
        second = self.purchase(); fulfil(self.payment(second))
        third = self.purchase(); fulfil(self.payment(third, customer_details={'email': 'later@example.com', 'name': 'Sonraki Kişi'}))
        response = self.client.get(reverse('landing:chip_receipt', args=[second.pk]))
        self.assertContains(response, 'payer@example.com')
        self.assertNotContains(response, 'earlier@example.com')
        self.assertNotContains(response, 'Önceki Kişi')
        self.assertNotContains(response, 'later@example.com')
        second.refresh_from_db()
        self.assertEqual(len(purchase_data(second)['participants']), 2)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(response['Referrer-Policy'], 'no-referrer')

    def test_reset_archives_only_test_and_ignores_late_webhooks(self):
        p = self.purchase(); fulfil(self.payment(p))
        pending = self.purchase()
        live = ChipCampaign.objects.get(mode='live')
        live_p = self.purchase(live); fulfil(self.payment(live_p))
        reset_test()
        self.campaign.refresh_from_db(); live.refresh_from_db()
        self.assertEqual(self.campaign.confirmed_count, 0)
        self.assertFalse(self.campaign.enabled)
        self.assertEqual(live.confirmed_count, 1)
        self.assertEqual(ChipPurchase.objects.count(), 3)
        self.assertIsNone(fulfil(self.payment(pending)))
        self.assertEqual(purchase_data(ChipPurchase.objects.select_related('campaign').get(pk=p.pk))['state'], 'archived')
        notify(p.pk); self.assertEqual(len(mail.outbox), 0)

    def test_notifications_retry_independently_after_smtp_failure(self):
        p = self.purchase(); fulfil(self.payment(p))
        with patch('django.core.mail.send_mail', side_effect=OSError), patch('skool.services.send_telegram', return_value=True):
            notify(p.pk)
        p.refresh_from_db(); self.assertIsNone(p.email_sent_at); self.assertIsNotNone(p.telegram_sent_at)
        with patch('skool.services.send_telegram') as telegram:
            notify(p.pk); telegram.assert_not_called()
        p.refresh_from_db(); self.assertIsNotNone(p.email_sent_at)

    def test_success_url_alone_cannot_confirm_payment(self):
        p = self.purchase()
        response = self.client.get(reverse('landing:chip_receipt', args=[p.pk]) + '?paid=1&position=1')
        self.assertEqual(response.status_code, 200)
        p.refresh_from_db(); self.assertIsNone(p.position)

    def test_checkout_requires_csrf_and_reset_requires_superuser(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('landing:chip_checkout', args=['test']), {'acknowledge': TERMS_VERSION}).status_code, 403)
        user = get_user_model().objects.create_user(username='chipstaff', is_staff=True, password='test')
        client.force_login(user)
        route = '/bulamazsinki/landing/chipcampaign/test-reset/'
        self.assertEqual(client.get(route).status_code, 403)
        user.is_superuser = True; user.save()
        self.assertEqual(client.get(route).status_code, 200)
        self.assertEqual(client.post(route, {'confirm': 'TEST SIFIRLA'}).status_code, 403)

    def test_expiry_event_frees_capacity_but_does_not_allocate(self):
        p = self.purchase(); p.stripe_session = self.payment(p)['id']; p.save()
        self.assertEqual(self.webhook(self.payment(p, payment_status='unpaid'), kind='checkout.session.expired').status_code, 200)
        p.refresh_from_db(); self.assertEqual(p.state, 'expired'); self.assertIsNone(p.position)

    def test_poll_verifies_stripe_resource_before_allocating(self):
        p = self.purchase(); p.stripe_session = self.payment(p)['id']; p.save()
        resource = stripe.checkout.Session.construct_from(self.payment(p), 'sk_test_demo')
        with patch('landing.chip.stripe.checkout.Session.retrieve', return_value=resource):
            response = self.client.get(reverse('landing:chip_status', args=[p.pk]))
        self.assertEqual(response.json()['position'], 1)
        self.assertEqual(response.json()['email'], 'payer@example.com')

    def test_pending_checkout_resumes_same_session_after_return(self):
        p = self.purchase(); p.stripe_session = 'cs_test_resume'; p.save()
        session = self.client.session; session['chip_pending_test'] = str(p.pk); session.save()
        resource = stripe.checkout.Session.construct_from({'id': p.stripe_session, 'url': 'https://checkout.stripe.com/resume'}, 'sk_test_demo')
        with patch('landing.chip.stripe.checkout.Session.retrieve', return_value=resource), patch('landing.chip.stripe.checkout.Session.create') as create:
            response = self.client.post(reverse('landing:chip_checkout', args=['test']), {'acknowledge': TERMS_VERSION})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.campaign.purchases.count(), 1)
        create.assert_not_called()

    def test_order_is_verification_order_and_closing_keeps_inflight_payment(self):
        a = self.purchase(); b = self.purchase()
        self.campaign.enabled = False; self.campaign.save()
        self.assertEqual(fulfil(self.payment(b)).position, 1)
        self.assertEqual(fulfil(self.payment(a)).position, 2)
        self.assertEqual(fulfil(self.payment(b)).position, 1)

    def test_reconciliation_only_frees_confirmed_expired_sessions(self):
        p = self.purchase(); p.stripe_session = 'cs_test_pending'; p.save()
        resource = stripe.checkout.Session.construct_from({'id': p.stripe_session, 'status': 'open', 'payment_status': 'unpaid'}, 'sk_test_demo')
        with patch('stripe.checkout.Session.retrieve', return_value=resource):
            call_command('reconcile_siberkobi_chips')
        p.refresh_from_db(); self.assertEqual(p.state, 'pending')
        resource = stripe.checkout.Session.construct_from({'id': p.stripe_session, 'status': 'expired', 'payment_status': 'unpaid'}, 'sk_test_demo')
        with patch('stripe.checkout.Session.retrieve', return_value=resource):
            call_command('reconcile_siberkobi_chips')
        p.refresh_from_db(); self.assertEqual(p.state, 'expired')

    def test_duplicate_position_rejected_by_database(self):
        a = self.purchase(); fulfil(self.payment(a))
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.campaign.purchases.create(generation=self.campaign.generation, position=1,
                expires_at=timezone.now() + timedelta(minutes=31))

    def test_chip_copy_stays_turkish_and_fixed_eur_across_site_locales(self):
        response = self.client.get(reverse('landing:chip_test') + '?lang=en&country=US')
        self.assertContains(response, '399 EUR')
        self.assertContains(response, 'Bir çip fiyatına')
        self.assertNotContains(response, 'site-language.js')
