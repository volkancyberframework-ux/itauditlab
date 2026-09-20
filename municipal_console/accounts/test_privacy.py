from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from .privacy import PRIVACY_VERSION
from workspace.models import Audit, Control, Membership, Organization, ResponseRevision


@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class PrivacyTests(TestCase):
    def setUp(self):
        self.audit = Audit.objects.create(organization=Organization.objects.create(name='Kurum', slug='kurum'), title='Denetim')
        self.control = Control.objects.create(audit=self.audit, code='C', title='Kontrol', risk='low')

    def login(self, user):
        self.client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')

    def test_every_role_requires_consent_before_reading_or_writing(self):
        for role in ('admin', 'auditor', 'intern', 'it', 'executive'):
            with self.subTest(role=role):
                user = get_user_model().objects.create_user(role+'@privacy.test', must_change_password=False, is_superuser=role=='admin', is_staff=role=='admin')
                if role != 'admin':Membership.objects.create(audit=self.audit, user=user, role=role)
                self.login(user)
                for path in ('/console/', '/admin/', f'/console/{self.audit.pk}/controls/{self.control.pk}/', f'/console/{self.audit.pk}/controls.pdf'):
                    self.assertRedirects(self.client.get(path), '/privacy/')
                response = self.client.post(f'/console/{self.audit.pk}/workflow/', {'action': 'answer', 'control': self.control.pk, 'status': 'partial', 'declaration': 'on'})
                self.assertRedirects(response, '/privacy/')
                self.assertFalse(ResponseRevision.objects.exists())

    def test_checkbox_and_exact_acknowledgement_are_both_required(self):
        user = get_user_model().objects.create_user('user@privacy.test', must_change_password=False)
        self.login(user)
        for data in ({}, {'consent': 'on'}, {'acknowledgement': 'okudum, anladım'}, {'consent': 'on', 'acknowledgement': 'hayır'}):
            response = self.client.post('/privacy/', data)
            self.assertEqual(response.status_code, 200)
            user.refresh_from_db()
            self.assertIsNone(user.privacy_accepted_at)
        self.assertRedirects(self.client.post('/privacy/', {'consent': 'on', 'acknowledgement': 'okudum, anladım'}), '/console/')
        user.refresh_from_db()
        self.assertEqual(user.privacy_version, PRIVACY_VERSION)
        accepted_at = user.privacy_accepted_at
        self.assertIsNotNone(accepted_at)
        self.client.post('/privacy/', {'consent': 'on', 'acknowledgement': 'okudum, anladım'})
        user.refresh_from_db()
        self.assertEqual(user.privacy_accepted_at, accepted_at)
        self.client.logout()
        self.login(user)
        self.assertEqual(self.client.get('/console/').status_code, 200)

    def test_old_version_requires_new_acceptance(self):
        from django.utils import timezone
        user = get_user_model().objects.create_user('old@privacy.test', must_change_password=False, privacy_accepted_at=timezone.now(), privacy_version='old')
        self.login(user)
        self.assertRedirects(self.client.get('/console/'), '/privacy/')

    def test_password_change_and_logout_remain_available_before_consent(self):
        user = get_user_model().objects.create_user('first@privacy.test')
        self.login(user)
        self.assertEqual(self.client.get('/password/change/').status_code, 200)
        self.assertEqual(self.client.post('/signout/').status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)
