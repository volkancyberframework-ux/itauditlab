from datetime import timedelta
from urllib.parse import urlsplit, parse_qs
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from accounts.privacy import PRIVACY_VERSION
from .models import *
from .cards import digest, pending_controls

@override_settings(SECURE_SSL_REDIRECT=False, STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class CardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.org=Organization.objects.create(name='Kart Kurumu',slug='cards',subdomain='cards')
        self.audit=Audit.objects.create(organization=self.org,title='Kart Denetimi')
        self.admin=get_user_model().objects.create_superuser('card-admin@example.test',must_change_password=False,privacy_version=PRIVACY_VERSION,privacy_accepted_at=timezone.now())
        self.it=get_user_model().objects.create_user('card-it@example.test',first_name='Deniz',must_change_password=False,privacy_version=PRIVACY_VERSION,privacy_accepted_at=timezone.now())
        self.membership=Membership.objects.create(audit=self.audit,user=self.it,role='it')
        self.c=Control.objects.create(audit=self.audit,code='CARD-1',title='Kontrol',description='Soru?',evidence_guidance='Kanıt',risk='high')
        self.c2=Control.objects.create(audit=self.audit,code='CARD-2',title='İkinci',description='Diğer soru?',risk='high')
        self.client.force_login(self.admin,backend='django.contrib.auth.backends.ModelBackend')
        self.portal=Client()
        self.dispatch=f'/console/{self.audit.pk}/send-controls/'
    def issue(self,selection='pending'):
        response=self.client.post(self.dispatch,{'recipient':self.membership.pk,'selection':selection})
        self.assertEqual(response.status_code,200)
        draft=response.context['draft']
        text=parse_qs(urlsplit(draft['mailto']).query)['body'][0]
        code=text.split('Tek kullanımlık giriş kodunuz: ')[1].split()[0]
        self.assertEqual(len(code),12);self.assertTrue(code.isalnum())
        return code,response
    def enter(self):
        code,_=self.issue();self.assertEqual(self.portal.post('/cards/',{'code':code}).status_code,302)
        return code
    def save(self,control=None,**kwargs):
        return self.portal.post('/cards/save/',{'control':(control or self.c).pk,'status':'missing','explanation':'Plan açıklaması','declaration':'on',**kwargs})
    def test_one_time_scoped_access_not_general_login(self):
        code=self.enter()
        self.assertContains(self.portal.get('/cards/work/'),'Soru?')
        self.assertEqual(self.portal.get('/console/').status_code,302)
        self.assertNotIn('_auth_user_id',self.portal.session)
        self.assertContains(Client().post('/cards/',{'code':code}),'Kod geçersiz')
        grant=CardAccess.objects.get();self.assertNotEqual(grant.code_digest,code)
        self.assertEqual(grant.code_digest,digest(code))
    def test_defer_then_complete_is_atomic_and_revision_created_once(self):
        self.enter();response=self.save(defer='1',explanation='',declaration='')
        self.assertEqual(response.status_code,200);self.assertFalse(self.c.revisions.exists())
        self.assertTrue(response.json()['cards'][0]['deferred'])
        self.assertEqual(self.save(explanation='').status_code,400)
        self.assertEqual(self.save(declaration='').status_code,400)
        self.assertEqual(self.save().status_code,200)
        self.assertEqual(self.c.revisions.count(),1);self.assertFalse(CardDraft.objects.exists())
        self.assertEqual(self.save().status_code,409);self.assertEqual(self.c.revisions.count(),1)
        self.assertEqual(self.save(self.c2).json()['cards'],[])
    def test_all_statuses_require_explanation_in_cards(self):
        self.enter()
        for status in ('implemented','partial','missing','na'):
            self.assertEqual(self.save(status=status,explanation='').status_code,400)
        self.assertEqual(self.save(status='unanswered').status_code,400)
        self.assertFalse(ResponseRevision.objects.exists())
    def test_completed_excluded_and_old_missing_explanation_included(self):
        ResponseRevision.objects.create(control=self.c,actor=self.it,status='implemented',explanation='Tamam')
        ResponseRevision.objects.create(control=self.c2,actor=self.it,status='missing',explanation='')
        rows=pending_controls(self.audit)
        self.assertEqual([r['id'] for r in rows],[self.c2.pk]);self.assertTrue(rows[0]['deferred'])
    def test_revocation_expiry_membership_and_disabled_user_enforced(self):
        self.enter();self.issue()
        self.assertEqual(self.save().status_code,403)
        self.portal=Client();self.enter()
        self.it.is_active=False;self.it.save();self.assertEqual(self.save().status_code,403)
        self.it.is_active=True;self.it.save()
        self.membership.role='auditor';self.membership.save();self.assertEqual(self.save().status_code,403)
    def test_expired_and_wrong_tenant_code_rejected_without_consumption(self):
        code,_=self.issue()
        other=Organization.objects.create(name='Başka',slug='other',subdomain='other')
        self.assertContains(self.portal.post('/cards/',{'code':code},HTTP_HOST='other.grcustasi.com'),'Kod geçersiz')
        self.assertIsNone(CardAccess.objects.get().used_at)
        CardAccess.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertContains(self.portal.post('/cards/',{'code':code}),'Kod geçersiz')
    def test_session_expiry_and_logout(self):
        self.enter();CardAccess.objects.update(used_at=timezone.now()-timedelta(hours=13))
        self.assertEqual(self.save().status_code,403)
        self.portal=Client();self.enter();self.portal.post('/cards/leave/')
        self.assertEqual(self.save().status_code,403)
    def test_privacy_required_for_code_entry(self):
        self.it.privacy_version='';self.it.save();self.enter()
        self.assertContains(self.portal.get('/cards/work/'),'Gizlilik sözleşmesi')
        self.assertEqual(self.save().status_code,403)
        response=self.portal.post('/cards/work/',{'consent':'on','acknowledgement':'okudum, anladım'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.save().status_code,200)
    def test_tenant_and_control_isolation(self):
        self.enter()
        other=Audit.objects.create(organization=self.org,title='Başka')
        control=Control.objects.create(audit=other,code='OTHER',title='Other',risk='high')
        self.assertEqual(self.save(control).status_code,404)
        self.assertFalse(control.revisions.exists())
    def test_draft_preview_has_table_previous_date_and_no_auditor_notes(self):
        revision=ResponseRevision.objects.create(control=self.c,actor=self.it,status='implemented',explanation='Önceki açıklama')
        Evaluation.objects.create(control=self.c,assessment='compliant',rationale='SECRET-RATIONALE',private_note='SECRET-PRIVATE')
        _,response=self.issue('all')
        self.assertContains(response,'<th>Kontrol sorusu</th>')
        self.assertContains(response,'Önceki cevap:')
        self.assertContains(response,'Önceki açıklama')
        self.assertNotContains(response,'SECRET-')
        self.assertIn('Content-Type: text/html',response.context['draft']['eml'])
        _,response=self.issue('pending');self.assertNotContains(response,'Önceki açıklama')
    def test_dispatch_rejects_wrong_recipient_and_readonly(self):
        other=Audit.objects.create(organization=self.org,title='Başka')
        member=Membership.objects.create(user=self.it,audit=other,role='it')
        response=self.client.post(self.dispatch,{'recipient':member.pk,'selection':'pending'})
        self.assertNotIn('draft',response.context);self.assertFalse(CardAccess.objects.exists())
        self.membership.role='intern';self.membership.auditor_readonly=True;self.membership.save()
        self.client.force_login(self.it,backend='django.contrib.auth.backends.ModelBackend')
        self.assertEqual(self.client.get(self.dispatch).status_code,403)
    def test_dashboard_alert_and_standard_response_clears_draft(self):
        CardDraft.objects.create(control=self.c,actor=self.it,status='partial')
        self.client.force_login(self.it,backend='django.contrib.auth.backends.ModelBackend')
        self.assertContains(self.client.get('/console/'),'Yanıt vermeniz gereken 2 kontrol var')
        from .services import answer
        answer(self.audit,self.c,self.it,'it',{'status':'implemented','explanation':'Mevcut yol','declaration':True})
        self.assertFalse(CardDraft.objects.exists())
    def test_csrf_protects_redemption_and_saves(self):
        code,_=self.issue();client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/cards/',{'code':code}).status_code,403)
        self.assertEqual(client.post('/cards/save/',{}).status_code,403)
        page=client.get('/cards/')
        self.assertContains(page, 'name="referrer" content="same-origin"')
        token=client.cookies['municipal_csrftoken'].value
        response=client.post('/cards/',{'code':code,'csrfmiddlewaretoken':token},HTTP_ORIGIN='http://testserver')
        self.assertEqual(response.status_code,302)
        response=client.post('/cards/save/',{'control':self.c.pk,'status':'missing','explanation':'Tamamlandı','declaration':'on','csrfmiddlewaretoken':token},HTTP_ORIGIN='http://testserver')
        self.assertEqual(response.status_code,200)
    def test_failed_code_attempts_are_limited(self):
        for _ in range(15):self.portal.post('/cards/',{'code':'WrongCod1234'})
        self.assertContains(self.portal.post('/cards/',{'code':'WrongCod1234'}),'Çok fazla deneme')
