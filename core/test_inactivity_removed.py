from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from core.account_inactivity import run_due_check, touch_access, inactivity_message
from core.inactivity_report import send_pending_reports, send_report
from itaudit.inactivity_scheduler import tick


class RetiredInactivityTests(TestCase):
    def test_compatibility_entrypoints_cannot_disable_or_send(self):
        user=get_user_model().objects.create_user('unused',date_joined=timezone.now()-timedelta(days=100))
        with patch('requests.post') as send, patch('subprocess.run') as process:
            call_command('check_account_inactivity')
            self.assertIsNone(run_due_check());self.assertFalse(touch_access(user));self.assertIsNone(inactivity_message(user))
            self.assertTrue(send_pending_reports());self.assertFalse(send_report(1));self.assertIsNone(tick(None))
            send.assert_not_called();process.assert_not_called()
        user.refresh_from_db();self.assertTrue(user.is_active)

    def test_migration_restores_only_inactivity_disabled_accounts(self):
        users=get_user_model().objects
        inactive=users.create_user('policy-disabled',is_active=False,inactivity_disabled_at=timezone.now())
        other=users.create_user('manually-disabled',is_active=False)
        active=users.create_user('active',is_active=True)
        restore=import_module('core.migrations.0037_cancel_account_inactivity').restore_accounts
        editor=SimpleNamespace(connection=SimpleNamespace(alias='default'))
        restore(apps,editor);restore(apps,editor)
        inactive.refresh_from_db();other.refresh_from_db();active.refresh_from_db()
        self.assertTrue(inactive.is_active);self.assertIsNone(inactive.inactivity_disabled_at)
        self.assertFalse(other.is_active);self.assertTrue(active.is_active)

    def test_middleware_and_runtime_do_not_start_inactivity(self):
        from django.conf import settings
        from itaudit import console_runtime
        self.assertNotIn('core.account_inactivity.AccountAccessMiddleware',settings.MIDDLEWARE)
        with patch.dict('os.environ',{'CONSOLE_ENABLED':'false'}),patch('itaudit.console_runtime.subprocess.Popen') as spawn:
            console_runtime.start(SimpleNamespace(log=SimpleNamespace(exception=lambda *_:None)))
            spawn.assert_not_called()
