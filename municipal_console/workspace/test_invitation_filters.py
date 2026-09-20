from urllib.parse import urlsplit, parse_qs
from datetime import timedelta
from html.parser import HTMLParser
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from accounts.privacy import PRIVACY_VERSION
from .models import *
from .forms import EvaluationForm
from .invitations import invitation_draft, temporary_password


@override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ConsoleChangesTests(TestCase):
    def test_visible_console_actions_are_enabled_for_every_working_role(self):
        class Buttons(HTMLParser):
            def __init__(self):
                super().__init__()
                self.disabled = []
            def handle_starttag(self, tag, attrs):
                attributes = dict(attrs)
                if tag in ('button', 'fieldset') and 'disabled' in attributes:
                    self.disabled.append(attributes)

        Finding.objects.create(audit=self.audit,control=self.c,title='Test bulgusu',recommendation='Düzelt',severity='high',treatment='risk_requested')
        for role, _ in ROLES:
            with self.subTest(role=role):
                self.client.post('/console/view-as/', {'role': role})
                for url in ('/console/', f'/console/{self.audit.pk}/controls/{self.c.pk}/'):
                    if role == 'intern' and url != '/console/':
                        continue
                    page = self.client.get(url)
                    self.assertEqual(page.status_code, 200)
                    parser = Buttons()
                    parser.feed(page.content.decode())
                    self.assertEqual(parser.disabled, [])

    def setUp(self):
        U=get_user_model()
        self.admin=U.objects.create_superuser('admin@new.test',must_change_password=False,privacy_version=PRIVACY_VERSION,privacy_accepted_at=timezone.now())
        self.org=Organization.objects.create(name='Örnek Hastanesi',slug='hospital',subdomain='hospital')
        self.audit=Audit.objects.create(organization=self.org,title='Hastane Denetimi',template=AuditTemplate.objects.get(name='Hastane Denetimi'))
        self.c=self.audit.controls.first()
        self.other=Organization.objects.create(name='Başka Kurum',slug='other',subdomain='other')
        self.other_audit=Audit.objects.create(organization=self.other,title='Başka Denetim')
        self.url=f'/console/{self.audit.pk}/workflow/'
        self.client.force_login(self.admin,backend='django.contrib.auth.backends.ModelBackend')
        self.client.get(f'/console/?audit={self.audit.pk}')

    def payload(self,**extra):
        return {'first_name':'Deniz','last_name':'Yılmaz','email':'deniz@example.test','organization':self.org.pk,'audit':self.audit.pk,'role':'intern','auditor_readonly':'on','sector':'hastane',**extra}

    def test_create_user_draft_password_and_first_use_lifecycle(self):
        response=self.client.post('/console/users/new/',self.payload())
        self.assertEqual(response.status_code,200)
        draft=response.context['draft']
        user=get_user_model().objects.get(email='deniz@example.test')
        password=draft['body'].split('Tek kullanımlık geçici parola: ')[1].split('\n')[0]
        self.assertEqual(len(password),12)
        self.assertTrue(user.check_password(password))
        self.assertTrue(user.must_change_password)
        self.assertTrue(user.temporary_password)
        self.assertFalse(user.is_staff)
        self.assertTrue(Membership.objects.get(user=user,audit=self.audit).auditor_readonly)
        self.assertIn('Bir hastanede',draft['body'])
        self.assertIn('Hastanelerin',draft['body'])
        self.assertNotIn('belediye',draft['body'])
        self.assertIn('Excel',draft['body'])
        self.assertIn(f'https://hospital.grcustasi.com/console/?audit={self.audit.pk}',draft['body'])
        self.assertEqual(parse_qs(urlsplit(draft['mailto']).query)['body'][0],draft['body'])
        self.assertIn('no-store',response['Cache-Control'])
        self.assertNotIn(password,str(dict(self.client.session)))
        self.assertNotIn(password,str(list(Activity.objects.values_list('metadata',flat=True))))
        self.assertFalse(ControlEmail.objects.exists())
        from django.core import mail
        self.assertEqual(len(mail.outbox),0)
        client=Client()
        client.post('/signin/',{'username':user.email,'password':'incorrect'})
        user.refresh_from_db()
        self.assertTrue(user.temporary_password)
        self.assertTrue(user.check_password(password))
        self.assertRedirects(client.post('/signin/',{'username':user.email,'password':password}),'/password/change/')
        user.refresh_from_db()
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.temporary_password)
        self.assertTrue(user.must_change_password)
        self.assertEqual(Client().post('/signin/',{'username':user.email,'password':password}).status_code,200)
        self.assertNotContains(client.get('/password/change/'),'name="old_password"')
        response=client.post('/password/change/',{'new_password1':'New-Personal-Password-93!','new_password2':'New-Personal-Password-93!'})
        self.assertEqual(response.status_code,302)
        user.refresh_from_db()
        self.assertFalse(user.must_change_password)
        self.assertTrue(user.check_password('New-Personal-Password-93!'))
        self.assertFalse(user.check_password(password))
        self.assertRedirects(client.get('/console/'),'/privacy/')

    def test_duplicate_does_not_reset_existing_account(self):
        original=self.admin.password
        response=self.client.post('/console/users/new/',self.payload(email=self.admin.email.upper()))
        self.assertContains(response,'zaten kayıtlı')
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.password,original)
        self.assertFalse(Membership.objects.filter(user=self.admin).exists())

    def test_mismatched_company_and_tenant_scope_rejected(self):
        response=self.client.post('/console/users/new/',self.payload(organization=self.other.pk))
        self.assertContains(response,'bu kuruma ait değil')
        response=self.client.post('/console/users/new/',self.payload(organization=self.other.pk,audit=self.other_audit.pk),HTTP_HOST='hospital.grcustasi.com')
        self.assertNotIn('draft',response.context)
        self.assertFalse(get_user_model().objects.filter(email='deniz@example.test').exists())

    def test_only_platform_admin_can_create_and_readonly_cannot_be_forged(self):
        u=get_user_model().objects.create_user('intern@new.test',must_change_password=False,privacy_version=PRIVACY_VERSION,privacy_accepted_at=timezone.now())
        Membership.objects.create(user=u,audit=self.audit,role='intern',auditor_readonly=True)
        self.client.force_login(u,backend='django.contrib.auth.backends.ModelBackend')
        for method in (self.client.get,self.client.post):self.assertEqual(method('/console/users/new/',self.payload()).status_code,403)
        self.assertEqual(self.client.post(self.url,{'action':'add_controls','controls':[self.c.source_id]}).status_code,403)

    def test_role_specific_drafts_and_shared_central_link(self):
        self.client.post('/console/users/new/',self.payload(role='executive',auditor_readonly=''))
        user=get_user_model().objects.get(email='deniz@example.test')
        request=self.client.get('/console/').wsgi_request
        with override_settings(PUBLIC_CONSOLE_URL='https://www.grcustasi.com/denetim'):
            self.other.subdomain=None;self.other.save()
            draft=invitation_draft(request,user,self.other_audit,'executive','Example-Temp1','sirket',False)
            self.assertIn('haftalık ve aylık',draft['body'])
            self.assertIn(f'https://www.grcustasi.com/denetim/console/?audit={self.other_audit.pk}',draft['body'])
            self.assertNotIn('Excel',draft['body'])
        for role in ('auditor','it'):
            draft=invitation_draft(request,user,self.audit,role,'Example-Temp1','hastane',False)
            self.assertIn(dict(ROLES)[role],draft['body'])
            self.assertNotIn('Excel',draft['body'])

    def test_production_admin_can_evaluate_add_catalog_and_close_finding(self):
        self.client.post('/console/view-as/',{'role':'auditor'})
        page=self.client.get('/console/')
        self.assertTrue(page.context['can_write'])
        self.assertNotContains(page,'disabled>Görüşü kaydet')
        self.assertNotContains(page,'disabled>Seçilen kontrolleri denetime ekle')
        response=self.client.post(self.url,{'action':'evaluate','control':self.c.pk,'assessment':'partial','deficiency':'design','rationale':'Test sonucu','recommendation':'İyileştirin','verified':'on'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(Evaluation.objects.get(control=self.c).deficiency,'design')
        extra=ControlDefinition.objects.get(code='BEL-001')
        self.assertEqual(self.client.post(self.url,{'action':'add_controls','controls':[extra.pk]}).status_code,302)
        self.assertTrue(self.audit.controls.filter(source=extra).exists())
        finding=Finding.objects.get(control=self.c)
        self.client.post(self.url,{'action':'finding','finding':finding.pk,'finding_action':'close','explanation':'Test tamamlandı'})
        finding.refresh_from_db();self.assertEqual(finding.status,'closed')
        self.assertEqual(finding.updates.get().actor,self.admin)

    def test_production_role_actions_appointments_suggestions_and_risk(self):
        self.client.post('/console/view-as/',{'role':'auditor'})
        self.client.post(self.url,{'action':'phase','target':'fieldwork'})
        self.audit.refresh_from_db();self.assertEqual(self.audit.phase,'fieldwork')
        self.client.post(self.url,{'action':'appointment','when':(timezone.now()+timedelta(days=3)).isoformat(),'note':'Görüşme'})
        self.audit.refresh_from_db();self.assertEqual(self.audit.appointment_status,'proposed')
        self.client.post('/console/view-as/',{'role':'it'})
        self.client.post(self.url,{'action':'confirm_appointment'})
        self.audit.refresh_from_db();self.assertEqual(self.audit.appointment_status,'confirmed')
        f=Finding.objects.create(audit=self.audit,control=self.c,title='Risk',recommendation='Düzelt',severity='high')
        self.client.post(self.url,{'action':'finding','finding':f.pk,'finding_action':'request_risk','explanation':'Risk kabulü önerisi'})
        self.client.post('/console/view-as/',{'role':'executive'})
        self.client.post(self.url,{'action':'finding','finding':f.pk,'finding_action':'accept_risk','explanation':'Kurum kararı'})
        f.refresh_from_db();self.assertEqual(f.status,'risk_accepted')
        self.client.post('/console/view-as/',{'role':'intern'})
        self.client.post(self.url,{'action':'suggest','title':'Yeni kontrol','framework':'ISO','description':'İyileştirme','test_steps':'Örnekleme alınan hesapların yetkilerini kontrol edin ve sonuçlarını belgeleyin.'})
        suggestion=Suggestion.objects.get(audit=self.audit)
        self.assertEqual(suggestion.author,self.admin)
        self.client.post('/console/view-as/',{'role':'auditor'})
        self.client.post(self.url,{'action':'review_suggestion','suggestion':suggestion.pk,'decision':'accepted','note':'Uygun kontrol'})
        suggestion.refresh_from_db();self.assertEqual(suggestion.status,'accepted')

    def test_successful_evaluation_ignores_irrelevant_past_finding_due_date(self):
        form=EvaluationForm({'assessment':'compliant','rationale':'Başarılı','due_date':'2020-01-01','verified':'on'})
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data['due_date'])

    def test_filters_combine_and_sort_links_preserve_scope(self):
        Evaluation.objects.create(control=self.c,assessment='partial',deficiency='design',rationale='Bulgu',verified=True)
        ResponseRevision.objects.create(control=self.c,actor=self.admin,status='missing',explanation='')
        query={'audit':self.audit.pk,'risk':self.c.risk,'status':'missing','assessment':'partial','verified':'yes','framework':self.c.framework,'sort':'-code'}
        response=self.client.get('/console/',query)
        self.assertEqual([r['id'] for r in response.context['rows']],[self.c.pk])
        self.assertEqual(response.context['total'],self.audit.controls.count())
        self.assertEqual(response.context['filtered_count'],1)
        link=response.context['sort_headers'][1]['url']
        params=parse_qs(urlsplit(link).query)
        self.assertEqual(params['audit'],[str(self.audit.pk)])
        self.assertEqual(params['status'],['missing'])
        self.assertEqual(params['assessment'],['partial'])
        self.assertEqual(params['sort'],['risk'])
        self.assertContains(response,'aria-sort="descending"')

    def test_sorting_and_unanswered_filter(self):
        response=self.client.get('/console/',{'audit':self.audit.pk,'sort':'risk'})
        risks=[r['risk'] for r in response.context['rows']]
        self.assertEqual(risks,sorted(risks,key={'high':0,'medium':1,'low':2}.get))
        response=self.client.get('/console/',{'sort':'-title'})
        titles=[r['title'].casefold() for r in response.context['rows']]
        self.assertEqual(titles,sorted(titles,reverse=True))
        response=self.client.get('/console/',{'status':'unanswered','assessment':'pending'})
        self.assertEqual(response.context['filtered_count'],self.audit.controls.count())
        self.assertEqual(self.client.get('/console/',{'q':'not-found'}).context['filtered_count'],0)

    def test_filters_cannot_infer_hidden_evaluations_or_intern_responses(self):
        Evaluation.objects.create(control=self.c,assessment='partial',deficiency='design',rationale='SECRET')
        self.client.post('/console/view-as/',{'role':'it'})
        response=self.client.get('/console/',{'assessment':'partial','verified':'yes','sort':'assessment'})
        self.assertEqual(response.context['filtered_count'],self.audit.controls.count())
        self.assertEqual(response.context['sort'],'code')
        self.assertNotContains(response,'name="assessment"')
        self.client.post('/console/view-as/',{'role':'intern'})
        response=self.client.get('/console/',{'status':'missing','assessment':'partial','sort':'status'})
        self.assertEqual(response.context['filtered_count'],self.audit.controls.filter(intern_visible=True).count())
        self.assertNotContains(response,'name="status"')
        self.assertNotContains(response,'SECRET')
