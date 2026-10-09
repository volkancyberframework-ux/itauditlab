from django.test import TestCase
from rest_framework.test import APIClient
from .admin import PracticeCaseForm
from .models import PracticeCase


class PracticeCatalogTests(TestCase):
    def test_public_catalog_respects_selection_order_and_answers(self):
        PracticeCase.objects.all().delete()
        fields = dict(situation='Senaryo', sentence=['Neden', 'Olay', 'Sonuç'],
                      controls=['Yanlış', 'Doğru'], control=2, control_reason='Kontrol açıklaması',
                      evidence=['Doğru', 'Yanlış'], proof=1, evidence_reason='Kanıt açıklaması',
                      likelihood=3, impact=4)
        PracticeCase.objects.create(title='Gizli', published=False, **fields)
        PracticeCase.objects.create(title='Sonra', published=True, order=2, **fields)
        first = PracticeCase.objects.create(title='Önce', published=True, order=1, **fields)
        response = APIClient().get('/api/mobile/v1/practice-cases/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([c['title'] for c in response.data], ['Önce', 'Sonra'])
        self.assertEqual(response.data[0]['control'], 1)
        self.assertEqual(response.data[0]['proof'], 0)
        first.published = False
        first.save()
        self.assertEqual(len(APIClient().get('/api/mobile/v1/practice-cases/').data), 1)

    def test_admin_lines_and_invalid_answer(self):
        data = dict(title='Vaka', situation='Senaryo', sentence='Neden\nOlay\nSonuç',
                    controls='Yanlış\nDoğru', control=2, control_reason='Açıklama',
                    evidence='Doğru\nYanlış', proof=1, evidence_reason='Açıklama',
                    likelihood=3, impact=4, order=0, published=True)
        form = PracticeCaseForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.controls, ['Yanlış', 'Doğru'])
        self.assertEqual(PracticeCaseForm(instance=saved).fields['controls'].initial, 'Yanlış\nDoğru')
        data['control'] = 3
        self.assertFalse(PracticeCaseForm(data=data).is_valid())
