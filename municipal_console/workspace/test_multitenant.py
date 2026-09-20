from datetime import timedelta
from io import BytesIO
from unittest.mock import patch
from PIL import Image
from django.test import TestCase,override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core import mail
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from .models import *
from .forms import ResponseForm
from .admin import OrganizationForm
from .notifications import deliver_email
from . import services

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class MultiTenantTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='Yeni Kurum',slug='yeni',subdomain='yenikurum')
        self.audit=Audit.objects.create(organization=self.org,title='Yeni Denetim')
        self.admin=get_user_model().objects.create_superuser('admin@test.local','Long-Password-739!',must_change_password=False)
        self.it=get_user_model().objects.create_user('it@test.local',first_name='Ahmet',must_change_password=False)
        self.it2=get_user_model().objects.create_user('it2@test.local',first_name='Volkan',must_change_password=False)
        for user in (self.it,self.it2):Membership.objects.create(user=user,audit=self.audit,role='it')
        self.control=Control.objects.create(audit=self.audit,code='C01',title='Kontrol',description='Kontrolün detayları',evidence_guidance='Erişim listesi',framework='ISO',risk='high')
    def login(self,user=None):self.client.force_login(user or self.admin,backend='django.contrib.auth.backends.ModelBackend')
    def test_response_rules(self):
        for status,expected in [('implemented',False),('na',False),('partial',True),('missing',True)]:
            self.assertEqual(ResponseForm({'status':status,'explanation':'  ','declaration':'on'}).is_valid(),expected)
        self.assertTrue(ResponseForm({'status':'na','explanation':'Kapsam dışı sistem.','declaration':'on'}).is_valid())
    def test_service_enforces_required_response(self):
        with self.assertRaises(ValidationError):services.answer(self.audit,self.control,self.it,'it',{'status':'implemented','explanation':'','declaration':True})
    def test_named_bt_and_evaluator_editor_visible(self):
        self.login();r=self.client.get('/console/');self.assertContains(r,'BT Sorumlusu (Ahmet, Volkan)');self.assertContains(r,'C01 denetçi görüşünü düzenle')
        self.assertContains(self.client.get(f'/console/{self.audit.pk}/controls/{self.control.pk}/'),'Kontrolü test ettim')
    def test_logo_upload_branding_and_tenant_isolation(self):
        im=BytesIO();Image.new('RGB',(60,30),'green').save(im,format='PNG')
        self.login();r=self.client.post(f'/admin/workspace/organization/{self.org.pk}/change/',{'name':self.org.name,'slug':self.org.slug,'subdomain':self.org.subdomain,'logo':SimpleUploadedFile('logo.png',im.getvalue(),content_type='image/png'),'_save':'Save'})
        self.assertEqual(r.status_code,302);self.org.refresh_from_db();self.assertTrue(self.org.logo_data)
        url=f'/branding/{self.org.pk}/logo/'
        r=self.client.get(url,HTTP_HOST='yenikurum.grcustasi.com');self.assertEqual(r.status_code,200);self.assertEqual(r['Content-Type'],'image/png')
        self.assertEqual(self.client.get(url,HTTP_HOST='yenikurum.grcustasi.com',HTTP_IF_NONE_MATCH=r['ETag']).status_code,304)
        other=Organization.objects.create(name='Other',slug='other',subdomain='other')
        self.assertEqual(self.client.get(url,HTTP_HOST='other.grcustasi.com').status_code,404)
        self.client.logout();r=self.client.get('/signin/',HTTP_HOST='yenikurum.grcustasi.com');self.assertContains(r,self.org.name);self.assertContains(r,url);self.assertNotContains(r,'Torbalı')
    def test_invalid_logo_rejected(self):
        form=OrganizationForm({'name':'bad','slug':'bad','subdomain':'bad'},files={'logo':SimpleUploadedFile('bad.svg',b'<svg onload="evil()"/>',content_type='image/svg+xml')})
        self.assertFalse(form.is_valid());self.assertIn('logo',form.errors)
    def test_audit_selector_authorization(self):
        other=Audit.objects.create(organization=self.org,title='Second')
        self.login(self.it);self.assertEqual(self.client.get(f'/console/?audit={other.pk}').status_code,404)
        Membership.objects.create(audit=other,user=self.it,role='it')
        self.assertContains(self.client.get(f'/console/?audit={other.pk}'),'Second')
        self.assertEqual(self.client.get('/console/').context['audit'].pk,other.pk)
    def test_no_email_before_phase4(self):
        for phase in ('responses','fieldwork','remediation'):
            self.audit.phase=phase;self.audit.save();Control.objects.create(audit=self.audit,code=phase,title='New',risk='low')
        self.assertEqual(ControlEmail.objects.count(),0)
    def test_phase4_email_only_assigned_active_bt_with_details(self):
        self.audit.phase='completed';self.audit.save()
        inactive=get_user_model().objects.create_user('inactive@test.local',is_active=False);Membership.objects.create(user=inactive,audit=self.audit,role='it')
        with self.captureOnCommitCallbacks(execute=True):c=Control.objects.create(audit=self.audit,code='C02',title='Yeni kontrol',description='Detaylar',evidence_guidance='Log dosyası',risk='high')
        self.assertEqual(len(mail.outbox),2);self.assertEqual(ControlEmail.objects.count(),2)
        self.assertIn('Log dosyası',mail.outbox[0].body);self.assertIn('yenikurum.grcustasi.com',mail.outbox[0].body)
        self.assertIn('Detaylar',mail.outbox[0].body)
        c.title='Updated';c.save();self.assertEqual(ControlEmail.objects.count(),2)
    def test_control_creation_rollback_discards_email(self):
        self.audit.phase='completed';self.audit.save()
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    Control.objects.create(audit=self.audit,code='ROLL',title='Rollback',risk='low')
                    raise ValueError()
            except ValueError:pass
        self.assertFalse(ControlEmail.objects.exists());self.assertFalse(Control.objects.filter(code='ROLL').exists())
    def test_failed_email_retried_without_duplicate_after_success(self):
        self.audit.phase='completed';self.audit.save()
        Control.objects.create(audit=self.audit,code='C02',title='Retry',risk='high')
        item=ControlEmail.objects.first()
        with patch('workspace.notifications.send_mail',side_effect=OSError('SMTP down')):deliver_email(item.pk)
        item.refresh_from_db();self.assertIsNone(item.delivered_at)
        deliver_email(item.pk);deliver_email(item.pk);self.assertEqual(len(mail.outbox),1)
    def test_draft_requires_final_test_before_phase3(self):
        self.audit.phase='fieldwork';self.audit.save()
        services.answer(self.audit,self.control,self.it,'it',{'status':'missing','explanation':'','declaration':True})
        services.evaluate(self.audit,self.control,self.admin,'auditor',{'assessment':'compliant','rationale':'İnceleme','recommendation':'','verified':False})
        with self.assertRaises(ValidationError):services.transition(self.audit,self.admin,'auditor','remediation')
        services.evaluate(self.audit,self.control,self.admin,'auditor',{'assessment':'compliant','rationale':'Test edildi','recommendation':'','verified':True})
        services.transition(self.audit,self.admin,'auditor','remediation')
        services.answer(self.audit,self.control,self.it,'it',{'status':'missing','explanation':'','declaration':True})
        self.assertFalse(Evaluation.objects.get(control=self.control).verified)
    def test_risk_acceptance_requires_manager_and_preserves_due_date(self):
        f=Finding.objects.create(audit=self.audit,control=self.control,title='Eksik',severity='high')
        due=timezone.localdate()+timedelta(days=10)
        services.finding_action(self.audit,f,self.it,'it','plan','Plan var',due_date=due)
        f.refresh_from_db();self.assertEqual(f.due_date,due);self.assertEqual(f.treatment,'mitigate')
        services.finding_action(self.audit,f,self.it,'it','request_risk','Yapılmayacak')
        with self.assertRaises(PermissionDenied):services.finding_action(self.audit,f,self.it,'it','accept_risk','Kabul')
        services.finding_action(self.audit,f,self.admin,'executive','accept_risk','Yönetici kararı')
        f.refresh_from_db();self.assertEqual(f.status,'risk_accepted');self.assertEqual(f.due_date,due)
        self.assertEqual(f.updates.count(),3)
    def test_due_date_required_for_plan(self):
        f=Finding.objects.create(audit=self.audit,title='Eksik',severity='high')
        with self.assertRaises(ValidationError):services.finding_action(self.audit,f,self.it,'it','plan','Plan')
    def test_new_control_allowed_in_fieldwork_via_admin(self):
        self.audit.phase='fieldwork';self.audit.save();self.login()
        r=self.client.post('/admin/workspace/control/add/',{'audit':self.audit.pk,'code':'NEW','title':'Yeni','description':'Tanım','evidence_guidance':'Kanıt','framework':'ISO','theme':'Erişim','risk':'medium','_save':'Save'})
        self.assertEqual(r.status_code,302);self.assertTrue(Control.objects.filter(code='NEW').exists());self.assertFalse(ControlEmail.objects.exists())
