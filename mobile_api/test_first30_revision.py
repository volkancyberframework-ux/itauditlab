from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient
from .first30_content import import_package
from .first30_revision import apply_revision,rollback_revision,CYCLE,load_revision
from .models import LearningPath,Question,AudioAsset,LearningSession,QuestionAttempt,UserPathProgress,XPTransaction
class First30RevisionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.path=LearningPath.objects.create(pk=26,title='🪪 İşe Alındın! İlk 30 Günün')
        self.other=LearningPath.objects.create(title='Other',published=True)
        self.other_question=Question.objects.create(kind='choice',prompt='Keep',options=[{'id':'a','text':'A'}],answer=['a'],published=True);self.other_question.paths.add(self.other)
        import_package(dry_run=False)
        self.user=get_user_model().objects.create_user(username='revision',is_mobile=True,mobile_full_access=True)
        self.client=APIClient();self.client.force_authenticate(self.user)
    def test_dry_run_roles_cycle_and_cards(self):
        before=AudioAsset.objects.count();report=apply_revision()
        self.assertEqual(report['lesson_pages'],40);self.assertEqual(AudioAsset.objects.count(),before)
        apply_revision(dry_run=False)
        self.assertEqual(list(self.path.questions.values_list('kind',flat=True)),CYCLE*10)
        for q in self.path.questions.filter(kind='info'):
            self.assertEqual(len(q.card_pages),4)
            self.assertGreater(sum(len(p['body'].split()) for p in q.card_pages),130)
        self.assertIn('Selin (Yöneticin)',self.path.questions.get(order=3).context)
        self.assertEqual(self.path.questions.filter(kind='audio',audio__isnull=False).count(),10)
        self.assertTrue(self.path.questions.get(order=6).image)
    def test_idempotence_history_and_rollback(self):
        q=self.path.questions.first();session=LearningSession.objects.create(path=self.path,user=self.user,questions=[q.pk,self.path.questions.get(order=8).pk,self.path.questions.get(order=2).pk])
        attempt=QuestionAttempt.objects.create(question=q,session=session,answer=q.answer,is_correct=True,xp_change=10)
        xp=XPTransaction.objects.create(user=self.user,attempt=attempt,amount=10,reason='correct')
        progress=UserPathProgress.objects.create(path=self.path,user=self.user);progress.completed.add(q)
        original_ids=set(self.path.questions.values_list('pk',flat=True));original=dict(self.path.questions.values_list('pk','kind'))
        apply_revision(dry_run=False);audio_count=AudioAsset.objects.count()
        self.assertTrue(apply_revision(dry_run=False)['already_applied'])
        self.assertEqual(AudioAsset.objects.count(),audio_count);self.assertEqual(set(self.path.questions.values_list('pk',flat=True)),original_ids)
        attempt.refresh_from_db();self.assertEqual(attempt.xp_change,10);self.assertEqual(XPTransaction.objects.get(pk=xp.pk).amount,10)
        self.assertEqual(list(progress.completed.values_list('pk',flat=True)),[q.pk])
        session.refresh_from_db();self.assertEqual(session.questions[0],q.pk);self.assertEqual(session.questions[1:],[self.path.questions.get(order=2).pk,self.path.questions.get(order=6).pk])
        self.other_question.refresh_from_db();self.assertEqual(self.other_question.prompt,'Keep')
        rollback_revision();self.assertEqual(dict(self.path.questions.values_list('pk','kind')),original)
        self.assertEqual(QuestionAttempt.objects.get(pk=attempt.pk).answer,q.answer)
        apply_revision(dry_run=False);self.assertEqual(list(self.path.questions.values_list('kind',flat=True)),CYCLE*10)
    def test_audio_and_image_private_real_and_nonempty(self):
        apply_revision(dry_run=False)
        for q in self.path.questions.filter(kind='audio'):
            data=self.client.get(f'/api/mobile/v1/questions/{q.pk}/image/')
            self.assertEqual(data.status_code,404)
            r=self.client.get(f'/api/mobile/v1/audio/{q.audio_id}/',HTTP_RANGE='bytes=0-99')
            self.assertIn(r.status_code,[200,206]);self.assertEqual(r['Content-Type'],'audio/mpeg')
            payload=b''.join(r.streaming_content);self.assertTrue(payload.startswith(b'ID3'));r.close()
        q=self.path.questions.get(order=6)
        r=self.client.get(f'/api/mobile/v1/questions/{q.pk}/image/');self.assertEqual(r.status_code,200);r.close()
        anonymous=APIClient();self.assertIn(anonymous.get(f'/api/mobile/v1/audio/{self.path.questions.first().audio_id}/').status_code,[401,403])
    def test_all_revised_records_via_real_api(self):
        apply_revision(dry_run=False);seen=[];correct=0
        while len(seen)<100:
            r=self.client.post('/api/mobile/v1/sessions/',{'path_id':26},format='json');self.assertEqual(r.status_code,201,r.data);sid=r.data['id'];state=r.data
            while state['question']:
                data=state['question'];q=Question.objects.get(pk=data['id']);seen.append(q.kind)
                self.assertEqual(bool(data['audio']),q.kind=='audio');self.assertNotIn('answer',data)
                if q.kind=='info':
                    r=self.client.post(f'/api/mobile/v1/sessions/{sid}/continue/',{'question_id':q.pk},format='json');state=r.data
                else:
                    answer=q.answer[0] if q.kind=='fill_blank' else q.answer
                    r=self.client.post(f'/api/mobile/v1/sessions/{sid}/answer/',{'question_id':q.pk,'answer':answer},format='json')
                    self.assertEqual(r.status_code,200,r.data);self.assertTrue(r.data['correct']);correct+=1;state=r.data['session']
        self.assertEqual(seen,CYCLE*10);self.assertEqual(correct,90)
        self.assertEqual(UserPathProgress.objects.get(path=self.path,user=self.user).completed.count(),100)
    def test_manual_edit_stops_overwrite(self):
        q=self.path.questions.first();q.prompt='Manual edit';q.save()
        with self.assertRaises(ValidationError):apply_revision(dry_run=False)
        q.refresh_from_db();self.assertEqual(q.prompt,'Manual edit')
