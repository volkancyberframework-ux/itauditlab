import re
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient
from .models import AccountDeletionRequest, LearningPath, LearningSession, Question, QuestionAttempt, XPTransaction
from .account_deletion import complete_deletion


class ReleaseTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='release-user', email='release@example.com', password='Original-Secure-918', is_mobile=True)
        self.client = APIClient()

    def test_reset_real_email_changes_password_clears_initial_flag_and_invalidates_link(self):
        self.user.mobile_must_change_password=True
        self.user.set_unusable_password(); self.user.save()
        response=self.client.post('/api/mobile/v1/auth/password-reset/',{'email':'RELEASE@example.com'},format='json')
        self.assertEqual(response.status_code,200); self.assertEqual(len(mail.outbox),1)
        link=re.search(r'https://[^\s]+', mail.outbox[0].body).group()
        self.assertTrue(link.startswith('https://www.grcustasi.com/'))
        from urllib.parse import urlparse
        path=urlparse(link).path
        first=self.client.get(path)
        self.assertEqual(first.status_code,302)
        reset=self.client.post(first.url,{'new_password1':'Renewed-Secure-8172','new_password2':'Renewed-Secure-8172'})
        self.assertEqual(reset.status_code,302)
        self.user.refresh_from_db(); self.assertFalse(self.user.mobile_must_change_password)
        self.assertTrue(self.user.check_password('Renewed-Secure-8172'))
        login=self.client.post('/api/mobile/v1/auth/login/',{'email':self.user.email,'password':'Renewed-Secure-8172'},format='json')
        self.assertEqual(login.status_code,200)
        self.assertContains(self.client.get(path),'süresi dolmuş')

    def test_unknown_and_inactive_emails_send_nothing(self):
        absent=self.client.post('/api/mobile/v1/auth/password-reset/',{'email':'absent@example.com'},format='json')
        self.assertEqual(absent.status_code,200); self.assertEqual(len(mail.outbox),0)
        self.user.is_active=False; self.user.save()
        inactive=self.client.post('/api/mobile/v1/auth/password-reset/',{'email':self.user.email},format='json')
        self.assertEqual(inactive.data,absent.data); self.assertEqual(len(mail.outbox),0)

    def test_deletion_needs_password_then_erases_learning_and_login_identity(self):
        self.client.force_authenticate(self.user)
        endpoint='/api/mobile/v1/auth/delete-account/'
        self.assertEqual(self.client.post(endpoint,{'password':'wrong','confirm':True},format='json').status_code,400)
        response=self.client.post(endpoint,{'password':'Original-Secure-918','confirm':True},format='json')
        self.assertEqual(response.status_code,202)
        self.assertEqual(self.client.post(endpoint,{'password':'Original-Secure-918','confirm':True},format='json').status_code,202)
        self.assertEqual(AccountDeletionRequest.objects.count(),1)
        path=LearningPath.objects.create(title='Shared',published=True)
        q=Question.objects.create(prompt='Example',kind='text',answer=['risk'],published=True)
        q.paths.add(path)
        session=LearningSession.objects.create(user=self.user,path=path)
        attempt=QuestionAttempt.objects.create(session=session,question=q,answer={'text':'risk'},is_correct=True,xp_change=10)
        XPTransaction.objects.create(user=self.user,attempt=attempt,amount=10,reason='correct')
        record=AccountDeletionRequest.objects.get(user=self.user)
        self.assertTrue(complete_deletion(record.pk))
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active); self.assertFalse(self.user.is_mobile)
        self.assertEqual(self.user.email,''); self.assertFalse(self.user.has_usable_password())
        self.assertFalse(LearningSession.objects.filter(user=self.user).exists())
        self.assertFalse(XPTransaction.objects.filter(user=self.user).exists())
        self.assertTrue(LearningPath.objects.filter(pk=path.pk).exists())
        self.assertEqual(len(mail.outbox),1)
        self.assertTrue(complete_deletion(record.pk)); self.assertEqual(len(mail.outbox),1)
        record.refresh_from_db(); self.assertEqual(record.email_to_notify,'')

    def test_public_store_urls_exist(self):
        self.assertContains(self.client.get(reverse('landing:mobile_privacy')),'gizlilik politikası')
        self.assertContains(self.client.get(reverse('landing:mobile_support')),'volkan@grcustasi.com')
