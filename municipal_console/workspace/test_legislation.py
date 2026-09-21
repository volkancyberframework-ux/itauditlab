import csv
import io
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from accounts.privacy import PRIVACY_VERSION
from .models import Organization, Audit, Control, ControlDefinition, AuditTemplate, Membership, Evaluation, Legislation, LegalArticle
from .legislation import compliance_context, HEADERS

@override_settings(SECURE_SSL_REDIRECT=False, STORAGES={'default': {'BACKEND':'django.core.files.storage.FileSystemStorage'}, 'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class LegislationTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('law-admin@test.example', must_change_password=False, privacy_version=PRIVACY_VERSION, privacy_accepted_at=timezone.now())
        self.org = Organization.objects.create(name='Test Kurumu', slug='legal-test', subdomain='legal-test')
        self.audit = Audit.objects.create(organization=self.org, title='Mevzuat denetimi')
        self.law = Legislation.objects.create(code='L-1', title='Test Kanunu')
        self.a = LegalArticle.objects.create(legislation=self.law, number='1', text='Madde metni')
        self.b = LegalArticle.objects.create(legislation=self.law, number='2/a', text='Başka madde')
        self.other_law = Legislation.objects.create(code='L-2', title='İkinci Kanun')
        self.other_article = LegalArticle.objects.create(legislation=self.other_law, number='3', text='İkinci metin')
        self.control = Control.objects.create(audit=self.audit, code='C-1', title='Kontrol', framework='ISO', theme='Tema', risk='high', description='Açıklama', evidence_guidance='Kanıt', intern_visible=True)
        self.control.legal_articles.set([self.a, self.b, self.other_article])
        self.ev = Evaluation.objects.create(control=self.control, assessment='compliant', verified=True, rationale='GİZLİ GEREKÇE', private_note='GİZLİ NOT')
        self.client.force_login(self.admin, backend='django.contrib.auth.backends.ModelBackend')

    def upload(self, rows):
        stream = io.StringIO(); writer = csv.writer(stream); writer.writerow(HEADERS); writer.writerows(rows)
        return self.client.post('/admin/legislation/import/', {'file': SimpleUploadedFile('laws.csv', stream.getvalue().encode('utf-8-sig'), content_type='text/csv')})

    def test_multiple_laws_deduplicate_controls_within_each_law(self):
        rows = compliance_context(self.audit, 'admin')['law_rows']
        self.assertEqual([(r['code'], r['total'], r['percent']) for r in rows], [('L-1', 1, 100), ('L-2', 1, 100)])
        self.ev.verified = False; self.ev.save()
        rows = compliance_context(self.audit, 'admin')['law_rows']
        self.assertEqual(rows[0]['percent'], 0)
        self.assertEqual(rows[0]['segments'][3]['count'], 1)

    def test_no_half_credit_and_unmapped_excluded(self):
        partial = Control.objects.create(audit=self.audit, code='C-2', title='Kısmi', risk='high')
        partial.legal_articles.add(self.a)
        Evaluation.objects.create(control=partial, assessment='partial', verified=True)
        Control.objects.create(audit=self.audit, code='C-3', title='Eşlenmemiş', risk='high')
        context = compliance_context(self.audit, 'admin')
        self.assertEqual(context['law_rows'][0]['percent'], 50)
        self.assertEqual(context['law_unmapped'], 1)

    def test_template_copies_references_without_overwriting_existing_audit(self):
        definition = ControlDefinition.objects.create(code='CAT-LAW', title='Katalog', risk='high')
        definition.legal_articles.add(self.a, self.other_article)
        template = AuditTemplate.objects.create(name='Mevzuat şablonu')
        template.controls.add(definition)
        audit = Audit.objects.create(organization=self.org, title='Yeni', template=template)
        control = audit.controls.get()
        self.assertEqual(set(control.legal_articles.all()), {self.a, self.other_article})
        definition.legal_articles.clear()
        from .services import add_catalog_controls
        add_catalog_controls(audit, [definition])
        self.assertEqual(control.legal_articles.count(), 2)
        self.ev.refresh_from_db(); self.assertTrue(self.ev.verified)

    def test_csv_upserts_and_preserves_links_and_evaluations(self):
        response = self.upload([['L-1', 'Güncel Kanun', '1', 'Güncel metin\nİkinci paragraf', 'https://example.com/law'], ['NEW', 'Yeni Kanun', '2', 'Yeni madde', '']])
        self.assertContains(response, '2 madde yüklendi')
        self.a.refresh_from_db(); self.assertIn('İkinci paragraf', self.a.text)
        self.assertEqual(self.control.legal_articles.count(), 3)
        self.ev.refresh_from_db(); self.assertTrue(self.ev.verified)

    def test_invalid_late_csv_row_rolls_back_entire_upload(self):
        response = self.upload([['NEW', 'Yeni Kanun', '1', 'Metin', ''], ['BAD', '', '2', 'Metin', '']])
        self.assertContains(response, 'Dosya yüklenemedi')
        self.assertFalse(Legislation.objects.filter(code='NEW').exists())
        response = self.upload([['NEW', 'Yeni', '1', 'Metin', ''], ['NEW', 'Yeni', '1', 'Tekrar', '']])
        self.assertContains(response, 'tekrarlanıyor')
        self.assertFalse(Legislation.objects.filter(code='NEW').exists())

    def test_panel_roles_and_private_information(self):
        hidden = Control.objects.create(audit=self.audit, code='SECRET', title='Gizli', risk='high')
        hidden.legal_articles.add(self.a)
        for role in ('executive', 'auditor', 'intern', 'it'):
            user = get_user_model().objects.create_user(f'{role}@law.example', must_change_password=False, privacy_version=PRIVACY_VERSION, privacy_accepted_at=timezone.now())
            Membership.objects.create(user=user, audit=self.audit, role=role)
            self.client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
            response = self.client.get(f'/console/{self.audit.pk}/compliance/')
            if role == 'it':self.assertEqual(response.status_code, 403);continue
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'GİZLİ')
            self.assertEqual(response.context['law_rows'][0]['total'], 1 if role == 'intern' else 2)
            self.assertEqual(self.client.get('/admin/legislation/import/').status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.get(f'/console/{self.audit.pk}/compliance/').status_code, 302)

    def test_cross_tenant_panel_is_blocked_even_for_admin(self):
        other = Audit.objects.create(organization=Organization.objects.create(name='Başka', slug='another'), title='Başka')
        response = self.client.get(f'/console/{other.pk}/compliance/', HTTP_HOST='legal-test.grcustasi.com')
        self.assertEqual(response.status_code, 404)

    def test_reference_only_admin_edit_keeps_last_test_approval(self):
        data = {field: getattr(self.control, field) for field in ('code', 'title', 'description', 'evidence_guidance', 'framework', 'theme', 'risk')}
        data.update(legal_articles=[self.a.pk], intern_visible='on', _save='Save')
        response = self.client.post(f'/admin/workspace/control/{self.control.pk}/change/', data)
        self.assertEqual(response.status_code, 302)
        self.ev.refresh_from_db(); self.assertTrue(self.ev.verified)
        self.assertEqual(list(self.control.legal_articles.all()), [self.a])

    def test_dashboard_shows_references_and_live_chart_ignoring_table_filter(self):
        response = self.client.get('/console/?q=does-not-match')
        self.assertContains(response, 'Kanun bazında uyumluluk')
        self.assertEqual(response.context['law_rows'][0]['percent'], 100)
        response = self.client.get('/console/')
        self.assertContains(response, 'Madde 2/a')
