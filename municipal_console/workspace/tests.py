from django.test import TestCase, override_settings
from django.core.management import call_command
from django.contrib.auth import get_user_model
from .models import Organization, Audit, Membership, Control, ResponseRevision, Evaluation, Finding

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class WorkspaceTests(TestCase):
    def setUp(self):
        U=get_user_model()
        self.admin=U.objects.create_superuser('admin@example.com','Long-Password-33!',must_change_password=False)
        self.org=Organization.objects.create(name='A Kurumu',slug='a')
        self.audit=Audit.objects.create(organization=self.org,title='A Denetimi')
        self.control=Control.objects.create(audit=self.audit,code='A-01',title='Erişim kontrolü',description='Açık tanım',evidence_guidance='Liste',framework='ISO',theme='Erişim',risk='high',intern_visible=True)
        self.hidden=Control.objects.create(audit=self.audit,code='A-02',title='Stajyere gizli kontrol',risk='medium')
        self.users={}
        for role in ['intern','it','executive','auditor']:
            user=U.objects.create_user(f'{role}@example.com','Long-Password-33!',must_change_password=False)
            Membership.objects.create(user=user,audit=self.audit,role=role);self.users[role]=user
        self.rev=ResponseRevision.objects.create(control=self.control,actor=self.users['it'],status='partial',explanation='GİZLİ-MÜŞTERİ-YANITI')
        Evaluation.objects.create(control=self.control,assessment='partial',rationale='PAYLAŞILAN-DEĞERLENDİRME',private_note='ÖZEL-DENETÇİ-NOTU')
        Finding.objects.create(audit=self.audit,title='İÇ-BULGU',recommendation='İç açıklama',severity='high',customer_visible=False)
        self.detail=f'/console/{self.audit.pk}/controls/{self.control.pk}/'
    def login(self,user):self.client.force_login(user,backend='django.contrib.auth.backends.ModelBackend')
    def test_only_admin_can_switch_role(self):
        self.login(self.users['it'])
        self.assertEqual(self.client.post('/console/view-as/',{'role':'admin'}).status_code,403)
        self.assertNotContains(self.client.get('/console/'),'Kullanıcı gözünden bakın')
    def test_switch_requires_post_and_valid_role(self):
        self.login(self.admin)
        self.assertEqual(self.client.get('/console/view-as/').status_code,405)
        self.assertEqual(self.client.post('/console/view-as/',{'role':'invalid'}).status_code,400)
    def test_intern_never_receives_restricted_data(self):
        self.login(self.users['intern'])
        for url in ['/console/',self.detail]:
            response=self.client.get(url)
            self.assertEqual(response.status_code,200)
            for secret in ['GİZLİ-MÜŞTERİ-YANITI','PAYLAŞILAN-DEĞERLENDİRME','ÖZEL-DENETÇİ-NOTU','İÇ-BULGU','Stajyere gizli kontrol']:
                self.assertNotContains(response,secret)
        self.assertEqual(self.client.get(self.detail+'history/').status_code,404)
        self.assertEqual(self.client.get(f'/console/{self.audit.pk}/controls/{self.hidden.pk}/').status_code,404)
    def test_intern_does_not_query_sensitive_tables(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        self.login(self.users['intern'])
        with CaptureQueriesContext(connection) as queries:self.client.get('/console/')
        for q in queries:
            self.assertNotIn('workspace_responserevision',q['sql'])
            self.assertNotIn('workspace_evaluation',q['sql'])
            self.assertNotIn('workspace_finding',q['sql'])
    def test_admin_intern_preview_has_same_restrictions(self):
        self.login(self.admin);self.client.post('/console/view-as/',{'role':'intern'})
        self.assertNotContains(self.client.get(self.detail),'GİZLİ-MÜŞTERİ-YANITI')
        self.assertEqual(self.client.get(self.detail+'history/').status_code,404)
    def test_executive_read_only_and_no_private_notes(self):
        self.login(self.users['executive'])
        response=self.client.get(self.detail)
        self.assertContains(response,'GİZLİ-MÜŞTERİ-YANITI')
        self.assertContains(response,'PAYLAŞILAN-DEĞERLENDİRME')
        self.assertNotContains(response,'ÖZEL-DENETÇİ-NOTU')
        self.assertNotContains(self.client.get('/console/'),'İÇ-BULGU')
        self.assertEqual(self.client.post(self.detail,{'status':'implemented','explanation':'change','declaration':'on'}).status_code,403)
    def test_private_evaluation_not_sent_to_customers(self):
        Evaluation.objects.filter(control=self.control).update(customer_visible=False)
        for role in ['it','intern']:
            self.login(self.users[role]);self.assertNotContains(self.client.get(self.detail),'PAYLAŞILAN-DEĞERLENDİRME')
        self.login(self.users['executive']);self.assertContains(self.client.get(self.detail),'PAYLAŞILAN-DEĞERLENDİRME')
    def test_it_submits_new_revision(self):
        self.login(self.users['it'])
        response=self.client.post(self.detail,{'status':'implemented','explanation':'Yeni açıklama','declaration':'on'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(ResponseRevision.objects.count(),2)
        self.rev.refresh_from_db();self.assertEqual(self.rev.explanation,'GİZLİ-MÜŞTERİ-YANITI')
    def test_it_cannot_overwrite_others_response(self):
        user=get_user_model().objects.create_user('another@example.com',must_change_password=False)
        Membership.objects.create(user=user,audit=self.audit,role='it');self.login(user)
        self.assertEqual(self.client.post(self.detail,{'status':'implemented','explanation':'change','declaration':'on'}).status_code,403)
    def test_declaration_required(self):
        self.login(self.users['it']);self.client.post(self.detail,{'status':'implemented','explanation':'change'})
        self.assertEqual(ResponseRevision.objects.count(),1)
    def test_preview_cannot_write_as_it(self):
        self.login(self.admin);self.client.post('/console/view-as/',{'role':'it'})
        self.assertContains(self.client.get(self.detail),'Önizlemede kayıt kapalı')
        self.assertEqual(self.client.post(self.detail,{'status':'implemented','explanation':'change','declaration':'on'}).status_code,403)
    def test_cross_tenant_and_unassigned_auditor_denied(self):
        b=Audit.objects.create(organization=Organization.objects.create(name='B',slug='b'),title='B Denetimi')
        c=Control.objects.create(audit=b,code='B-1',title='B özel kontrol',risk='high')
        for role in ['intern','it','executive','auditor']:
            self.login(self.users[role])
            self.assertEqual(self.client.get(f'/console/{b.pk}/controls/{c.pk}/').status_code,404)
            self.assertEqual(self.client.get(f'/console/{self.audit.pk}/controls/{c.pk}/').status_code,404)
    def test_assigned_auditor_sees_private_notes(self):
        self.login(self.users['auditor']);self.assertContains(self.client.get(self.detail),'ÖZEL-DENETÇİ-NOTU')
    def test_normal_user_cannot_forge_session_role(self):
        self.login(self.users['intern']);session=self.client.session;session['view_as']='admin';session.save()
        self.assertNotContains(self.client.get(self.detail),'GİZLİ-MÜŞTERİ-YANITI')
    @override_settings(DEBUG=True)
    def test_seed_idempotent(self):
        call_command('seed_workspace');count=Control.objects.count();revisions=ResponseRevision.objects.count()
        call_command('seed_workspace');self.assertEqual(Control.objects.count(),count);self.assertEqual(ResponseRevision.objects.count(),revisions)
    def test_history_model_cannot_be_edited(self):
        with self.assertRaises(ValueError):self.rev.save()
        with self.assertRaises(ValueError):self.rev.delete()

    def test_role_switch_preserves_accessible_detail(self):
        self.login(self.admin)
        response=self.client.post('/console/view-as/',{'role':'intern','next':self.detail})
        self.assertRedirects(response,self.detail)
    def test_role_switch_does_not_redirect_outside_app(self):
        self.login(self.admin)
        response=self.client.post('/console/view-as/',{'role':'it','next':'https://example.net/'})
        self.assertRedirects(response,'/console/')
