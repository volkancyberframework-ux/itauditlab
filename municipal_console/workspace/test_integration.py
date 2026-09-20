from accounts.privacy import PRIVACY_VERSION
from django.utils import timezone
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from .models import Organization, Audit, Control, Notification, ResponseRevision, Evaluation
from . import services
from .notifications import deliver,queue

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class IntegrationTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='Torbalı',slug='torbali',subdomain='torbalibld')
        self.audit=Audit.objects.create(organization=self.org,title='Denetim',phase='completed')
        self.user=get_user_model().objects.create_superuser('admin@example.com','Strong-Password-784!',must_change_password=False,privacy_accepted_at=timezone.now(),privacy_version=PRIVACY_VERSION)
        self.c=Control.objects.create(audit=self.audit,code='T1',title='Test',risk='high')
    def test_unknown_tenant_rejected(self):self.assertEqual(self.client.get('/signin/',HTTP_HOST='unknown.grcustasi.com').status_code,404)
    def test_subdomain_change_takes_effect(self):
        self.org.subdomain='newtown';self.org.save()
        self.assertEqual(self.client.get('/signin/',HTTP_HOST='torbalibld.grcustasi.com').status_code,404)
        self.assertEqual(self.client.get('/signin/',HTTP_HOST='newtown.grcustasi.com').status_code,200)
    def test_continuous_control_preserves_revisions(self):
        data={'status':'implemented','explanation':'İlk yanıt','declaration':True}
        services.answer(self.audit,self.c,self.user,'it',data)
        services.answer(self.audit,self.c,self.user,'it',{**data,'explanation':'Güncel yanıt'})
        self.assertEqual(ResponseRevision.objects.filter(control=self.c).count(),2)
    def test_continuous_evaluation_reopens_findings(self):
        data={'assessment':'noncompliant','deficiency':'both','rationale':'Yeni eksik','private_note':'Gizli not','recommendation':'Düzelt'}
        services.evaluate(self.audit,self.c,self.user,'auditor',data.copy())
        finding=self.c.finding;finding.status='closed';finding.save()
        services.evaluate(self.audit,self.c,self.user,'auditor',data.copy())
        finding.refresh_from_db();self.assertEqual(finding.status,'open')
        self.assertFalse(Notification.objects.filter(message__contains='Gizli not').exists())
    @override_settings(TELEGRAM_BOT_TOKEN='test',TELEGRAM_CHAT_ID='test')
    @patch('workspace.notifications.send',return_value=False)
    def test_failure_kept_for_retry(self,send):
        item=Notification.objects.create(message='Test');deliver(item.pk);item.refresh_from_db()
        self.assertIsNone(item.delivered_at);self.assertEqual(item.attempts,1)
        send.return_value=True;deliver(item.pk);deliver(item.pk);item.refresh_from_db()
        self.assertIsNotNone(item.delivered_at);self.assertEqual(send.call_count,2)
    @patch('workspace.notifications.send',return_value=True)
    def test_queue_waits_for_commit(self,send):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:queue('İşlem')
        self.assertEqual(len(callbacks),1);send.assert_not_called()
    def test_admin_and_cookie_isolation(self):
        self.client.force_login(self.user,backend='django.contrib.auth.backends.ModelBackend')
        self.assertIn('municipal_sessionid',self.client.cookies)
        self.assertNotIn('sessionid',self.client.cookies)
        self.assertEqual(self.client.get('/admin/workspace/organization/').status_code,200)
        self.assertEqual(self.client.get('/admin/accounts/user/?q=admin').status_code,200)
    def test_central_admin_creates_independent_user(self):
        self.client.force_login(self.user,backend='django.contrib.auth.backends.ModelBackend')
        response=self.client.post('/admin/accounts/user/add/',{'email':'new@example.com','password1':'New-Strong-Password-739!','password2':'New-Strong-Password-739!','usable_password':'true','_save':'Save'})
        self.assertEqual(response.status_code,302)
        user=get_user_model().objects.get(email='new@example.com')
        self.assertTrue(user.check_password('New-Strong-Password-739!'))
        self.assertTrue(user.must_change_password)
