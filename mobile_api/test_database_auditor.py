import hashlib,json
from collections import Counter
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase,override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .database_auditor import seed,assign_paid,package
from .models import LearningPath,Question,UserPathProgress,QuestionAttempt,XPTransaction,Subscription

@patch('mobile_api.views.MobileThrottle.allow_request',return_value=True)
class DatabaseAuditTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.path=LearningPath.objects.get(pk=seed(dry_run=False)['path_id'])
        self.user=get_user_model().objects.create_user(username='db-paid',email='db-paid@example.test',is_mobile=True,mobile_full_access=True,mobile_email_verified=True)
        self.client=APIClient();self.client.force_authenticate(self.user)

    def complete(self,prefix):
        first=None
        for chapter in range(1,6):
            state=self.client.post(prefix+'sessions/',{'path_id':self.path.pk},format='json')
            self.assertEqual(state.status_code,201,state.data);state=state.data
            self.assertEqual(state['total'],11)
            resume=self.client.post(prefix+'sessions/',{'path_id':self.path.pk},format='json')
            self.assertEqual(resume.data['id'],state['id'])
            for offset in range(11):
                q=state['question'];model=self.path.questions.get(pk=q['id'])
                self.assertEqual(model.module.order,chapter);self.assertEqual(model.order,(chapter-1)*11+offset+1)
                self.assertEqual(q['kind'],'image');self.assertTrue(q['image'])
                self.assertNotIn('answer',q)
                image=self.client.get(q['image']);self.assertEqual(image.status_code,200)
                self.assertEqual(hashlib.sha256(b''.join(image.streaming_content)).hexdigest(),package()[1][model.order-1]['sha256'])
                payload={'question_id':model.pk,'answer':model.answer}
                response=self.client.post(f'{prefix}sessions/{state["id"]}/answer/',payload,format='json')
                self.assertEqual(response.status_code,200,response.data);self.assertTrue(response.data['correct'])
                for label in ('Doğru yanıt','Teknik gerekçe','Risk','İş etkisi','Önerilen kontrol'):
                    self.assertIn(label,response.data['explanation'])
                if first is None:first=(state['id'],payload)
                state=response.data['session']
                self.assertEqual(state['path']['progress'],round(model.order/55*100))
                self.assertEqual(state['path']['completed'],model.order)
            self.assertTrue(state['complete'])
        self.assertTrue(state['path']['is_complete']);self.assertEqual(state['path']['progress'],100)
        again=self.client.post(f'{prefix}sessions/{first[0]}/answer/',first[1],format='json')
        self.assertEqual(again.status_code,200)
        self.assertEqual(QuestionAttempt.objects.filter(session__user=self.user).count(),55)
        self.assertEqual(XPTransaction.objects.filter(user=self.user).count(),55)
        self.assertEqual(UserPathProgress.objects.get(user=self.user,path=self.path).completed.count(),55)

    def test_all_55_native_questions_images_feedback_progress_and_resume(self,_throttle):
        self.complete('/api/mobile/v1/')

    @override_settings(ROOT_URLCONF='mobile_web.urls')
    def test_all_55_web_questions_images_feedback_progress_and_resume(self,_throttle):
        listing=self.client.get('/web-api/paths/')
        data=next(p for p in listing.data if p['id']==self.path.pk)
        self.assertTrue(data['show_path_percentage']);self.assertEqual(data['session_size'],11)
        self.complete('/web-api/')

    def test_wrong_answer_and_out_of_order_submission(self,_throttle):
        state=self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json').data
        other=self.path.questions.get(order=2)
        bad=self.client.post(f'/api/mobile/v1/sessions/{state["id"]}/answer/',{'question_id':other.pk,'answer':other.answer},format='json')
        self.assertEqual(bad.status_code,400)
        result=self.client.post(f'/api/mobile/v1/sessions/{state["id"]}/answer/',{'question_id':state['question']['id'],'answer':['b']},format='json')
        self.assertFalse(result.data['correct']);self.assertEqual(result.data['xp_change'],0)
        self.assertIn('Diğer yanıtların',result.data['explanation']);self.assertEqual(result.data['session']['path']['progress'],0)

    def test_free_and_anonymous_access_is_denied(self,_throttle):
        free=get_user_model().objects.create_user(username='db-free',is_mobile=True,mobile_email_verified=True)
        self.client.force_authenticate(free)
        self.assertNotIn(self.path.pk,[p['id'] for p in self.client.get('/api/mobile/v1/paths/').data])
        self.assertEqual(self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json').status_code,403)
        self.assertEqual(self.client.get(f'/api/mobile/v1/questions/{self.path.questions.first().pk}/image/').status_code,404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f'/api/mobile/v1/questions/{self.path.questions.first().pk}/image/').status_code,401)

    def test_assignment_includes_lifetime_monthly_and_store_subscriptions(self,_throttle):
        User=get_user_model();now=timezone.now()
        monthly=User.objects.create_user(username='db-monthly',is_mobile=True,mobile_paid_until=now+timedelta(days=3))
        store=User.objects.create_user(username='db-store',is_mobile=True)
        expired=User.objects.create_user(username='db-expired',is_mobile=True,mobile_paid_until=now-timedelta(days=1))
        Subscription.objects.create(user=store,provider='apple',transaction_id='db-store-transaction',status='active',expires_at=now+timedelta(days=3),verified_at=now)
        existing=set(UserPathProgress.objects.filter(path=self.path).values_list('user_id',flat=True))
        self.assertEqual(assign_paid(self.path),3);self.assertEqual(assign_paid(self.path),0)
        self.assertEqual(set(UserPathProgress.objects.filter(path=self.path).values_list('user_id',flat=True)),existing|{self.user.pk,monthly.pk,store.pk})
        self.assertFalse(UserPathProgress.objects.filter(user=expired,path=self.path).exists())

    def test_existing_linux_content_progress_and_assets_are_untouched(self,_throttle):
        from .linux_auditor import seed as linux_seed
        linux=LearningPath.objects.get(pk=linux_seed(dry_run=False)['path_id'])
        progress,_=UserPathProgress.objects.get_or_create(user=self.user,path=linux)
        q=linux.questions.first();progress.completed.add(q)
        before=list(linux.questions.order_by('pk').values());prefs=linux.preferences.copy()
        # Reseed with an existing database answer; neither course is replaced.
        own_progress,_=UserPathProgress.objects.get_or_create(user=self.user,path=self.path)
        own_progress.completed.add(self.path.questions.first())
        self.assertEqual(seed(dry_run=False)['create'],0)
        linux.refresh_from_db();self.assertEqual(linux.preferences,prefs)
        self.assertEqual(list(linux.questions.order_by('pk').values()),before)
        self.assertEqual(list(progress.completed.values_list('pk',flat=True)),[q.pk])
        self.assertEqual(own_progress.completed.count(),1)
        self.assertEqual(linux_seed(dry_run=False)['create'],0)

    def test_unique_evidence_coverage_and_admin_edit_protection(self,_throttle):
        p,images=package()
        self.assertEqual(Counter(q['engine'] for q in p['questions']),{'PG':14,'MY':13,'MS':14,'OR':14})
        self.assertEqual(len({q['evidence']['output'] for q in p['questions']}),55)
        self.assertEqual(len({m['sha256'] for m in images}),55)
        q=self.path.questions.first();q.explanation='Admin revision';q.save()
        with self.assertRaises(ValidationError):seed(dry_run=False)
        q.refresh_from_db();self.assertEqual(q.explanation,'Admin revision')
