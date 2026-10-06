from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import MotivationMessage, MobileSettings, MobileAdminAlert, LearningPath, LearningSession, Question, QuestionAttempt, VoiceSubmission
from .alerts import deliver_alert

class EngagementTests(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user(username='engage',email='engage@example.com',password='Strong-Example-456',is_mobile=True,mobile_full_access=True)
        self.client=APIClient();self.client.force_authenticate(self.user)

    def test_one_daily_message_and_special_date_overrides_rotation(self):
        MotivationMessage.objects.all().delete()
        MotivationMessage.objects.create(body='General')
        MotivationMessage.objects.create(body='Draft',published=False)
        today=timezone.localdate()
        MotivationMessage.objects.create(body='Today special',day=today)
        plan=self.client.get('/api/mobile/v1/notifications/plan/').data
        self.assertEqual(len(plan['days']),60)
        self.assertEqual(len(set(day['date'] for day in plan['days'])),60)
        self.assertEqual(plan['days'][0]['body'],'Today special')
        self.assertEqual(plan['days'][1]['body'],'General')
        config,_=MobileSettings.objects.get_or_create(pk=1);config.notifications_enabled=False;config.save()
        self.assertEqual(self.client.get('/api/mobile/v1/notifications/plan/').data['days'],[])
        self.assertEqual(self.client.get('/api/mobile/v1/notifications/plan/?timezone=unknown').status_code,400)

    def test_activity_graph_and_user_isolation(self):
        path=LearningPath.objects.create(title='Daily',published=True)
        question=Question.objects.create(prompt='Activity',kind='choice',published=True)
        session=LearningSession.objects.create(user=self.user,path=path)
        attempt=QuestionAttempt.objects.create(session=session,question=question,answer=[],is_correct=True,xp_change=20)
        QuestionAttempt.objects.filter(pk=attempt.pk).update(created_at=timezone.now()-timedelta(days=1))
        other=get_user_model().objects.create_user(username='daily-other',is_mobile=True)
        second=LearningSession.objects.create(user=other,path=path)
        QuestionAttempt.objects.create(session=second,question=question,answer=[],is_correct=True,xp_change=99)
        data=self.client.get('/api/mobile/v1/activity/').data
        self.assertEqual(len(data['days']),28);self.assertEqual(data['active_days'],1);self.assertEqual(data['streak'],1)
        self.assertEqual(data['today_tasks'],0);self.assertEqual(data['days'][-2]['xp'],20)
        self.assertEqual(sum(day['xp'] for day in data['days']),20)

    def test_removed_personal_path_endpoint_and_old_personal_paths_hidden(self):
        path=LearningPath.objects.create(title='Old personal',published=True,owner=self.user)
        self.assertEqual(self.client.post('/api/mobile/v1/paths/personalize/',{},format='json').status_code,404)
        self.assertNotIn(path.pk,[p['id'] for p in self.client.get('/api/mobile/v1/paths/').data])

    def test_signup_alert_sends_once_and_failure_can_retry(self):
        with patch('skool.services.send_telegram',return_value=True) as send:
            with self.captureOnCommitCallbacks(execute=True):
                user=get_user_model().objects.create_user(username='alert-signup',email='signup@example.com',is_mobile=True)
            alert=MobileAdminAlert.objects.get(key=f'signup-{user.pk}')
            self.assertIsNotNone(alert.sent_at);self.assertIn('/bulamazsinki/core/customuser/',alert.text)
            user.first_name='Changed';user.save();deliver_alert(alert.pk)
            self.assertEqual(send.call_count,1)
        alert=MobileAdminAlert.objects.create(key='failed',text='Retry')
        with patch('skool.services.send_telegram',side_effect=Exception):
            self.assertFalse(deliver_alert(alert.pk))
        alert.refresh_from_db();self.assertIsNone(alert.sent_at);self.assertTrue(alert.last_error)
        with patch('skool.services.send_telegram',return_value=True):self.assertTrue(deliver_alert(alert.pk))

    def test_voice_alert_contains_review_link_and_is_not_sent_again_on_save(self):
        path=LearningPath.objects.create(title='Voice',published=True)
        q=Question.objects.create(kind='voice',prompt='Risk?',published=True)
        session=LearningSession.objects.create(user=self.user,path=path)
        attempt=QuestionAttempt.objects.create(session=session,question=q,answer={},is_correct=False)
        with patch('skool.services.send_telegram',return_value=True) as send:
            with self.captureOnCommitCallbacks(execute=True):
                voice=VoiceSubmission.objects.create(attempt=attempt,file='test.m4a',duration=1)
            voice.save();self.assertEqual(send.call_count,1)
        alert=MobileAdminAlert.objects.get(key=f'voice-{voice.pk}')
        self.assertIn(f'/voicesubmission/{voice.pk}/change/',alert.text)
        self.assertIn('24 saat',alert.text)

    def test_manual_create_mobile_user_hashes_password_and_requires_add_permission(self):
        admin=get_user_model().objects.create_superuser(username='mobile-admin',email='admin@example.com',password='Strong-Admin-567')
        self.client.force_login(admin)
        with self.captureOnCommitCallbacks(execute=True),patch('skool.services.send_telegram',return_value=True):
            response=self.client.post('/bulamazsinki/core/customuser/create-mobile-user/',{'name':'Manual Student','email':'manual@example.com','password':'Strong-Manual-678'})
        self.assertEqual(response.status_code,302)
        user=get_user_model().objects.get(email='manual@example.com')
        self.assertTrue(user.is_mobile);self.assertTrue(user.check_password('Strong-Manual-678'));self.assertFalse(user.is_staff or user.mobile_full_access)
        staff=get_user_model().objects.create_user(username='restricted-staff',is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get('/bulamazsinki/core/customuser/create-mobile-user/').status_code,403)

    def test_free_path_tick_replaces_previous_selection_and_preserves_list_edits(self):
        from django.test import RequestFactory
        from django.contrib.admin.sites import AdminSite
        from .admin import PathForm, PathAdmin
        first=LearningPath.objects.create(title='First',published=True)
        second=LearningPath.objects.create(title='Second',published=True)
        config,_=MobileSettings.objects.get_or_create(pk=1)
        config.free_path=first; config.save()
        self.assertTrue(PathForm(instance=first).fields['free_for_mobile'].initial)
        self.assertFalse(PathForm(instance=second).fields['free_for_mobile'].initial)
        from types import SimpleNamespace
        form=SimpleNamespace(cleaned_data={'free_for_mobile': True})
        admin=PathAdmin(LearningPath,AdminSite())
        admin.save_model(RequestFactory().post('/',{}),second,form,True)
        config.refresh_from_db(); self.assertEqual(config.free_path,second)
        admin.save_model(RequestFactory().post('/',{'form-TOTAL_FORMS':1}),second,SimpleNamespace(cleaned_data={'free_for_mobile':False}),True)
        config.refresh_from_db(); self.assertEqual(config.free_path,second)
        admin.save_model(RequestFactory().post('/',{}),second,SimpleNamespace(cleaned_data={'free_for_mobile':False}),True)
        config.refresh_from_db(); self.assertIsNone(config.free_path)
