from collections import Counter
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .cism_manager import seed, load_package, KEY
from .cisa_simulator import answer_key
from .models import LearningPath, Question, LearningSession, UserPathProgress, QuestionAttempt, XPTransaction

class CismManagerTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        seed(dry_run=False)
        self.path=LearningPath.objects.get(preferences__cism_manager_v1__slug='cism-manager-v1')
        self.other=LearningPath.objects.create(title='Unrelated',published=True)
        self.other_q=Question.objects.create(kind='choice',prompt='Unchanged',answer=['a'],options=[{'id':'a','text':'A'},{'id':'b','text':'B'}],published=True)
        self.other_q.paths.add(self.other)
        self.user=get_user_model().objects.create_user(username='cism-test',is_mobile=True,mobile_full_access=True)
        self.client=APIClient();self.client.force_authenticate(self.user)

    def test_content_and_idempotence(self):
        package=load_package()
        self.assertEqual(len(package['questions']),100)
        self.assertEqual(Counter(q.module.order for q in self.path.questions.all()),Counter({i:25 for i in range(1,5)}))
        self.assertEqual(self.path.questions.count(),100)
        self.assertEqual(Counter(q.kind for q in self.path.questions.all()),Counter(choice=20,scenario=20,drag_select=20,sentence_order=20,multi_select=10,fill_blank=10))
        self.assertFalse(self.path.questions.filter(kind__in=['voice','audio']).exists())
        self.assertFalse(self.path.questions.exclude(audio=None).exists())
        self.assertEqual(Counter(q['presentation'] for q in package['questions'] if 'presentation' in q),Counter(true_false=5,pair_matching=5))
        ids=list(self.path.questions.values_list('id',flat=True));before=Question.objects.count()
        self.assertEqual(seed(dry_run=False)['create'],0)
        self.assertEqual(Question.objects.count(),before)
        self.assertEqual(ids,list(self.path.questions.values_list('id',flat=True)))
        self.other_q.refresh_from_db();self.assertEqual(self.other_q.prompt,'Unchanged')

    def test_all_100_answers_keys_and_domain_summary(self):
        orders=[]
        for domain in range(1,5):
            response=self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json')
            self.assertEqual(response.status_code,201,response.data)
            state=response.data;sid=state['id'];self.assertEqual(state['total'],25)
            while state['question']:
                q=Question.objects.get(pk=state['question']['id'])
                self.assertEqual(q.module.order,domain);orders.append(q.order)
                self.assertEqual(state['question']['audio'],[])
                self.assertTrue(all(set(o)=={'id','text'} for o in state['question']['options']))
                submitted=q.answer[0] if q.kind=='fill_blank' else q.answer
                result=self.client.post(f'/api/mobile/v1/sessions/{sid}/answer/',{'question_id':q.pk,'answer':submitted},format='json')
                self.assertEqual(result.status_code,200,result.data);self.assertTrue(result.data['correct'],q.prompt)
                for text in answer_key(q):self.assertIn(text,result.data['explanation'])
                self.assertNotIn('http',result.data['explanation']);self.assertNotIn('Kaynak:',result.data['explanation'])
                state=result.data['session']
            self.assertEqual(state['evaluation']['domains'][-1]['correct'],25)
            self.assertEqual(state['evaluation']['complete'],domain==4)
        self.assertEqual(orders,list(range(1,101)))
        self.assertEqual(UserPathProgress.objects.get(path=self.path,user=self.user).completed.count(),100)
        self.assertEqual(QuestionAttempt.objects.filter(session__user=self.user).count(),100)
        count=XPTransaction.objects.filter(user=self.user).count();seed(dry_run=False)
        self.assertEqual(XPTransaction.objects.filter(user=self.user).count(),count)

    def test_wrong_answer_specific_feedback_and_resume(self):
        state=self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json').data
        q=Question.objects.get(pk=state['question']['id']);wrong=next(o for o in q.options if o['id'] not in q.answer)
        r=self.client.post(f'/api/mobile/v1/sessions/{state["id"]}/answer/',{'question_id':q.pk,'answer':[wrong['id']]},format='json')
        self.assertFalse(r.data['correct']);self.assertEqual(r.data['xp_change'],0);self.assertIn(wrong['feedback'],r.data['explanation'])
        self.assertEqual(r.data['session']['question']['id'],self.path.questions.get(order=2).pk)
        resumed=self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json').data
        self.assertEqual(resumed['id'],state['id']);self.assertEqual(resumed['question']['id'],r.data['session']['question']['id'])
        self.assertTrue(resumed['path']['direct_start'])
        repeat=self.client.post(f'/api/mobile/v1/sessions/{state["id"]}/answer/',{'question_id':q.pk,'answer':q.answer},format='json')
        self.assertFalse(repeat.data['correct']);self.assertEqual(repeat.data['explanation'],r.data['explanation'])

    def test_invalid_partial_multi_wrong_order_and_text(self):
        for kind in ['multi_select','sentence_order','fill_blank']:
            q=self.path.questions.filter(kind=kind).first()
            session=LearningSession.objects.create(user=self.user,path=self.path,questions=[q.pk])
            wrong=[q.answer[0]] if kind=='multi_select' else list(reversed(q.answer)) if kind=='sentence_order' else 'bilinmeyen'
            r=self.client.post(f'/api/mobile/v1/sessions/{session.pk}/answer/',{'question_id':q.pk,'answer':wrong},format='json')
            self.assertEqual(r.status_code,200,r.data);self.assertFalse(r.data['correct'])
            self.assertIn('Senin cevabın neden uygun değil?',r.data['explanation'])
            for text in answer_key(q):self.assertIn(text,r.data['explanation'])
        q=self.path.questions.filter(kind='fill_blank').first()
        session=LearningSession.objects.create(user=self.user,path=self.path,questions=[q.pk])
        r=self.client.post(f'/api/mobile/v1/sessions/{session.pk}/answer/',{'question_id':q.pk,'answer':q.answer[-1].upper()},format='json')
        self.assertTrue(r.data['correct'])

    def test_other_path_behavior_and_foreign_question_protected(self):
        state=self.client.post('/api/mobile/v1/sessions/',{'path_id':self.other.pk},format='json').data
        self.assertFalse(state['path']['direct_start']);self.assertEqual(state['path']['session_size'],8)
        r=self.client.post(f'/api/mobile/v1/sessions/{state["id"]}/answer/',{'question_id':self.other_q.pk,'answer':['b']},format='json')
        self.assertFalse(r.data['correct']);self.assertNotIn('Doğru cevap:',r.data['explanation'])
        self.assertFalse(UserPathProgress.objects.get(path=self.other,user=self.user).completed.exists())
        state=self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json').data
        r=self.client.post(f'/api/mobile/v1/sessions/{state["id"]}/answer/',{'question_id':self.other_q.pk,'answer':['a']},format='json')
        self.assertEqual(r.status_code,400)

    def test_changed_content_is_not_overwritten(self):
        q=self.path.questions.first();q.prompt='Manual edit';q.save(update_fields=['prompt'])
        with self.assertRaises(ValidationError):seed(dry_run=False)
        q.refresh_from_db();self.assertEqual(q.prompt,'Manual edit')

    def test_domain_summary_counts_wrong_attempts_without_blocking(self):
        state=self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json').data
        sid=state['id'];correct_count=0
        while state['question']:
            q=Question.objects.get(pk=state['question']['id'])
            if q.order%2:
                submitted='uygunsuz' if q.kind=='fill_blank' else list(reversed(q.answer)) if q.kind=='sentence_order' else [next(o['id'] for o in q.options if o['id'] not in q.answer)]
            else:
                submitted=q.answer[0] if q.kind=='fill_blank' else q.answer;correct_count+=1
            r=self.client.post(f'/api/mobile/v1/sessions/{sid}/answer/',{'question_id':q.pk,'answer':submitted},format='json')
            self.assertEqual(r.status_code,200,r.data);state=r.data['session']
        summary=state['evaluation']['domains'][0]
        self.assertEqual(summary['correct'],correct_count);self.assertEqual(summary['rate'],48)
        self.assertEqual(len(summary['development']),13)
        next_state=self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json').data
        self.assertEqual(Question.objects.get(pk=next_state['question']['id']).order,26)

    @override_settings(ROOT_URLCONF='mobile_web.urls')
    def test_all_100_on_web(self):
        for domain in range(1,5):
            state=self.client.post('/web-api/sessions/',{'path_id':self.path.pk},format='json').data
            self.assertEqual(state['total'],25)
            while state['question']:
                q=Question.objects.get(pk=state['question']['id'])
                submitted=q.answer[0] if q.kind=='fill_blank' else q.answer
                r=self.client.post(f'/web-api/sessions/{state["id"]}/answer/',{'question_id':q.pk,'answer':submitted},format='json')
                self.assertEqual(r.status_code,200,r.data);self.assertTrue(r.data['correct'])
                state=r.data['session']
            self.assertEqual(state['path']['progress'],domain*25)
        self.assertTrue(state['evaluation']['complete'])

    def test_paid_only_survives_free_path_misconfiguration(self):
        from .models import MobileSettings
        free=get_user_model().objects.create_user('cism-free',is_mobile=True,mobile_email_verified=True)
        settings,_=MobileSettings.objects.get_or_create(pk=1)
        settings.free_path=self.path;settings.save()
        self.client.force_authenticate(free)
        self.assertNotIn(self.path.pk,[p['id'] for p in self.client.get('/api/mobile/v1/paths/').data])
        self.assertEqual(self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json').status_code,403)
