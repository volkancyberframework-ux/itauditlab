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
        telegram_patch = patch('landing.fridge.send_telegram', return_value=True)
        self.telegram = telegram_patch.start()
        self.addCleanup(telegram_patch.stop)

    def payload(self, **changes):
        from django.core import signing
        from uuid import uuid4
        return {'token': signing.dumps({'id': uuid4().hex, 'authenticated': True}, salt='fridge-demo-v1'),
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
        self.assertEqual(len(mail.outbox), 0)
        self.telegram.assert_called_once()
        message = self.telegram.call_args.args[0]
        self.assertIn('Yeni sıcaklık: -2°C', message)
        self.assertRegex(response.json()['code'], r'^GRC60-[A-F0-9]{12}$')
        self.assertIn(response.json()['code'], message)
        self.assertIn('15 dakika birebir görüşme', message)

    def test_unchanged_or_invalid_temperature_does_not_notify(self):
        for value in [-5, True, 50.5, 51, -31, '3', None, float('nan')]:
            with self.subTest(value=value):
                self.assertEqual(self.post(self.payload(temperature=value)).status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_fake_auth_and_bad_token_do_not_notify(self):
        self.assertEqual(self.client.post('/buzdolabi/giris', json.dumps(self.payload(password='wrong')), content_type='application/json').status_code, 403)
        self.assertEqual(self.post(self.payload(token='invalid')).status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_one_confirmation_per_demo(self):
        data = self.payload()
        self.assertEqual(self.post(data).status_code, 200)
        self.assertEqual(self.post(data).status_code, 409)
        self.assertEqual(len(mail.outbox), 0)
        self.telegram.assert_called_once()

    @patch('landing.fridge.send_telegram', side_effect=RuntimeError('telegram offline'))
    def test_failed_telegram_allows_retry(self, send):
        data = self.payload()
        self.assertEqual(self.post(data).status_code, 503)
        send.side_effect = None
        send.return_value = True
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

    def test_login_uses_video_password_with_final_period_without_database(self):
        with self.assertNumQueries(0):
            response = self.client.post('/buzdolabi/giris', json.dumps(self.payload(password='volkanseyahat1234.')), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.json()['code'], r'^GRC25-[A-F0-9]{12}$')
        self.assertEqual(self.post(self.payload(token=response.json()['token'])).status_code, 200)
        response = self.client.get('/buzdolabi')
        self.assertNotContains(response, 'volkanseyahat1234')
        self.assertContains(response, 'Parola için videoya gidin.')
        self.assertContains(response, 'volkanseyahat12 ...?')

    def test_reward_codes_are_stable_per_demo_and_different_for_other_demos(self):
        from .fridge import reward_code
        self.assertEqual(reward_code('demo-one', 60), reward_code('demo-one', 60))
        self.assertNotEqual(reward_code('demo-one', 60), reward_code('demo-two', 60))
        self.assertNotEqual(reward_code('demo-one', 25), reward_code('demo-one', 60))

    def test_missing_telegram_configuration_allows_retry_without_email(self):
        self.telegram.return_value = False
        data = self.payload()
        self.assertEqual(self.post(data).status_code, 503)
        self.assertEqual(len(mail.outbox), 0)
        self.telegram.return_value = True
        self.assertEqual(self.post(data).status_code, 200)

    @override_settings(GRCUSTASI_TELEGRAM_BOT_TOKEN='demo-test-token', GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID='123')
    def test_real_telegram_helper_does_not_query_database(self):
        from skool.services import send_telegram
        with patch('landing.fridge.send_telegram', wraps=send_telegram), patch('skool.services.requests.post') as post:
            with self.assertNumQueries(0):
                response = self.post(self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(post.call_args.kwargs['data']['chat_id'], '123')
        self.assertEqual(len(mail.outbox), 0)

    def test_fifty_degrees_is_accepted(self):
        with self.assertNumQueries(0):
            response = self.post(self.payload(temperature=50))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['temperature'], 50)
        self.assertIn('Yeni sıcaklık: 50°C', self.telegram.call_args.args[0])
