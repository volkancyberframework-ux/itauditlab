import uuid
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, Client
from django.urls import reverse
from .chip import share_percent
from .chip_models import ChipCampaign, ChipPurchase, ChipRequestRound, ChipParticipationRequest
from .chip_requests import archive_round, notify


class ChipRequestTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.round = ChipRequestRound.objects.get(mode='live')
        self.url = reverse('landing:chip_page')
        self.submit_url = reverse('landing:chip_request_submit', args=['live'])

    def form(self, email='volkan@example.com', quantity=1):
        self.client.get(self.url)
        self.round.refresh_from_db()
        return {'email': email, 'quantity': str(quantity), 'nonce': self.client.session['chip_request_nonces'][-1], 'generation': str(self.round.generation)}

    def submit(self, email='volkan@example.com', quantity=1):
        return self.client.post(self.submit_url, self.form(email, quantity))

    def test_page_has_email_quantity_and_no_checkout(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Ödeme sırasında kullandığın e-posta adresini gir.')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="quantity"')
        self.assertContains(response, 'ödeme doğrulaması yapmaz')
        self.assertNotContains(response, '399')
        self.assertNotContains(response, 'Stripe')
        self.assertNotContains(response, '/checkout/')

    def test_removed_payment_endpoints_never_contact_stripe(self):
        with patch('stripe.checkout.Session.create') as create:
            for route in ('chip_checkout', 'chip_webhook'):
                self.assertEqual(self.client.post(reverse('landing:' + route, args=['live'])).status_code, 410)
            create.assert_not_called()

    def test_request_immediately_shows_provisional_rank_without_payment_record(self):
        response = self.submit(' VOLKAN@example.com ')
        self.assertEqual(response.status_code, 302)
        item = ChipParticipationRequest.objects.get()
        self.assertEqual(item.email, 'volkan@example.com')
        self.assertEqual(item.start_position, 1)
        self.assertEqual(item.provisional_percent, Decimal('.5'))
        response = self.client.get(response['Location'])
        self.assertContains(response, 'Ödeme doğrulanmadı')
        self.assertContains(response, '%0,50000000')
        self.assertEqual(ChipPurchase.objects.count(), 0)
        self.assertEqual(ChipCampaign.objects.get(mode='live').confirmed_count, 0)

    def test_multiple_units_and_multiple_requests_same_email(self):
        self.submit(quantity=2)
        response = self.submit(quantity=2)
        rows = list(ChipParticipationRequest.objects.order_by('created_at'))
        self.assertEqual((rows[0].start_position, rows[0].end_position), (1, 2))
        self.assertEqual(rows[0].provisional_percent, Decimal('.75'))
        self.assertEqual((rows[1].start_position, rows[1].end_position), (3, 4))
        self.assertAlmostEqual(rows[1].provisional_percent, share_percent(3)+share_percent(4), places=14)
        self.assertContains(self.client.get(response['Location']), '2 ÇİP')
        self.round.refresh_from_db(); self.assertEqual(self.round.requested_units, 4)

    def test_duplicate_submit_is_idempotent_and_notifies_once(self):
        form = self.form()
        with patch('skool.services.send_telegram', return_value=True) as telegram:
            with self.captureOnCommitCallbacks(execute=True):
                first = self.client.post(self.submit_url, form)
                second = self.client.post(self.submit_url, form)
        self.assertEqual(first['Location'], second['Location'])
        self.assertEqual(ChipParticipationRequest.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(telegram.call_count, 1)
        self.assertIn('ÖDEME DOĞRULANMADI', telegram.call_args.args[0])
        self.assertIn('ödeme onayı değildir', mail.outbox[0].body)

    def test_capacity_and_exact_formula_total(self):
        response = self.submit(quantity=43)
        self.assertEqual(response.status_code, 302)
        item = ChipParticipationRequest.objects.get()
        self.assertEqual(item.provisional_percent, Decimal('2'))
        self.assertEqual(self.submit().status_code, 409)
        self.assertEqual(sum(share_percent(n) for n in range(1, 44)), Decimal('2'))
        self.assertEqual(f'{share_percent(4):.8f}', '0.10150026')

    def test_invalid_input_and_unissued_nonce_do_not_consume_counter(self):
        for email,qty in [('invalid', 1), ('test@example.com', 0), ('test@example.com', -1), ('test@example.com', 44), ('test@example.com', 'a')]:
            self.assertEqual(self.submit(email, qty).status_code, 400)
        form = self.form(); form['nonce'] = str(uuid.uuid4())
        self.assertEqual(self.client.post(self.submit_url, form).status_code, 400)
        self.assertEqual(ChipParticipationRequest.objects.count(), 0)
        self.round.refresh_from_db(); self.assertEqual(self.round.requested_units, 0)

    def test_other_people_masked_and_later_requests_not_exposed(self):
        self.submit('earlier@example.com')
        own = self.submit('own@example.com')
        self.submit('later@example.com')
        response = self.client.get(own['Location'])
        self.assertContains(response, 'own@example.com')
        self.assertContains(response, 'e***@e***.com')
        self.assertNotContains(response, 'earlier@example.com')
        self.assertNotContains(response, 'later@example.com')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(response['Referrer-Policy'], 'no-referrer')

    def test_archiving_keeps_requests_and_payment_counter_unchanged(self):
        response = self.submit()
        old_form = self.form()
        archive_round('live')
        self.round.refresh_from_db(); self.assertEqual(self.round.requested_units, 0)
        self.assertEqual(ChipParticipationRequest.objects.count(), 1)
        self.assertContains(self.client.get(response['Location']), 'arşivlendi')
        self.assertEqual(self.client.post(self.submit_url, old_form).status_code, 400)
        self.assertEqual(self.submit().status_code, 302)
        self.assertEqual(ChipParticipationRequest.objects.count(), 2)
        self.assertEqual(ChipCampaign.objects.get(mode='live').confirmed_count, 0)

    def test_closed_round_and_csrf(self):
        self.round.enabled = False; self.round.save()
        self.assertEqual(self.submit().status_code, 403)
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(self.submit_url, self.form()).status_code, 403)

    def test_failed_mail_retries_without_repeating_telegram(self):
        self.submit(); item = ChipParticipationRequest.objects.get()
        with patch('django.core.mail.send_mail', side_effect=OSError), patch('skool.services.send_telegram', return_value=True):
            notify(item.pk)
        item.refresh_from_db(); self.assertIsNone(item.email_sent_at); self.assertIsNotNone(item.telegram_sent_at)
        with patch('skool.services.send_telegram') as telegram:
            call_command('reconcile_siberkobi_chips')
            telegram.assert_not_called()
        item.refresh_from_db(); self.assertIsNotNone(item.email_sent_at)

    def test_closed_session_cannot_read_others_by_email(self):
        response = self.submit()
        other = Client()
        response = other.get(self.url + '?email=volkan@example.com')
        self.assertNotContains(response, 'volkan@example.com')
        self.assertNotContains(response, '%0,50000000')

    def test_database_guards_position_and_capacity(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ChipRequestRound.objects.filter(pk=self.round.pk).update(requested_units=44)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.round.requests.create(generation=self.round.generation, nonce=uuid.uuid4(), email='a@example.com',
                quantity=2, start_position=43, provisional_percent='.1')

    def test_archive_admin_is_superuser_only(self):
        user = get_user_model().objects.create_user(username='request-staff', is_staff=True)
        self.client.force_login(user)
        route = reverse('admin:chip_request_archive')
        self.assertEqual(self.client.get(route).status_code, 403)
        user.is_superuser = True; user.save()
        self.assertEqual(self.client.get(route).status_code, 200)
