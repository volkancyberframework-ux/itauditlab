import uuid
from unittest.mock import patch
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from .models import Question, AudioAsset, WorkshopVoice


class WorkshopTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.audio = AudioAsset.objects.create(title='Ses', file='demo/mfa.m4a')
        self.voice = Question.objects.create(kind='voice', prompt='Söyle', published=True,
            in_workshop=True, answer=['risk'], audio=self.audio)
        Question.objects.create(kind='text', prompt='Özel', published=True, answer=['gizli'])

    def test_all_types_and_public_media_are_explicitly_selected(self):
        for kind, _ in Question.TYPES:
            Question.objects.create(kind=kind,prompt=kind,published=True,in_workshop=True,
                options=[{'id':'a','text':'A'}],answer=['a'])
        Question.objects.create(kind='text',prompt='Taslak',published=False,in_workshop=True)
        data = self.client.get('/api/mobile/v1/workshop/questions/').data
        self.assertEqual({q['kind'] for q in data}, {k for k,_ in Question.TYPES})
        self.assertNotIn('Özel', [q['prompt'] for q in data])
        self.assertNotIn('Taslak', [q['prompt'] for q in data])
        url = f'/api/mobile/v1/workshop/questions/{self.voice.pk}/audio/{self.audio.pk}/'
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(url.replace(f'audio/{self.audio.pk}', 'audio/999999')).status_code, 404)
        self.voice.in_workshop = False; self.voice.save()
        self.assertEqual(self.client.get(url).status_code,404)

    @patch('mobile_api.workshop.VoiceThrottle.rate', '100/day')
    @patch('mobile_api.alerts.deliver_alert', return_value=True)
    def test_voice_requires_token_valid_email_and_file_and_is_idempotent(self, _):
        q = self.client.get('/api/mobile/v1/workshop/questions/').data[0]
        key = str(uuid.uuid4())
        def upload(token, email='learner@example.com', content=b'\x00\x00\x00\x18ftypM4A '+b'\x00'*30):
            return self.client.post(f'/api/mobile/v1/workshop/questions/{self.voice.pk}/voice/',
                {'token':token,'email':email,'submission_id':key,'duration':3,
                 'file':SimpleUploadedFile('voice.m4a',content)},format='multipart')
        self.assertEqual(upload('invalid').status_code,400)
        self.assertEqual(upload(q['voice_token'],email='bad').status_code,400)
        self.assertEqual(upload(q['voice_token'],content=b'not an audio').status_code,400)
        self.assertEqual(upload(q['voice_token']).status_code,200)
        self.assertEqual(upload(q['voice_token']).status_code,200)
        self.assertEqual(WorkshopVoice.objects.count(),1)
        self.assertEqual(upload(q['voice_token'],email='other@example.com').status_code,400)
        record=WorkshopVoice.objects.get(); record.feedback='Kontrol ekle.'; record.save()
        from .workshop import send_feedback
        from django.core import mail
        send_feedback(record.pk); send_feedback(record.pk)
        self.assertEqual(len(mail.outbox),1)
        record.delete()
