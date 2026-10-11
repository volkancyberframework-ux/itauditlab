from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Question, MobileSettings, LearningPath
from .web_demo import seed_web_demo, TITLE


class WebDemoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='browser-qa', is_mobile=True, mobile_email_verified=True, mobile_full_access=False)
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.path = LearningPath.objects.get(title=TITLE, owner=None)

    def test_all_types_in_one_session_and_assets_accessible(self):
        self.assertEqual(set(self.path.questions.values_list('kind', flat=True)), {kind for kind, _ in Question.TYPES})
        data = self.api.post('/api/mobile/v1/sessions/', {'path_id': self.path.pk}, format='json')
        self.assertEqual(data.status_code, 201)
        self.assertEqual(data.data['total'], 11)
        self.assertEqual(data.data['question_total'], 10)
        image = self.path.questions.get(kind='image')
        audio = self.path.questions.get(kind='audio').audio
        for url in [f'/api/mobile/v1/questions/{image.pk}/image/', f'/api/mobile/v1/audio/{audio.pk}/']:
            self.assertEqual(self.api.get(url).status_code, 200)
            self.api.force_authenticate(None)
            self.assertEqual(self.api.get(url).status_code, 401)
            self.api.force_authenticate(self.user)

    def test_demo_available_without_changing_starter_or_unlocking_paid_paths(self):
        starter = LearningPath.objects.create(title='Starter', published=True)
        paid = LearningPath.objects.create(title='Paid', published=True, premium=True)
        settings, _ = MobileSettings.objects.get_or_create(pk=1)
        settings.free_path = starter
        settings.save()
        result = self.api.get('/api/mobile/v1/paths/')
        ids = {item['id'] for item in result.data}
        self.assertIn(self.path.pk, ids)
        self.assertIn(starter.pk, ids)
        self.assertNotIn(paid.pk, ids)
        settings.refresh_from_db()
        self.assertEqual(settings.free_path, starter)

    def test_seeding_is_repeatable(self):
        ids = list(self.path.questions.values_list('pk', flat=True))
        self.assertEqual(seed_web_demo(apps).pk, self.path.pk)
        self.assertEqual(list(self.path.questions.values_list('pk', flat=True)), ids)
