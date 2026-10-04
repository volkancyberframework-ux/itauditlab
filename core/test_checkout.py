from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, RequestFactory, override_settings

from core import views


@override_settings(STRIPE_SECRET_KEY='sk_test_placeholder', TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_ID='')
class CheckoutCompatibilityTests(SimpleTestCase):
    def request(self):
        request = RequestFactory().post('/')
        request.user = AnonymousUser()
        return request

    def test_memberships_use_dashboard_payment_methods(self):
        for plan in ('monthly', 'yearly'):
            with self.subTest(plan=plan), patch('stripe.checkout.Session.create') as create:
                create.return_value.url = 'https://checkout.stripe.com/session'
                response = views.create_membership_checkout(self.request(), plan)
                self.assertEqual(response.status_code, 302)
                self.assertNotIn('payment_method_types', create.call_args.kwargs)
                self.assertEqual(create.call_args.kwargs['mode'], 'subscription')

    def test_corporate_checkout_uses_dashboard_payment_methods(self):
        with patch('stripe.checkout.Session.create') as create:
            create.return_value.url = 'https://checkout.stripe.com/session'
            response = views.corporate_assurance_checkout(self.request())
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('payment_method_types', create.call_args.kwargs)

    def test_legacy_bootcamp_uses_dashboard_payment_methods(self):
        product = SimpleNamespace(title='Bootcamp', description='Training', currency='try', price=Decimal('100'))
        with patch('core.views.get_object_or_404', return_value=product), patch('core.views.BootcampInterest.objects.create'), patch('stripe.checkout.Session.create') as create:
            create.return_value.url = 'https://checkout.stripe.com/session'
            response = views.bootcamp_checkout(self.request(), 'bootcamp')
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('payment_method_types', create.call_args.kwargs)
        self.assertEqual(create.call_args.kwargs['line_items'][0]['price_data']['unit_amount'], 10000)
