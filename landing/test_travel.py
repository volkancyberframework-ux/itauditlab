import hashlib
import hmac
import json
import time
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import TravelPayment, TravelRegistration
from .travel import next_monday, notify_registration


@override_settings(
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
    STRIPE_SECRET_KEY='sk_test_placeholder', TRAVEL_BOOTCAMP_WEBHOOK_SECRET='whsec_test',
)
class TravelTests(TestCase):
    def event(self, **overrides):
        session = {
            'id': 'cs_test_travel', 'object': 'checkout.session', 'mode': 'payment',
            'metadata': {'product': 'travel_bootcamp'}, 'payment_status': 'paid',
            'amount_total': 24900, 'currency': 'usd', 'payment_intent': 'pi_travel',
            'customer': 'cus_travel',
            'customer_details': {'email': 'ADA@example.com', 'name': 'Ada Lovelace', 'phone': '+905550000000'},
        }
        session.update(overrides)
        return {'id': 'evt_travel', 'object': 'event', 'type': 'checkout.session.completed',
                'created': 1791100800, 'livemode': False, 'data': {'object': session}}

    def deliver(self, event=None, signature=None, timestamp=None):
        body = json.dumps(event or self.event())
        timestamp = timestamp or int(time.time())
        digest = hmac.new(b'whsec_test', f'{timestamp}.{body}'.encode(), hashlib.sha256).hexdigest()
        return self.client.post(reverse('landing:travel_webhook'), body, content_type='application/json',
                                HTTP_STRIPE_SIGNATURE=signature or f't={timestamp},v1={digest}')

    def test_page_has_six_sections_and_consistent_ctas(self):
        response = self.client.get(reverse('landing:travel_bootcamp'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().count('<section '), 6)
        self.assertContains(response, 'Travel Bootcamp’e Katıl — $249', count=4)
        self.assertContains(response, 'Ömür boyu video erişimi')
        self.assertNotContains(response, 'sk_test_placeholder')
        self.assertNotContains(response, 'whsec_test')

    def test_checkout_price_cannot_be_changed_by_client(self):
        with patch('landing.travel.stripe.checkout.Session.create', return_value=SimpleNamespace(url='https://checkout.stripe.com/c/pay/cs_test')) as create:
            response = self.client.post(reverse('landing:travel_checkout'), {'amount': 1, 'currency': 'try'})
        self.assertEqual(response.status_code, 303)
        args = create.call_args.kwargs
        self.assertEqual(args['line_items'][0]['price_data']['unit_amount'], 24900)
        self.assertEqual(args['line_items'][0]['price_data']['currency'], 'usd')
        self.assertEqual(args['metadata']['product'], 'travel_bootcamp')
        self.assertIn('{CHECKOUT_SESSION_ID}', args['success_url'])
        self.assertEqual(TravelRegistration.objects.count(), 0)

    def test_checkout_json_and_csrf(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post(reverse('landing:travel_checkout')).status_code, 403)
        with patch('landing.travel.stripe.checkout.Session.create', return_value=SimpleNamespace(url='https://checkout.stripe.com/test')):
            response = self.client.post(reverse('landing:travel_checkout'), HTTP_ACCEPT='application/json')
        self.assertEqual(response.json()['url'], 'https://checkout.stripe.com/test')

    @override_settings(TRAVEL_BOOTCAMP_WEBHOOK_SECRET='')
    def test_checkout_closed_without_webhook_configuration(self):
        with patch('landing.travel.stripe.checkout.Session.create') as create:
            self.assertEqual(self.client.post(reverse('landing:travel_checkout')).status_code, 503)
            create.assert_not_called()

    def test_valid_webhook_persists_required_fields(self):
        self.assertEqual(self.deliver().status_code, 200)
        record = TravelRegistration.objects.get()
        payment = TravelPayment.objects.get()
        self.assertEqual((record.name, record.email, record.phone), ('Ada Lovelace', 'ada@example.com', '+905550000000'))
        self.assertEqual(record.payment_status, 'paid')
        self.assertEqual(record.product, 'Travel Bootcamp')
        self.assertEqual(record.starts_on, date(2026, 10, 5))
        self.assertEqual((payment.amount_minor, payment.currency), (24900, 'usd'))
        self.assertEqual((payment.customer_id, payment.payment_intent_id), ('cus_travel', 'pi_travel'))

    def test_signature_and_replay_age_rejected(self):
        self.assertEqual(self.deliver(signature='t=1,v1=invalid').status_code, 400)
        self.assertEqual(self.deliver(timestamp=int(time.time()) - 600).status_code, 400)
        self.assertEqual(TravelRegistration.objects.count(), 0)

    def test_unpaid_other_products_and_other_events_do_not_enroll(self):
        for fields in ({'payment_status': 'unpaid'}, {'metadata': {'product': 'cisa'}}):
            self.assertEqual(self.deliver(self.event(**fields)).status_code, 200)
        event = self.event()
        event['type'] = 'payment_intent.succeeded'
        self.assertEqual(self.deliver(event).status_code, 200)
        self.assertEqual(TravelRegistration.objects.count(), 0)

    def test_invalid_amount_currency_email_or_mode_rejected(self):
        for fields in ({'amount_total': 1}, {'currency': 'try'}, {'mode': 'subscription'},
                       {'customer_details': {'email': 'invalid'}}, {'payment_intent': None}):
            self.assertEqual(self.deliver(self.event(**fields)).status_code, 400)
        self.assertEqual(TravelRegistration.objects.count(), 0)

    @override_settings(STRIPE_SECRET_KEY='sk_live_placeholder')
    def test_test_event_cannot_enroll_on_live_service(self):
        self.assertEqual(self.deliver().status_code, 400)
        self.assertEqual(TravelRegistration.objects.count(), 0)

    def test_repeated_events_and_case_variant_email_deduplicated(self):
        self.deliver()
        self.deliver()
        later = self.event()
        later['type'] = 'checkout.session.async_payment_succeeded'
        later['id'] = 'evt_async'
        self.deliver(later)
        second = self.event(id='cs_test_second', payment_intent='pi_second', customer_details={'email': 'ada@EXAMPLE.com'})
        second['id'] = 'evt_second'
        self.deliver(second)
        self.assertEqual(TravelRegistration.objects.count(), 1)
        self.assertEqual(TravelPayment.objects.count(), 2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            TravelRegistration.objects.create(email='ADA@EXAMPLE.COM', registered_at=datetime.now(timezone.utc), starts_on=date(2026, 10, 5))

    def test_delayed_payment_only_enrolls_when_paid(self):
        self.deliver(self.event(payment_status='unpaid'))
        event = self.event()
        event['id'] = 'evt_delayed'
        event['type'] = 'checkout.session.async_payment_succeeded'
        self.assertEqual(self.deliver(event).status_code, 200)
        self.assertEqual(TravelRegistration.objects.count(), 1)

    def test_duplicate_payment_intent_does_not_create_another_participant(self):
        self.deliver()
        event = self.event(id='cs_test_other', customer_details={'email': 'other@example.com'})
        event['id'] = 'evt_other'
        self.assertEqual(self.deliver(event).status_code, 200)
        self.assertEqual(TravelRegistration.objects.count(), 1)
        self.assertEqual(TravelPayment.objects.count(), 1)

    def test_repeated_webhook_sends_only_one_notification(self):
        with patch('skool.services.send_telegram', return_value=True) as notify:
            with self.captureOnCommitCallbacks(execute=True):
                self.deliver()
            with self.captureOnCommitCallbacks(execute=True):
                self.deliver()
        self.assertEqual(notify.call_count, 1)

    def test_telegram_failure_does_not_rollback_and_can_retry(self):
        with patch('skool.services.send_telegram', side_effect=RuntimeError('network unavailable')):
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.deliver().status_code, 200)
        record = TravelRegistration.objects.get()
        self.assertIsNone(record.telegram_sent_at)
        with patch('skool.services.send_telegram', return_value=True) as notify:
            notify_registration(record.pk)
            notify_registration(record.pk)
        self.assertEqual(notify.call_count, 1)
        record.refresh_from_db()
        self.assertIsNotNone(record.telegram_sent_at)
        self.assertIn('YENİ TRAVEL BOOTCAMP KAYDI', notify.call_args.args[0])

    def test_database_failure_propagates_for_stripe_retry(self):
        with patch('landing.travel.TravelPayment.objects.get_or_create', side_effect=IntegrityError):
            with self.assertRaises(IntegrityError):
                self.deliver()
        self.assertEqual(TravelRegistration.objects.count(), 0)

    def test_success_and_status_are_read_only_and_private(self):
        for url in ('landing:travel_success', 'landing:travel_status'):
            self.client.get(reverse(url), {'session_id': 'cs_forged', 'payment_status': 'paid'})
        self.assertEqual(TravelRegistration.objects.count(), 0)
        self.deliver()
        result = self.client.get(reverse('landing:travel_success'), {'session_id': 'cs_test_travel'})
        self.assertContains(result, 'Hoş Geldin!')
        self.assertContains(result, '5 Ekim 2026 Pazartesi')
        self.assertNotContains(result, 'ada@example.com')
        self.assertIn('no-store', result['Cache-Control'])
        self.assertEqual(result['Referrer-Policy'], 'no-referrer')
        self.assertEqual(self.client.get(reverse('landing:travel_status'), {'session_id': 'cs_test_travel'}).json(), {'confirmed': True})

    def test_monday_rule_uses_istanbul_and_strictly_following_monday(self):
        self.assertEqual(next_monday(datetime(2026, 10, 4, 20, 59, tzinfo=timezone.utc)), date(2026, 10, 5))
        self.assertEqual(next_monday(datetime(2026, 10, 4, 21, 0, tzinfo=timezone.utc)), date(2026, 10, 12))
        self.assertEqual(next_monday(datetime(2026, 12, 31, 12, tzinfo=timezone.utc)), date(2027, 1, 4))
