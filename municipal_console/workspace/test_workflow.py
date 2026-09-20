from accounts.privacy import PRIVACY_VERSION
from django.utils import timezone
from io import BytesIO
from datetime import timedelta
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.management import call_command
from pypdf import PdfReader
from .models import *

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class WorkflowTests(TestCase):
    def setUp(self):
        U=get_user_model()
        self.admin=U.objects.create_superuser('demo@grcustasi.local','Long-Test-Password!',must_change_password=False,privacy_accepted_at=timezone.now(),privacy_version=PRIVACY_VERSION)
        self.audit=Audit.objects.create(organization=Organization.objects.create(name='Test Belediyesi',slug='test'),title='Akış',is_demo=True)
        self.control=Control.objects.create(audit=self.audit,code='GRC-001',title='İş süreçleri ve güvenlik',description='Test açıklaması',risk='medium',intern_visible=True)
        self.users={}
        for role in ['it','executive','auditor','intern']:
            user=U.objects.create_user(f'{role}@example.com','Long-Test-Password!',must_change_password=False,privacy_accepted_at=timezone.now(),privacy_version=PRIVACY_VERSION)
            Membership.objects.create(user=user,audit=self.audit,role=role);self.users[role]=user
        self.url=f'/console/{self.audit.pk}/workflow/'
    def login(self,role):self.client.force_login(self.admin if role=='admin' else self.users[role],backend='django.contrib.auth.backends.ModelBackend')
    def post(self,action,**data):return self.client.post(self.url,{'action':action,**data})
    def answer(self):
        self.login('it');return self.post('answer',control=self.control.pk,status='partial',explanation='Örnek BT yanıtı',declaration='on')
    def fieldwork(self):
        self.answer();self.login('auditor');self.post('phase',target='fieldwork')
        when=timezone.localtime(timezone.now()+timedelta(days=3)).strftime('%Y-%m-%dT%H:%M')
        self.post('appointment',when=when,note='BT ekibi ile telefonla görüşüldü.');self.login('it');self.post('confirm_appointment')
    def evaluate(self,status='partial'):
        self.login('auditor');return self.post('evaluate',control=self.control.pk,assessment=status,deficiency='both',verified='on',rationale='YÖNETİCİYE-GİZLİ-GÖRÜŞ',private_note='EKİP-ÖZEL-NOT',recommendation='Erişim yetkilerini gözden geçirin; kanıt özetini paylaşın.')
    def test_initial_unanswered_and_inline_form(self):
        self.login('it');r=self.client.get('/console/');self.assertContains(r,'Başlanmadı');self.assertContains(r,'GRC-001 yanıtını düzenle');self.assertNotContains(r,'Denetçi görüşü')
    def test_auditor_can_start_fieldwork_without_answers(self):
        self.login('admin');self.post('phase',target='fieldwork');self.audit.refresh_from_db();self.assertEqual(self.audit.phase,'fieldwork')
    def test_inline_answer_and_revision(self):
        self.answer();self.post('answer',control=self.control.pk,status='implemented',explanation='Yeni açıklama',declaration='on');self.assertEqual(self.control.revisions.count(),2)
    def test_readonly_roles_cannot_answer(self):
        for role in ['executive','intern','auditor','admin']:
            self.login(role);self.assertEqual(self.post('answer',control=self.control.pk,status='partial',explanation='Açıklama',declaration='on').status_code,403)
    def test_invalid_answer_preserves_text(self):
        self.login('it');r=self.post('answer',control=self.control.pk,status='partial',explanation='Korunacak açıklama');self.assertEqual(r.status_code,400);self.assertContains(r,'Korunacak açıklama',status_code=400)
    def test_evaluation_available_from_first_phase(self):
        self.evaluate();self.assertTrue(Evaluation.objects.exists());self.assertTrue(Evaluation.objects.get().verified)
        self.answer();self.assertFalse(Evaluation.objects.get().verified)
    def test_appointment_counter_and_confirmation(self):
        self.answer();self.login('admin');self.post('phase',target='fieldwork')
        when=timezone.localtime(timezone.now()+timedelta(days=4)).strftime('%Y-%m-%dT%H:%M')
        self.login('it');self.post('appointment',when=when,note='Başka saat öneriyoruz.');self.post('confirm_appointment');self.audit.refresh_from_db();self.assertEqual(self.audit.appointment_status,'counter')
        self.login('auditor');self.post('confirm_appointment');self.audit.refresh_from_db();self.assertEqual(self.audit.appointment_status,'confirmed')
    def test_response_remains_editable_after_phase1(self):
        self.fieldwork();self.login('it');self.post('answer',control=self.control.pk,status='missing',explanation='Sonra',declaration='on');self.assertEqual(self.control.revisions.count(),2)
    def test_noncompliance_creates_single_finding(self):
        self.fieldwork();self.evaluate();self.evaluate('noncompliant');self.assertEqual(Finding.objects.count(),1);self.assertEqual(Finding.objects.get().severity,'high')
    def test_compliant_creates_no_finding(self):
        self.fieldwork();self.evaluate('compliant');self.assertFalse(Finding.objects.exists())
    def test_rationale_only_management_and_team(self):
        self.fieldwork();self.evaluate()
        for role in ['it','intern']:
            self.login(role)
            for url in ['/console/',f'/console/{self.audit.pk}/controls/{self.control.pk}/']:
                self.assertNotContains(self.client.get(url),'YÖNETİCİYE-GİZLİ-GÖRÜŞ')
        self.login('executive');self.assertContains(self.client.get('/console/'),'YÖNETİCİYE-GİZLİ-GÖRÜŞ');self.assertNotContains(self.client.get('/console/'),'EKİP-ÖZEL-NOT')
    def test_it_cannot_evaluate(self):
        self.fieldwork();self.login('it');self.assertEqual(self.post('evaluate',control=self.control.pk,assessment='compliant',rationale='x').status_code,403)
    def test_dispute_remediation_and_close_full_lifecycle(self):
        self.fieldwork();self.evaluate();finding=Finding.objects.get()
        self.login('auditor');self.post('phase',target='remediation')
        self.login('it');self.post('finding',finding=finding.pk,finding_action='dispute',explanation='Kapsama ilişkin itiraz.')
        finding.refresh_from_db();self.assertEqual(finding.status,'disputed')
        self.login('auditor');self.post('finding',finding=finding.pk,finding_action='reject',explanation='Kapsam doğrulandı; giderim gerekli.')
        self.login('it');self.post('finding',finding=finding.pk,finding_action='remediate',explanation='Yetkiler kaldırıldı, kayıtlar hazır.')
        self.login('auditor');self.post('finding',finding=finding.pk,finding_action='close',explanation='Kanıt kontrol edildi.')
        finding.refresh_from_db();self.assertEqual(finding.status,'closed');self.assertEqual(finding.updates.count(),4)
        self.post('phase',target='completed');self.audit.refresh_from_db();self.assertEqual(self.audit.phase,'completed');self.assertTrue(Activity.objects.filter(audit=self.audit).exists())
    def test_open_findings_block_completion(self):
        self.fieldwork();self.evaluate();self.post('phase',target='remediation');self.post('phase',target='completed');self.audit.refresh_from_db();self.assertEqual(self.audit.phase,'remediation')
    def test_it_cannot_close(self):
        self.fieldwork();self.evaluate();self.login('it');self.assertEqual(self.post('finding',finding=Finding.objects.get().pk,finding_action='close',explanation='İzinsiz').status_code,403)
    def test_suggestion_and_acceptance(self):
        self.login('intern');self.post('suggest',title='Yeni öneri',framework='ISO teması',description='Özgün kontrol sorusu',test_steps='1. Sistem listesini alın. 2. Örneklem belirleyin. 3. Kanıtları karşılaştırın.')
        suggestion=Suggestion.objects.get();self.login('auditor');self.post('review_suggestion',suggestion=suggestion.pk,decision='accepted',note='Uygun test adımları.')
        suggestion.refresh_from_db();self.assertEqual(suggestion.status,'accepted');self.assertEqual(self.audit.controls.count(),2);self.assertFalse(suggestion.control.revisions.exists())
    def test_invalid_suggestion_rejected(self):
        self.login('intern');r=self.post('suggest',title='Başlık',framework='ISO',description='Test',test_steps='Kısa');self.assertEqual(r.status_code,400);self.assertFalse(Suggestion.objects.exists())
    def test_only_intern_can_propose(self):
        self.login('it');self.assertEqual(self.post('suggest').status_code,403)
    def test_pdf_authorization_and_privacy(self):
        self.fieldwork();self.evaluate();url=f'/console/{self.audit.pk}/findings.pdf'
        self.login('it');response=self.client.get(url);self.assertEqual(response['Content-Type'],'application/pdf');text=''.join(p.extract_text() for p in PdfReader(BytesIO(response.content)).pages)
        self.assertIn('Test Belediyesi',text);self.assertIn('gözden',text);self.assertNotIn('YÖNETİCİYE-GİZLİ-GÖRÜŞ',text);self.assertNotIn('EKİP-ÖZEL-NOT',text)
        self.login('intern');self.assertEqual(self.client.get(url).status_code,404)
    def test_cross_tenant_write_and_pdf_denied(self):
        other=Audit.objects.create(organization=Organization.objects.create(name='Başka',slug='other'),title='Other');self.login('it')
        self.assertEqual(self.client.post(f'/console/{other.pk}/workflow/',{'action':'answer','control':self.control.pk}).status_code,404)
        self.assertEqual(self.client.get(f'/console/{other.pk}/findings.pdf').status_code,404)
    @override_settings(DEBUG=True)
    def test_demo_role_write_attributed_to_admin(self):
        self.login('admin');self.client.post('/console/view-as/',{'role':'it'});self.post('answer',control=self.control.pk,status='implemented',explanation='Demo yanıt',declaration='on');self.assertEqual(ResponseRevision.objects.get().actor,self.admin);self.assertEqual(Activity.objects.get().role,'it')
    @override_settings(DEBUG=False)
    def test_production_preview_cannot_write(self):
        self.login('admin');session=self.client.session;session['view_as']='it';session.save()
        with override_settings(SECURE_SSL_REDIRECT=False):self.assertEqual(self.post('answer',control=self.control.pk,status='implemented',explanation='Demo yanıt',declaration='on').status_code,403)
