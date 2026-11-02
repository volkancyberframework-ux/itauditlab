import json
from unittest.mock import patch
from django.core import mail
from django.test import Client, TestCase
from django.test.utils import override_settings
from .fridge import _cache

@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class FridgeDemoTests(TestCase):
    def setUp(self):
        _cache.clear()

    def payload(self, **changes):
        from django.core import signing
        from uuid import uuid4
        return {'token': signing.dumps({'id': uuid4().hex}, salt='fridge-demo-v1'),
                'username': 'volkanadmin', 'password': 'volkanseyahat1234', 'temperature': -2, **changes}

    def post(self, data):
        return self.client.post('/buzdolabi/onay', json.dumps(data), content_type='application/json')

    def test_page_never_reads_or_writes_database_even_with_session_cookie(self):
        self.client.cookies['sessionid'] = 'old-real-session-that-must-not-be-read'
        with self.assertNumQueries(0):
            response = self.client.get('/buzdolabi')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '−5°C')
        self.assertContains(response, 'volkanadmin')
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_change_notifies_owner_without_database_access(self):
        with self.assertNumQueries(0):
            response = self.post(self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['volkan@grcustasi.com'])
        self.assertIn('Yeni sıcaklık: -2°C', mail.outbox[0].body)

    def test_unchanged_or_invalid_temperature_does_not_notify(self):
        for value in [-5, True, 16, -31, '3', None, float('nan')]:
            with self.subTest(value=value):
                self.assertEqual(self.post(self.payload(temperature=value)).status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_fake_auth_and_bad_token_do_not_notify(self):
        self.assertEqual(self.post(self.payload(password='wrong')).status_code, 403)
        self.assertEqual(self.post(self.payload(token='invalid')).status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_one_confirmation_per_demo(self):
        data = self.payload()
        self.assertEqual(self.post(data).status_code, 200)
        self.assertEqual(self.post(data).status_code, 409)
        self.assertEqual(len(mail.outbox), 1)

    @patch('landing.fridge.send_mail', side_effect=RuntimeError('mail offline'))
    def test_failed_mail_allows_retry(self, send):
        data = self.payload()
        self.assertEqual(self.post(data).status_code, 503)
        send.side_effect = None
        send.return_value = 1
        self.assertEqual(self.post(data).status_code, 200)

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/buzdolabi/onay', json.dumps(self.payload()), content_type='application/json').status_code, 403)
        client.get('/buzdolabi')
        self.assertEqual(client.post('/buzdolabi/onay', json.dumps(self.payload()), content_type='application/json', HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value).status_code, 200)

    def test_other_methods_and_malformed_json(self):
        self.assertEqual(self.client.get('/buzdolabi/onay').status_code, 405)
        self.assertEqual(self.client.post('/buzdolabi').status_code, 405)
        self.assertEqual(self.client.post('/buzdolabi/onay', '[]', content_type='application/json').status_code, 400)
