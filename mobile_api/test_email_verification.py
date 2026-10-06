from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core import mail, signing
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch
from .email_verification import verification_url, SALT
from urllib.parse import urlparse


class VerificationTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.addCleanup(cache.clear)
        self.api = APIClient()
        self.user = get_user_model().objects.create_user(username='verify-demo', email='verify@example.com', password='Strong!Password-917', is_mobile=True, mobile_email_verified=False)

    def test_signup_requires_email_confirmation_and_get_does_not_confirm(self):
        result = self.api.post('/api/mobile/v1/auth/register/', {'name': 'Yeni', 'email': 'new-verify@example.com', 'password': 'Strong!Password-917'}, format='json')
        self.assertEqual(result.status_code, 201)
        self.assertNotIn('access', result.data)
        user = get_user_model().objects.get(email='new-verify@example.com')
        self.assertFalse(user.mobile_email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('https://www.grcustasi.com/api/mobile/v1/auth/verify-email/', mail.outbox[0].body)
        login = {'email': user.email, 'password': 'Strong!Password-917'}
        self.assertEqual(self.api.post('/api/mobile/v1/auth/login/', login).status_code, 403)
        url = urlparse(verification_url(user)).path
        browser = Client(enforce_csrf_checks=True)
        self.assertEqual(browser.get(url).status_code, 200)
        user.refresh_from_db(); self.assertFalse(user.mobile_email_verified)
        self.assertEqual(browser.post(url).status_code, 403)
        token = browser.cookies['csrftoken'].value
        self.assertEqual(browser.post(url, {'csrfmiddlewaretoken': token}).status_code, 200)
        user.refresh_from_db(); self.assertTrue(user.mobile_email_verified)
        self.assertEqual(self.api.post('/api/mobile/v1/auth/login/', login).status_code, 200)
        self.assertEqual(browser.post(url, {'csrfmiddlewaretoken': token}).status_code, 200)

    def test_tampered_expired_changed_email_and_disabled_tokens_fail(self):
        path = urlparse(verification_url(self.user)).path
        self.assertEqual(self.client.post(path.replace('/verify-email/', '/verify-email/x')).status_code, 400)
        with patch('django.core.signing.time.time', return_value=1):
            token = signing.dumps({'id': self.user.pk, 'email': self.user.email}, salt=SALT)
        self.assertEqual(self.client.post('/api/mobile/v1/auth/verify-email/'+token+'/').status_code, 400)
        self.user.email='changed@example.com'; self.user.save()
        self.assertEqual(self.client.post(path).status_code, 400)
        path=urlparse(verification_url(self.user)).path
        self.user.is_active=False; self.user.save()
        self.assertEqual(self.client.post(path).status_code, 400)

    def test_refresh_and_authenticated_api_are_blocked_until_verified(self):
        refresh=RefreshToken.for_user(self.user)
        self.assertEqual(self.api.post('/api/mobile/v1/auth/refresh/', {'refresh': str(refresh)}).status_code, 403)
        self.api.credentials(HTTP_AUTHORIZATION='Bearer '+str(refresh.access_token))
        self.assertEqual(self.api.get('/api/mobile/v1/profile/').status_code, 403)

    def test_resend_is_generic_and_smtp_failure_retryable(self):
        route='/api/mobile/v1/auth/resend-verification/'
        missing=self.api.post(route, {'email':'missing@example.com'})
        existing=self.api.post(route, {'email':self.user.email})
        self.assertEqual(missing.data, existing.data)
        self.assertEqual(len(mail.outbox), 1)
        with patch('mobile_api.email_verification.send_mail', side_effect=RuntimeError('mail unavailable')):
            self.assertEqual(self.api.post(route, {'email':self.user.email}).status_code, 200)
        self.user.mobile_email_verified=True; self.user.save()
        self.api.post(route, {'email':self.user.email})
        self.assertEqual(len(mail.outbox), 1)
