from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from .models import LearningPath, Question, UserPathProgress, LearningSession, QuestionAttempt, XPTransaction

class PathRestartTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user(username='restart',is_mobile=True,mobile_full_access=True)
        self.client=APIClient();self.client.force_authenticate(self.user)
        self.path=LearningPath.objects.create(title='Restart',published=True)
        self.q=Question.objects.create(kind='choice',prompt='Risk?',published=True,options=[{'id':'a','text':'Risk'}],answer=['a'],base_xp=20)
        self.path.questions.add(self.q)
        self.progress=UserPathProgress.objects.create(user=self.user,path=self.path);self.progress.completed.add(self.q)
        self.session=LearningSession.objects.create(user=self.user,path=self.path,questions=[self.q.pk])
        attempt=QuestionAttempt.objects.create(session=self.session,question=self.q,answer=['a'],is_correct=True,xp_change=20)
        XPTransaction.objects.create(user=self.user,attempt=attempt,amount=20,reason='correct')

    def data(self):
        return next(p for p in self.client.get('/api/mobile/v1/paths/').data if p['id']==self.path.pk)

    def test_restart_retains_history_xp_invalidates_old_sessions_and_allows_practice(self):
        self.assertTrue(self.data()['is_complete'])
        response=self.client.post(f'/api/mobile/v1/paths/{self.path.pk}/restart/',{},format='json')
        self.assertEqual(response.status_code,200);self.assertEqual(response.data['completed'],0)
        self.assertEqual(QuestionAttempt.objects.count(),1);self.assertEqual(XPTransaction.objects.get().amount,20)
        self.assertEqual(self.client.post(f'/api/mobile/v1/sessions/{self.session.pk}/answer/',{'question_id':self.q.pk,'answer':['a']},format='json').status_code,404)
        self.assertEqual(self.client.get(f'/api/mobile/v1/sessions/{self.session.pk}/').status_code,404)
        session=self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json').data
        self.assertEqual(session['question']['id'],self.q.pk)
        answer=self.client.post(f"/api/mobile/v1/sessions/{session['id']}/answer/",{'question_id':self.q.pk,'answer':['a']},format='json')
        self.assertEqual(answer.status_code,200);self.assertEqual(answer.data['xp_change'],0)

    def test_new_published_question_reopens_without_resetting_completed_questions(self):
        extra=Question.objects.create(kind='choice',prompt='New?',options=[{'id':'b','text':'Yes'}],answer=['b'],published=False)
        self.path.questions.add(extra)
        self.assertTrue(self.data()['is_complete'])
        extra.published=True;extra.save()
        data=self.data();self.assertFalse(data['is_complete']);self.assertEqual(data['remaining_tasks'],1);self.assertEqual(data['completed'],1);self.assertEqual(data['question_count'],2)
        self.assertEqual(self.client.post(f'/api/mobile/v1/paths/{self.path.pk}/restart/',{},format='json').status_code,409)
        session=self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json').data
        self.assertEqual(session['question']['id'],extra.pk)
        self.assertEqual(self.progress.completed.count(),1)

    def test_new_information_card_reopens_even_at_100_percent_question_progress(self):
        card=Question.objects.create(kind='info',prompt='Learn',published=True,card_pages=[{'title':'Info','body':'Risk'}]);self.path.questions.add(card)
        data=self.data();self.assertEqual(data['progress'],100);self.assertFalse(data['is_complete']);self.assertEqual(data['remaining_tasks'],1)
        session=self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json').data
        self.assertEqual(session['question']['kind'],'info')

    def test_restart_is_per_user_and_path_and_enforces_access(self):
        other=get_user_model().objects.create_user(username='other-restart',is_mobile=True)
        other_progress=UserPathProgress.objects.create(user=other,path=self.path);other_progress.completed.add(self.q)
        path=LearningPath.objects.create(title='Other',published=True)
        progress=UserPathProgress.objects.create(user=self.user,path=path);progress.completed.add(self.q)
        self.client.post(f'/api/mobile/v1/paths/{self.path.pk}/restart/',{},format='json')
        self.assertEqual(other_progress.completed.count(),1);self.assertEqual(progress.completed.count(),1)
        self.client.force_authenticate(other)
        self.assertEqual(self.client.post(f'/api/mobile/v1/paths/{self.path.pk}/restart/',{},format='json').status_code,404)
