from io import BytesIO
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from accounts.privacy import PRIVACY_VERSION
from .admin import OrganizationForm
from .forms import EvaluationForm
from .models import Audit, AuditTemplate, Control, ControlDefinition, Evaluation, Finding, Membership, Organization, ResponseRevision
from .services import add_catalog_controls, evaluate


@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class TemplateAndPermissionTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='Kurum A', slug='kurum-a', subdomain='kuruma')
        self.audit = Audit.objects.create(organization=self.org, title='Denetim')
        self.control = Control.objects.create(audit=self.audit, code='TEST', title='Gizli kontrol', risk='high')
        self.auditor = self.user('auditor')
        self.it = self.user('it')
        self.intern = self.user('intern')
        self.admin = get_user_model().objects.create_superuser('admin@unit.test', must_change_password=False, privacy_accepted_at=timezone.now(), privacy_version=PRIVACY_VERSION)
        self.url = f'/console/{self.audit.pk}/workflow/'

    def user(self, role):
        user = get_user_model().objects.create_user(role+'@unit.test', must_change_password=False, privacy_accepted_at=timezone.now(), privacy_version=PRIVACY_VERSION)
        Membership.objects.create(user=user, audit=self.audit, role=role)
        return user

    def login(self, user):
        self.client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')

    def test_predefined_templates_and_independent_snapshots(self):
        municipal = AuditTemplate.objects.get(name='Belediye Denetimi')
        hospital = AuditTemplate.objects.get(name='Hastane Denetimi')
        self.assertTrue(municipal.controls.filter(code__startswith='BEL-').exists())
        self.assertFalse(municipal.controls.filter(code__startswith='HAS-').exists())
        first = Audit.objects.create(organization=self.org, title='Belediye', template=municipal)
        second = Audit.objects.create(organization=self.org, title='Hastane', template=hospital)
        other = Organization.objects.create(name='Kurum B', slug='kurum-b')
        third = Audit.objects.create(organization=other, title='Hastane B', template=hospital)
        self.assertEqual(first.controls.count(), municipal.controls.count())
        self.assertEqual(second.controls.count(), hospital.controls.count())
        definition = hospital.controls.first()
        original = second.controls.get(source=definition).title
        definition.title = 'Katalog değişti'
        definition.save()
        self.assertEqual(second.controls.get(source=definition).title, original)
        self.assertEqual(third.controls.get(source=definition).title, original)
        second.controls.filter(source=definition).update(title='Sadece bu denetim')
        self.assertEqual(third.controls.get(source=definition).title, original)

    def test_catalog_add_is_idempotent_and_preserves_existing_revisions(self):
        definition = ControlDefinition.objects.first()
        self.control.code = definition.code
        self.control.save()
        ResponseRevision.objects.create(control=self.control, actor=self.it, status='partial', explanation='Korunacak yanıt')
        add_catalog_controls(self.audit, [definition])
        add_catalog_controls(self.audit, [definition])
        self.assertEqual(self.audit.controls.count(), 2)
        self.assertEqual(self.control.revisions.get().explanation, 'Korunacak yanıt')
        self.assertEqual(self.audit.controls.get(source=definition).code, definition.code+'-2')

    def test_admin_creates_template_audit_members_and_extra_controls_together(self):
        self.login(self.admin)
        template = AuditTemplate.objects.get(name='Belediye Denetimi')
        extra = ControlDefinition.objects.filter(code__startswith='HAS-').first()
        response = self.client.post('/admin/workspace/audit/add/', {
            'organization': self.org.pk, 'title': 'Hazır denetim', 'template': template.pk,
            'extra_controls': [extra.pk], 'membership_set-TOTAL_FORMS': '1',
            'membership_set-INITIAL_FORMS': '0', 'membership_set-MIN_NUM_FORMS': '0',
            'membership_set-MAX_NUM_FORMS': '1000', 'membership_set-0-user': self.intern.pk,
            'membership_set-0-role': 'intern', 'membership_set-0-auditor_readonly': 'on', '_save': 'Save',
        })
        self.assertEqual(response.status_code, 302)
        audit = Audit.objects.get(title='Hazır denetim')
        self.assertEqual(audit.controls.count(), template.controls.count()+1)
        self.assertTrue(audit.membership_set.get(user=self.intern).auditor_readonly)

    def test_auditor_adds_catalog_controls_but_it_cannot(self):
        payload = {'action': 'add_controls', 'controls': [ControlDefinition.objects.first().pk]}
        self.login(self.it)
        self.assertEqual(self.client.post(self.url, payload).status_code, 403)
        self.login(self.auditor)
        self.assertContains(self.client.get('/console/'), 'Katalogdan ek kontrol seç')
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        self.assertEqual(self.audit.controls.count(), 2)

    def test_deficiency_required_for_each_failure_and_cleared_for_success(self):
        for assessment in ('partial', 'noncompliant'):
            data = {'assessment': assessment, 'rationale': 'Test sonucu', 'recommendation': 'Giderin'}
            form = EvaluationForm(data)
            self.assertFalse(form.is_valid())
            self.assertIn('deficiency', form.errors)
            with self.assertRaises(ValidationError):
                evaluate(self.audit, self.control, self.auditor, 'auditor', data)
            for deficiency in ('design', 'implementation', 'both'):
                form = EvaluationForm({**data, 'deficiency': deficiency})
                self.assertTrue(form.is_valid(), form.errors)
        form = EvaluationForm({'assessment': 'compliant', 'rationale': 'Başarılı', 'deficiency': 'both'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['deficiency'], '')

    def test_evaluate_and_close_without_any_it_response(self):
        self.login(self.auditor)
        payload = {'action': 'evaluate', 'control': self.control.pk, 'assessment': 'noncompliant', 'rationale': 'Test ettim', 'recommendation': 'Düzeltin', 'deficiency': 'design', 'verified': 'on'}
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        self.assertFalse(ResponseRevision.objects.exists())
        finding = Finding.objects.get(control=self.control)
        self.assertEqual(self.client.post(self.url, {'action': 'finding', 'finding': finding.pk, 'finding_action': 'close', 'explanation': 'Tekrar test ettim, kapatıyorum.'}).status_code, 302)
        finding.refresh_from_db()
        self.assertEqual(finding.status, 'closed')
        self.assertEqual(finding.updates.get().action, 'close')

    def test_verified_compliant_evaluation_closes_previous_finding(self):
        finding = Finding.objects.create(audit=self.audit, control=self.control, title='Bulgu', recommendation='Düzelt', severity='high')
        self.login(self.auditor)
        payload = {'action': 'evaluate', 'control': self.control.pk, 'assessment': 'compliant', 'rationale': 'Test başarılı'}
        self.client.post(self.url, payload)
        finding.refresh_from_db()
        self.assertEqual(finding.status, 'open')
        self.client.post(self.url, {**payload, 'verified': 'on'})
        finding.refresh_from_db()
        self.assertEqual(finding.status, 'closed')
        self.assertEqual(Evaluation.objects.get(control=self.control).deficiency, '')
        for phase in ('fieldwork', 'remediation', 'completed'):
            self.client.post(self.url, {'action': 'phase', 'target': phase})
            self.audit.refresh_from_db()
            self.assertEqual(self.audit.phase, phase)

    def test_readonly_intern_sees_all_auditor_data_and_cannot_mutate(self):
        Membership.objects.filter(user=self.intern, audit=self.audit).update(auditor_readonly=True)
        Evaluation.objects.create(control=self.control, assessment='partial', deficiency='both', rationale='GİZLİ GEREKÇE', private_note='GİZLİ EKİP NOTU')
        Finding.objects.create(audit=self.audit, control=self.control, title='GİZLİ BULGU', recommendation='Gider', severity='high', customer_visible=False)
        self.login(self.intern)
        response = self.client.get('/console/')
        for text in ('GİZLİ GEREKÇE', 'GİZLİ EKİP NOTU', 'GİZLİ BULGU', 'Gizli kontrol', 'salt okunur'):
            self.assertContains(response, text)
        self.assertNotContains(response, 'Görüşü kaydet')
        self.assertNotContains(response, 'Kararı kaydet')
        self.assertNotContains(response, 'Seçilen kontrolleri denetime ekle')
        for action in ('evaluate', 'answer', 'finding', 'phase', 'appointment', 'confirm_appointment', 'suggest', 'review_suggestion', 'add_controls'):
            self.assertEqual(self.client.post(self.url, {'action': action}).status_code, 403)
        detail = f'/console/{self.audit.pk}/controls/{self.control.pk}/'
        self.assertEqual(self.client.get(detail+'history/').status_code, 200)
        self.assertEqual(self.client.post(detail, {'status': 'partial', 'declaration': 'on'}).status_code, 403)
        self.assertEqual(self.client.get(f'/console/{self.audit.pk}/controls.pdf').status_code, 200)
        self.assertEqual(self.client.get(f'/console/{self.audit.pk}/findings.pdf').status_code, 200)
        Membership.objects.filter(user=self.intern, audit=self.audit).update(auditor_readonly=False)
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertNotContains(self.client.get('/console/'), 'GİZLİ GEREKÇE')

    def test_readonly_intern_remains_scoped_to_membership(self):
        Membership.objects.filter(user=self.intern, audit=self.audit).update(auditor_readonly=True)
        other = Audit.objects.create(organization=self.org, title='Başka denetim')
        Membership.objects.create(user=self.intern, audit=other, role='intern')
        hidden = Control.objects.create(audit=other, code='H', title='Diğer gizli kontrol', risk='high')
        self.login(self.intern)
        self.assertEqual(self.client.get(f'/console/{other.pk}/controls/{hidden.pk}/').status_code, 404)
        unassigned = Audit.objects.create(organization=self.org, title='Atanmamış')
        self.assertEqual(self.client.get(f'/console/?audit={unassigned.pk}').status_code, 404)

    def test_transparent_upload_keeps_alpha_and_branding_updates(self):
        image = BytesIO()
        Image.new('RGBA', (50, 50), (0, 100, 200, 0)).save(image, format='PNG')
        form = OrganizationForm({'name': self.org.name, 'slug': self.org.slug, 'subdomain': self.org.subdomain}, {'logo': SimpleUploadedFile('logo.png', image.getvalue(), content_type='image/png')}, instance=self.org)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertEqual(Image.open(BytesIO(bytes(self.org.logo_data))).getpixel((0, 0))[3], 0)
        response = self.client.get('/signin/', HTTP_HOST='kuruma.grcustasi.com')
        self.assertContains(response, '<title>Giriş yap · Kurum A</title>', html=True)
        self.assertContains(response, f'/branding/{self.org.pk}/logo/?v=')
        self.login(self.auditor)
        response = self.client.get('/console/')
        self.assertNotContains(response, 'overview-logo')
        self.assertContains(response, '<title>Denetim çalışma alanı · Kurum A</title>', html=True)
