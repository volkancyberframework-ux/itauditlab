from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import PersonalAppAddress
from .personal_address import personal_host, check_console_address
from itaudit.console_gateway import ConsoleGateway


class PersonalAddressTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='ayse', password='password', is_mobile=True, mobile_email_verified=True)
        self.other = get_user_model().objects.create_user(username='other', password='password', is_mobile=True, mobile_email_verified=True)
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.endpoint = '/api/mobile/v1/profile/address/'

    def save(self, slug):
        return self.api.post(self.endpoint, {'slug': slug}, format='json')

    def test_claim_normalize_profile_rename_release(self):
        result = self.save(' Ayse ')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data['url'], 'https://ayse.grcustasi.com')
        self.assertEqual(self.api.get('/api/mobile/v1/profile/').data['personal_address'], result.data)
        self.assertEqual(self.save('ayse-yeni').status_code, 200)
        self.assertFalse(personal_host('ayse.grcustasi.com'))
        self.assertTrue(personal_host('ayse-yeni.grcustasi.com'))
        self.assertEqual(self.save('').data['url'], '')
        self.assertFalse(PersonalAppAddress.objects.filter(user=self.user).exists())

    def test_unique_ownership_no_overwrite(self):
        self.save('ayse')
        self.api.force_authenticate(self.other)
        self.assertEqual(self.save('ayse').status_code, 400)
        self.assertEqual(PersonalAppAddress.objects.get(slug='ayse').user, self.user)
        self.assertEqual(self.save('').status_code, 200)
        self.assertTrue(personal_host('ayse.grcustasi.com'))

    def test_reserved_and_invalid_names(self):
        for slug in ['app', 'www', 'admin', 'support', 'denetim', 'ab', '1ayse', '-ayse', 'ayse-', 'ay.se', 'ayşe', 'a'*31, 'ayse/grcustasi', None]:
            with self.subTest(slug=slug):
                self.assertEqual(self.save(slug).status_code, 400)
        self.assertFalse(PersonalAppAddress.objects.exists())

    def test_requires_account_and_mobile_access(self):
        self.api.force_authenticate(None)
        self.assertEqual(self.save('ayse').status_code, 401)
        self.other.is_mobile = False
        self.other.save()
        self.api.force_authenticate(self.other)
        self.assertEqual(self.save('ayse').status_code, 403)

    @override_settings(ALLOWED_HOSTS=['.grcustasi.com', 'testserver'])
    def test_personal_host_serves_app_without_exposing_owner(self):
        self.save('ayse')
        with TemporaryDirectory() as root, override_settings(MOBILE_WEB_ROOT=root):
            Path(root, 'index.html').write_text('<title>GRC app</title>')
            response = self.client.get('/', HTTP_HOST='ayse.grcustasi.com')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'GRC app', b''.join(response.streaming_content))
            self.assertEqual(self.client.get('/api/mobile/v1/profile/', HTTP_HOST='ayse.grcustasi.com').status_code, 401)
        self.assertFalse(personal_host('ayse.grcustasi.com.evil.test'))
        self.assertFalse(personal_host('x.ayse.grcustasi.com'))
        app = lambda environ, start: [b'personal app']
        gateway = ConsoleGateway(app)
        self.assertEqual(gateway({'HTTP_HOST': 'ayse.grcustasi.com', 'PATH_INFO': '/'}, lambda *args: None), [b'personal app'])
        with patch('itaudit.console_gateway.UnixConnection', side_effect=RuntimeError('console route')):
            with self.assertRaisesRegex(RuntimeError, 'console route'):
                gateway({'HTTP_HOST': 'company.grcustasi.com', 'PATH_INFO': '/', 'CONTENT_LENGTH': '0'}, lambda *args: None)


    def test_console_collision_and_shared_lock(self):
        from rest_framework.exceptions import ValidationError
        cursor = MagicMock()
        cursor.fetchone.side_effect = [('workspace_organization',), (1,)]
        with patch('mobile_api.personal_address.connection') as db:
            db.vendor = 'postgresql'
            db.cursor.return_value.__enter__.return_value = cursor
            with self.assertRaises(ValidationError):
                check_console_address('ayse')
        cursor.execute.assert_any_call('SELECT pg_advisory_xact_lock(74123, hashtext(%s))', ['ayse'])
        cursor.execute.assert_any_call('SELECT 1 FROM municipal_console.workspace_organization WHERE lower(subdomain) = %s', ['ayse'])
