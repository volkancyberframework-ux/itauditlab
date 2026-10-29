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
