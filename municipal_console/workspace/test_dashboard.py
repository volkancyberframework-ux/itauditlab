from accounts.privacy import PRIVACY_VERSION
from django.utils import timezone
import json
from io import BytesIO
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from pypdf import PdfReader
from .models import Organization,Audit,Control,Membership,ResponseRevision,Evaluation

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class DashboardTests(TestCase):
    def setUp(self):
        self.org=Organization.objects.create(name='Torbalı Belediyesi',slug='torbali-belediyesi',subdomain='torbalibld')
        self.audit=Audit.objects.create(organization=self.org,title='Torbalı Denetimi')
        self.admin=get_user_model().objects.create_superuser('test@example.com','Test-Password-784!',must_change_password=False,privacy_accepted_at=timezone.now(),privacy_version=PRIVACY_VERSION)
        self.users={}
        for role in ['it','intern','executive','auditor']:
            u=get_user_model().objects.create_user(role+'@example.com',must_change_password=False,privacy_accepted_at=timezone.now(),privacy_version=PRIVACY_VERSION)
            Membership.objects.create(audit=self.audit,user=u,role=role);self.users[role]=u
        self.c=Control.objects.create(audit=self.audit,code='TB-01',title='Şifreleme ve erişim',description='Özgün kontrol sorusu.',evidence_guidance='Test adımları ve kanıtlar.',risk='high',framework='ISO',theme='Erişim',intern_visible=True)
        self.hidden=Control.objects.create(audit=self.audit,code='TB-02',title='Stajyere kapalı kontrol',risk='medium',framework='NIST',intern_visible=False)
        ResponseRevision.objects.create(control=self.c,actor=self.users['it'],status='partial',explanation='SADECE-YETKİLİ-BT-YANITI')
        Evaluation.objects.create(control=self.c,assessment='noncompliant',deficiency='both',rationale='YÖNETİCİYE-ÖZEL-GÖRÜŞ',private_note='RAPORA-GİRMEYECEK-İÇ-NOT')
    def login(self,role):self.client.force_login(self.admin if role=='admin' else self.users[role],backend='django.contrib.auth.backends.ModelBackend')
    def pdf(self,role):
        self.login(role);response=self.client.get(f'/console/{self.audit.pk}/controls.pdf')
        self.assertEqual(response.status_code,200)
        return ''.join(p.extract_text() for p in PdfReader(BytesIO(response.content)).pages)
    def test_branding_and_host(self):
        self.login('admin');response=self.client.get('/console/',HTTP_HOST='torbalibld.grcustasi.com');self.assertEqual(response.status_code,200);self.assertContains(response,'torbali-belediyesi.gif');self.assertNotContains(response,'GRC Ustası')
    def test_host_scope_blocks_other_tenant_even_for_admin(self):
        audit=Audit.objects.create(organization=Organization.objects.create(name='Other',slug='other'),title='Other')
        c=Control.objects.create(audit=audit,code='OTHER',title='Other control',risk='high');self.login('admin')
        self.assertEqual(self.client.get(f'/console/{audit.pk}/controls/{c.pk}/',HTTP_HOST='torbalibld.grcustasi.com').status_code,404)
        self.assertEqual(self.client.get(f'/console/{audit.pk}/controls.pdf',HTTP_HOST='torbalibld.grcustasi.com').status_code,404)
    def test_charts_match_current_records(self):
        self.login('executive');r=self.client.get('/console/');d=r.context['charts']
        self.assertEqual(d['responses']['values'],[0,1,0,0,1]);self.assertEqual(d['risks']['values'],[1,1,0]);self.assertEqual(d['evaluations']['values'],[0,0,1,1])
    def test_it_chart_payload_has_no_evaluations(self):
        self.login('it');r=self.client.get('/console/');self.assertNotIn('evaluations',r.context['charts']);self.assertNotContains(r,'YÖNETİCİYE-ÖZEL-GÖRÜŞ')
    def test_intern_chart_payload_is_metadata_only(self):
        self.login('intern');r=self.client.get('/console/');d=r.context['charts'];self.assertEqual(set(d),{'risks','frameworks'});self.assertEqual(sum(d['risks']['values']),1);self.assertNotContains(r,'SADECE-YETKİLİ-BT-YANITI')
    def test_pdf_it_excludes_evaluation(self):
        text=self.pdf('it');self.assertIn('Torbalı Belediyesi',text);self.assertIn('SADECE-YETKİLİ-BT-YANITI',text);self.assertNotIn('YÖNETİCİYE-ÖZEL-GÖRÜŞ',text);self.assertNotIn('RAPORA-GİRMEYECEK-İÇ-NOT',text)
    def test_pdf_executive_includes_evaluation_not_private_notes(self):
        text=self.pdf('executive');self.assertIn('YÖNETİCİYE-ÖZEL-GÖRÜŞ',text);self.assertNotIn('RAPORA-GİRMEYECEK-İÇ-NOT',text)
    def test_pdf_admin_also_omits_private_notes(self):self.assertNotIn('RAPORA-GİRMEYECEK-İÇ-NOT',self.pdf('admin'))
    def test_pdf_intern_only_visible_definitions(self):
        text=self.pdf('intern');self.assertIn('Özgün kontrol sorusu',text);self.assertNotIn('Stajyere kapalı kontrol',text);self.assertNotIn('SADECE-YETKİLİ-BT-YANITI',text);self.assertNotIn('YÖNETİCİYE-ÖZEL-GÖRÜŞ',text)
    def test_pdf_requires_login(self):self.assertEqual(self.client.get(f'/console/{self.audit.pk}/controls.pdf').status_code,302)
    def test_login_brand_without_platform_name(self):
        r=self.client.get('/signin/',HTTP_HOST='torbalibld.grcustasi.com');self.assertContains(r,'Torbalı Belediyesi');self.assertNotContains(r,'GRC Ustası');self.assertContains(r,'torbali-belediyesi.gif')
    def test_charts_ignore_table_filter(self):
        self.login('admin');r=self.client.get('/console/?q=Şifreleme');self.assertEqual(len(r.context['rows']),1);self.assertEqual(sum(r.context['charts']['responses']['values']),2)
