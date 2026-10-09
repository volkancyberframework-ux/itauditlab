from copy import copy
from types import SimpleNamespace
from unittest.mock import patch
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import PermissionDenied, ValidationError
from appstoreserverlibrary.models.Environment import Environment
from .apple_billing import apply_purchase, decode, verifier
from .models import BillingIdentity, Subscription
from .views import premium


class AppleBillingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='apple', email='apple@example.com',
            password='example-pass', is_mobile=True, mobile_email_verified=True)
        self.identity = BillingIdentity.objects.create(user=self.user)
        now = timezone.now()
        self.payload = SimpleNamespace(productId='grcustasi_premium_monthly', bundleId='com.grcustasi.grcUstasi',
            type='Auto-Renewable Subscription', originalTransactionId='10001', transactionId='10002',
            appAccountToken=str(self.identity.pk), purchaseDate=int(now.timestamp()*1000),
            signedDate=int(now.timestamp()*1000), expiresDate=int((now + timedelta(days=30)).timestamp()*1000),
            revocationDate=None, environment=Environment.PRODUCTION)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_valid_purchase_is_bound_and_idempotent(self):
        apply_purchase(self.payload, self.user)
        apply_purchase(self.payload, self.user)
        self.assertTrue(premium(self.user))
        self.assertEqual(Subscription.objects.count(), 1)
        self.assertFalse(self.user.mobile_paid)

    def test_no_client_flag_or_forged_jws_can_grant_access(self):
        response = self.client.post('/api/mobile/v1/payments/apple/verify/', {'premium': True}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post('/api/mobile/v1/payments/apple/verify/',
            {'signed_transaction': 'a.' + 'b'*110 + '.c'}, format='json').status_code, 400)
        self.assertFalse(premium(self.user))

    def test_verify_endpoint_and_profile_access(self):
        with patch('mobile_api.apple_billing.decode', return_value=(self.payload, None)):
            response = self.client.post('/api/mobile/v1/payments/apple/verify/', {'signed_transaction': 'fixture'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['premium'])
        self.assertTrue(self.client.get('/api/mobile/v1/profile/').data['premium'])

    def test_other_account_cannot_restore_purchase(self):
        other = get_user_model().objects.create_user(username='other')
        with self.assertRaises(PermissionDenied): apply_purchase(self.payload, other)
        self.assertFalse(Subscription.objects.exists())

    def test_product_account_type_and_bundle_validation(self):
        for field, value in [('productId', 'wrong'), ('bundleId', 'wrong'), ('appAccountToken', None),
                             ('type', 'Consumable'), ('expiresDate', None)]:
            payload = copy(self.payload); setattr(payload, field, value)
            with self.assertRaises(ValidationError): apply_purchase(payload, self.user)
        self.assertFalse(Subscription.objects.exists())

    def test_expired_transaction_does_not_unlock(self):
        self.payload.expiresDate = int((timezone.now()-timedelta(days=1)).timestamp()*1000)
        apply_purchase(self.payload, self.user)
        self.assertFalse(premium(self.user))

    def test_refund_and_old_replay_do_not_unlock(self):
        original = copy(self.payload)
        apply_purchase(original, self.user)
        self.payload.revocationDate = self.payload.signedDate + 1000
        self.payload.signedDate += 1000
        apply_purchase(self.payload)
        apply_purchase(original, self.user)
        self.assertFalse(premium(self.user))
        self.assertEqual(Subscription.objects.get().status, 'cancelled')

    def test_renewal_advances_expiry_old_delivery_cannot_shorten(self):
        original = copy(self.payload)
        apply_purchase(original, self.user)
        self.payload.transactionId = '10003'
        self.payload.signedDate += 2000
        self.payload.expiresDate += 30*86400000
        apply_purchase(self.payload)
        apply_purchase(original, self.user)
        self.assertEqual(int(Subscription.objects.get().expires_at.timestamp()*1000), self.payload.expiresDate)
        self.assertEqual(Subscription.objects.count(), 1)

    def test_signed_notification_applies_refund_and_is_idempotent(self):
        apply_purchase(self.payload, self.user)
        self.payload.revocationDate = self.payload.signedDate + 1000
        self.payload.signedDate += 1000
        verifier_mock = SimpleNamespace(verify_and_decode_signed_transaction=lambda _: self.payload)
        notification = SimpleNamespace(data=SimpleNamespace(signedTransactionInfo='signed'))
        anonymous = APIClient()
        with patch('mobile_api.apple_billing.decode', return_value=(notification, verifier_mock)):
            for _ in range(2):
                self.assertEqual(anonymous.post('/api/mobile/v1/payments/apple/notifications/', {'signedPayload':'fixture'}, format='json').status_code, 200)
        self.assertFalse(premium(self.user))

    def test_unsigned_notification_rejected_and_deleted_account_not_recreated(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.post('/api/mobile/v1/payments/apple/notifications/', {'premium':True}, format='json').status_code, 400)
        self.identity.delete()
        self.assertIsNone(apply_purchase(self.payload))
        self.assertFalse(Subscription.objects.exists())

    def test_sandbox_can_be_disabled_and_environment_is_not_client_chosen(self):
        with override_settings(APPLE_ALLOW_SANDBOX=False), patch('mobile_api.apple_billing.verifier') as check:
            from appstoreserverlibrary.signed_data_verifier import VerificationException, VerificationStatus
            check.return_value.verify_and_decode_signed_transaction.side_effect = VerificationException(VerificationStatus.INVALID_ENVIRONMENT)
            with self.assertRaises(ValidationError): decode('x' * 200)
            self.assertEqual(check.call_count, 1)
            check.assert_called_with(Environment.PRODUCTION)

    def test_public_roots_load_and_tampered_signature_is_rejected(self):
        self.assertIsNotNone(verifier(Environment.PRODUCTION))
        with self.assertRaises(ValidationError): decode('x' * 200)

    def test_transient_certificate_check_returns_retryable_503(self):
        from appstoreserverlibrary.signed_data_verifier import VerificationException, VerificationStatus
        with patch('mobile_api.apple_billing.verifier') as check:
            check.return_value.verify_and_decode_signed_transaction.side_effect = VerificationException(VerificationStatus.RETRYABLE_VERIFICATION_FAILURE)
            response = self.client.post('/api/mobile/v1/payments/apple/verify/', {'signed_transaction':'x'*200}, format='json')
        self.assertEqual(response.status_code,503)
        self.assertFalse(Subscription.objects.exists())
