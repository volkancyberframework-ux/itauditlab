from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from .models import (Organization, Audit, Control, Membership, Activity, ResponseRevision,
                     Finding, FindingUpdate, Suggestion, CardDraft, ControlEmail)
from .notifications import deliver_email
from .pdf import user_label

@override_settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_ID='')
class UserDeletionTests(TestCase):
    def test_delete_preserves_history_and_stops_pending_email(self):
        user = get_user_model().objects.create_user('removed@example.test', 'password')
        org = Organization.objects.create(name='Test', slug='deletion')
        audit = Audit.objects.create(organization=org, title='Test')
        control = Control.objects.create(audit=audit, code='A1', title='Test')
        Membership.objects.create(user=user, audit=audit, role='it')
        finding = Finding.objects.create(audit=audit, title='Test')
        records = [
            Activity.objects.create(audit=audit, actor=user, action='Test', role='auditor'),
            ResponseRevision.objects.create(control=control, actor=user, status='partial', explanation='Evidence'),
            FindingUpdate.objects.create(finding=finding, actor=user, role='it', action='plan'),
            Suggestion.objects.create(audit=audit, author=user, title='Test'),
            CardDraft.objects.create(control=control, actor=user, status='partial'),
            ControlEmail.objects.create(control=control, recipient=user, email=user.email, subject='Test', body='Test'),
        ]
        pk = user.pk
        get_user_model().objects.filter(pk=pk).delete()
        self.assertFalse(get_user_model().objects.filter(pk=pk).exists())
        self.assertFalse(Membership.objects.filter(user_id=pk).exists())
        for record in records:
            record.refresh_from_db()
            field = 'author_id' if isinstance(record, Suggestion) else 'recipient_id' if isinstance(record, ControlEmail) else 'actor_id'
            self.assertIsNone(getattr(record, field))
        deliver_email(records[-1].pk)
        records[-1].refresh_from_db()
        self.assertEqual(records[-1].attempts, 0)
        self.assertEqual(user_label(None), 'Silinmiş kullanıcı')

    @override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
    def test_console_and_history_render_after_actor_deleted(self):
        from accounts.privacy import PRIVACY_VERSION
        from django.utils import timezone
        admin = get_user_model().objects.create_superuser('owner@example.test', 'test-password',
            must_change_password=False, privacy_accepted_at=timezone.now(), privacy_version=PRIVACY_VERSION)
        removed = get_user_model().objects.create_user('deleted@example.test', 'test-password')
        org = Organization.objects.create(name='GRC', slug='grc', subdomain='grcustasi')
        audit = Audit.objects.create(organization=org, title='Audit')
        control = Control.objects.create(audit=audit, code='TEST-1', title='Control', risk='high')
        Activity.objects.create(audit=audit, actor=removed, action='Old action', role='auditor')
        ResponseRevision.objects.create(control=control, actor=removed, status='partial', explanation='Evidence')
        Suggestion.objects.create(audit=audit, author=removed, title='Suggestion')
        finding = Finding.objects.create(audit=audit, title='Finding')
        FindingUpdate.objects.create(finding=finding, actor=removed, role='it', action='plan')
        removed.delete()
        self.client.force_login(admin, backend='django.contrib.auth.backends.ModelBackend')
        for path in ['/console/', f'/console/{audit.pk}/controls/{control.pk}/']:
            with self.subTest(path=path):
                response = self.client.get(path, HTTP_HOST='grcustasi.grcustasi.com')
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Silinmiş kullanıcı')
