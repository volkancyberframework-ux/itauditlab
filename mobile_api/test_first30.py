from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient
from .first30_content import import_package, load_package
from .models import LearningPath, Question, Module, AudioAsset, UserPathProgress, XPTransaction, LearningSession
class First30Tests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.path=LearningPath.objects.create(pk=26,title='🪪 İşe Alındın! İlk 30 Günün',preferences={'keep':'yes'})
        self.other=LearningPath.objects.create(title='Other',published=True)
        self.other_q=Question.objects.create(kind='choice',prompt='Original',published=True,answer=['a']);self.other_q.paths.add(self.other)
        self.user=get_user_model().objects.create_user(username='first30',is_mobile=True,mobile_full_access=True)
        self.client=APIClient();self.client.force_authenticate(self.user)
        self.audio_baseline=AudioAsset.objects.count();self.baseline=Question.objects.count();self.module_baseline=Module.objects.count()
    def test_dry_run_and_idempotence_preserve_other_paths(self):
        self.assertEqual(import_package()['create'],100)
        self.assertEqual(Question.objects.count(),self.baseline);self.assertEqual(Module.objects.count(),self.module_baseline)
        import_package(dry_run=False)
        ids=list(self.path.questions.values_list('pk',flat=True))
        self.assertEqual(import_package(dry_run=False)['created'],0)
        self.assertEqual(ids,list(self.path.questions.values_list('pk',flat=True)))
        self.assertEqual(list(self.other.questions.values_list('pk',flat=True)),[self.other_q.pk])
        self.assertEqual(AudioAsset.objects.count(),self.audio_baseline)
        self.path.refresh_from_db();self.assertEqual(self.path.preferences['keep'],'yes');self.assertTrue(self.path.published)
    def test_wrong_id_and_unmanaged_content_stop(self):
        with self.assertRaises(ValidationError):import_package(path_id=self.other.pk,dry_run=False)
        self.other_q.paths.add(self.path)
        with self.assertRaises(ValidationError):import_package(dry_run=False)
        self.assertEqual(Question.objects.count(),self.baseline)
    def test_all_records_evaluate_and_progress_survives_rerun(self):
        import_package(dry_run=False)
        seen=[];graded=0
        while len(seen)<100:
            r=self.client.post('/api/mobile/v1/sessions/',{'path_id':26},format='json');self.assertEqual(r.status_code,201,r.data)
            sid=r.data['id'];state=r.data
            while state['question']:
                data=state['question'];q=Question.objects.get(pk=data['id']);seen.append(q.order)
                self.assertEqual(data['audio'],[]);self.assertNotIn('answer',data)
                if q.kind=='info':
                    r=self.client.post(f'/api/mobile/v1/sessions/{sid}/continue/',{'question_id':q.pk},format='json')
                else:
                    answer=q.answer[0] if q.kind=='fill_blank' else q.answer
                    r=self.client.post(f'/api/mobile/v1/sessions/{sid}/answer/',{'question_id':q.pk,'answer':answer},format='json')
                    self.assertEqual(r.status_code,200,r.data);self.assertTrue(r.data['correct'],q.prompt);graded+=1
                self.assertEqual(r.status_code,200,r.data);state=r.data if q.kind=='info' else r.data['session']
        self.assertEqual(seen,list(range(1,101)));self.assertEqual(graded,90)
        self.assertEqual(UserPathProgress.objects.get(path=self.path,user=self.user).completed.count(),100)
        before=XPTransaction.objects.filter(user=self.user).count()
        import_package(dry_run=False)
        self.assertEqual(XPTransaction.objects.filter(user=self.user).count(),before)
        self.assertEqual(UserPathProgress.objects.get(path=self.path,user=self.user).completed.count(),100)
    def test_images_private_and_real(self):
        import_package(dry_run=False)
        for q in self.path.questions.filter(kind='image'):
            with q.image.open('rb') as f:self.assertEqual(f.read(8),b'\x89PNG\r\n\x1a\n')
            r=self.client.get(f'/api/mobile/v1/questions/{q.pk}/image/');self.assertEqual(r.status_code,200)
            r.close()
        anon=APIClient();q=self.path.questions.filter(kind='image').first()
        self.assertIn(anon.get(f'/api/mobile/v1/questions/{q.pk}/image/').status_code,[401,403])
    def test_wrong_order_incomplete_multi_and_wrong_text(self):
        import_package(dry_run=False)
        for kind in ['sentence_order','multi_select','fill_blank']:
            q=self.path.questions.filter(kind=kind).first();s=LearningSession.objects.create(path=self.path,user=self.user,questions=[q.pk])
            answer=list(reversed(q.answer)) if kind=='sentence_order' else [q.answer[0]] if kind=='multi_select' else 'uydurma'
            r=self.client.post(f'/api/mobile/v1/sessions/{s.pk}/answer/',{'question_id':q.pk,'answer':answer},format='json')
            self.assertEqual(r.status_code,200,r.data);self.assertFalse(r.data['correct'])
