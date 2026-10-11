import io
import wave
from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError
from mobile_api.recording_formats import recording_extension
from itaudit.console_gateway import console_route


class WebAppTests(TestCase):
    @override_settings(ALLOWED_HOSTS=['app.grcustasi.com', 'www.grcustasi.com'])
    def test_app_host_and_path_boundaries(self):
        with TemporaryDirectory() as root, override_settings(MOBILE_WEB_ROOT=root):
            Path(root, 'index.html').write_text('<title>GRC Ustası web</title>')
            response = self.client.get('/', HTTP_HOST='app.grcustasi.com')
            self.assertEqual(response.status_code, 200)
            self.assertIn('GRC Ustası web'.encode(), b''.join(response.streaming_content))
            self.assertEqual(response['Permissions-Policy'], 'microphone=(self), camera=()')
            self.assertEqual(self.client.get('/../settings.py', HTTP_HOST='app.grcustasi.com').status_code, 404)
            self.assertEqual(self.client.get('/.hidden', HTTP_HOST='app.grcustasi.com').status_code, 404)
            self.assertIsNone(console_route({'PATH_INFO': '/', 'HTTP_HOST': 'app.grcustasi.com'}))
            self.assertEqual(self.client.get('/api/mobile/v1/profile/', HTTP_HOST='app.grcustasi.com').status_code, 401)

    def test_browser_wav_and_invalid_recordings(self):
        data = io.BytesIO()
        with wave.open(data, 'wb') as audio:
            audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
            audio.writeframes(b'\x00\x00' * 16000)
        upload = SimpleUploadedFile('recording.wav', data.getvalue())
        self.assertEqual(recording_extension(upload), 'wav')
        self.assertEqual(upload.tell(), 0)
        with self.assertRaises(ValidationError):
            recording_extension(SimpleUploadedFile('recording.wav', data.getvalue()[:-100]))
        with self.assertRaises(ValidationError):
            recording_extension(SimpleUploadedFile('fake.m4a', b'fake'))

    @override_settings(MOBILE_VOICE_ROOT='/tmp/grc-web-voice-tests')
    def test_browser_wav_upload_uses_existing_private_review_pipeline(self):
        import uuid
        from rest_framework.test import APIClient
        from mobile_api.models import Question, WorkshopVoice
        from unittest.mock import patch
        client = APIClient()
        q = Question.objects.create(kind='voice', prompt='Web ses', published=True, in_workshop=True, answer=['risk'])
        token = client.get('/api/mobile/v1/workshop/questions/').data[0]['voice_token']
        data = io.BytesIO()
        with wave.open(data, 'wb') as audio:
            audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
            audio.writeframes(b'\x00\x00' * 16000)
        with patch('mobile_api.alerts.deliver_alert', return_value=True):
            response = client.post(f'/api/mobile/v1/workshop/questions/{q.pk}/voice/', {
                'token': token, 'email': 'qa@example.test', 'submission_id': str(uuid.uuid4()),
                'duration': 1, 'file': SimpleUploadedFile('recording.wav', data.getvalue()),
            }, format='multipart')
        self.assertEqual(response.status_code, 200)
        submission = WorkshopVoice.objects.get()
        self.assertTrue(submission.file.name.endswith('.wav'))
        self.assertEqual(submission.duration, 1)
        submission.file.delete()

    @override_settings(ALLOWED_HOSTS=['app.grcustasi.com'])
    def test_browser_payment_link_uses_marketing_routes(self):
        from rest_framework.test import APIClient
        from django.contrib.auth import get_user_model
        client = APIClient()
        user = get_user_model().objects.create_user(username='web-payer', email='web-payer@example.test', is_mobile=True)
        client.force_authenticate(user)
        response = client.post('/api/mobile/v1/payments/link/', HTTP_HOST='app.grcustasi.com')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['url'].startswith('https://www.grcustasi.com/mobiluygulama?token='))
