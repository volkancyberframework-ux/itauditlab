import io
import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .guest_views import LOGIN_ERROR
from .models import SkoolGuestAccount, SkoolInvitation, SkoolUser


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage', MEDIA_ROOT='/tmp/skool-guest-test-media')
class GuestAccessTests(TestCase):
    initial = 'Initial-test-only-123!'
    replacement = 'Personal-test-7^New-Secret'

    def seed(self, emails=None, password=None, **options):
        data = json.dumps({'emails': emails or ['invited@example.com'], 'password': password or self.initial})
        out = io.StringIO()
        with patch('sys.stdin', io.StringIO(data + '\n')):
            call_command('provision_skool_guests', stdin=True, stdout=out, **options)
        return json.loads(out.getvalue())

    def setUp(self):
        self.seed()
        self.account = SkoolGuestAccount.objects.select_related('user__invitation').get(email='invited@example.com')
        self.user = self.account.user
        self.login_url = reverse('skool:guest_login')
        self.change_url = reverse('skool:guest_password_change')

    def login(self, client=None, password=None, email='INVITED@example.com'):
        return (client or self.client).post(self.login_url, {'email': email, 'password': password or self.initial})

    def change(self, client=None, **kwargs):
        data = {'full_name': 'Davetli Kullanıcı', 'new_password1': self.replacement, 'new_password2': self.replacement}
        data.update(kwargs)
        return (client or self.client).post(self.change_url, data)

    def test_seed_is_case_insensitive_deduplicated_and_never_resets_existing_passwords(self):
        self.account.set_password(self.replacement)
        self.account.must_change_password = False
        self.account.save()
        result = self.seed(['INVITED@example.com', ' invited@example.com ', 'another@example.com'])
        self.assertEqual(result, {'created': 1, 'existing_preserved': 1, 'unique_emails': 2, 'duplicates_removed': 1, 'dry_run': False})
        self.account.refresh_from_db()
        self.assertTrue(self.account.check_password(self.replacement))
        self.assertFalse(self.account.must_change_password)
        self.assertNotEqual(self.account.password, self.replacement)
        self.assertFalse(get_user_model().objects.filter(email__in=['invited@example.com', 'another@example.com']).exists())

    def test_dry_run_does_not_create_rows(self):
        result = self.seed(['dry-run@example.com'], dry_run=True)
        self.assertEqual(result['created'], 1)
        self.assertFalse(SkoolGuestAccount.objects.filter(email='dry-run@example.com').exists())

    def test_guest_button_and_login_page_do_not_disclose_initial_password(self):
        self.assertContains(self.client.get(reverse('skool:onboarding')), 'Misafir Girişi')
        response = self.client.get(self.login_url)
        self.assertContains(response, 'autocomplete="username"')
        self.assertNotContains(response, self.initial)
        self.assertIn('no-store', response['Cache-Control'])

    def test_first_login_cannot_access_journey_labs_or_api_before_password_change(self):
        self.assertRedirects(self.login(), self.change_url)
        self.assertNotIn('skool_user_id', self.client.session)
        self.assertEqual(self.client.session['skool_guest_pending_id'], self.account.pk)
        for path in [reverse('skool:onboarding'), reverse('skool:labs')]:
            self.assertRedirects(self.client.get(path), self.change_url)
        self.assertRedirects(self.client.get(reverse('skool:journey')), reverse('skool:onboarding'), fetch_redirect_response=False)
        self.assertEqual(self.client.post(reverse('skool:mark_intro')).status_code, 302)

    def test_change_password_enters_existing_consent_and_journey_and_resumes(self):
        self.login()
        response = self.change()
        self.assertRedirects(response, reverse('skool:onboarding'))
        self.account.refresh_from_db()
        self.user.refresh_from_db()
        self.assertFalse(self.account.must_change_password)
        self.assertTrue(self.account.check_password(self.replacement))
        self.assertFalse(self.account.check_password(self.initial))
        self.assertIsNotNone(self.account.password_changed_at)
        self.assertEqual(self.user.full_name, 'Davetli Kullanıcı')
        self.assertIsNone(self.user.withdrawal_notice_accepted_at)
        self.assertEqual(self.client.session['skool_user_id'], self.user.pk)
        self.assertNotIn('skool_guest_pending_id', self.client.session)
        self.client.post(reverse('skool:onboarding'), {'action': 'accept_withdrawal_notice'})
        self.assertEqual(self.client.get(reverse('skool:journey')).status_code, 200)
        self.user.current_question = 7
        self.user.save(update_fields=("current_question",))
        self.client.get(reverse('skool:logout'))
        self.assertNotIn('skool_guest_auth', self.client.session)
        self.assertContains(self.login(), LOGIN_ERROR)
        self.assertRedirects(self.login(password=self.replacement), reverse('skool:onboarding'), fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse('skool:journey')), 'current:7')

    def test_initial_weak_or_mismatched_passwords_do_not_unlock_account(self):
        self.login()
        for first, second in [(self.initial, self.initial), ('123', '123'), (self.replacement, 'mismatch')]:
            response = self.change(new_password1=first, new_password2=second)
            self.assertEqual(response.status_code, 200)
            self.account.refresh_from_db()
            self.assertTrue(self.account.must_change_password)
            self.assertNotIn('skool_user_id', self.client.session)

    def test_guest_cannot_bypass_password_using_name_or_invitation_token(self):
        for path in [reverse('skool:onboarding'), reverse('skool:labs')]:
            other = Client()
            response = other.post(path, {'full_name': self.user.invitation.full_name})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('skool_user_id', other.session)
        # Even a valid invitation token is not a passwordless credential for a guest.
        invitation, raw = SkoolInvitation.create_invitation('Another Guest')
        user = SkoolUser.objects.create(invitation=invitation, full_name='Another Guest')
        invitation.status = 'claimed'
        invitation.save()
        guest = SkoolGuestAccount(user=user, email='another@example.com')
        guest.set_password(self.initial)
        guest.save()
        self.client.get(reverse('skool:onboarding') + '?invite=' + raw)
        self.client.post(reverse('skool:onboarding'), {'full_name': 'Another Guest'})
        self.assertNotIn('skool_user_id', self.client.session)

    def test_missing_auth_hash_cannot_use_a_guest_profile(self):
        session = self.client.session
        session['skool_user_id'] = self.user.pk
        session.save()
        self.assertRedirects(self.client.get(reverse('skool:journey')), reverse('skool:onboarding'), fetch_redirect_response=False)
        self.assertNotIn('skool_user_id', self.client.session)

    def test_revoked_or_disabled_guests_cannot_login_or_complete_pending_change(self):
        self.login()
        self.account.is_active = False
        self.account.save()
        self.assertRedirects(self.change(), self.login_url, fetch_redirect_response=False)
        self.assertContains(self.login(), LOGIN_ERROR)
        self.account.is_active = True
        self.account.save()
        self.user.invitation.status = 'revoked'
        self.user.invitation.save()
        self.assertContains(self.login(), LOGIN_ERROR)

    def test_password_change_invalidates_other_pending_sessions(self):
        other = Client()
        self.login()
        self.login(client=other)
        self.change()
        self.assertRedirects(other.get(self.change_url), self.login_url, fetch_redirect_response=False)
        self.assertNotIn('skool_guest_pending_id', other.session)

    def test_failed_login_lock_is_shared_across_sessions_and_expires(self):
        for _ in range(5):
            self.assertContains(self.login(client=Client(), password='incorrect'), LOGIN_ERROR)
        self.assertContains(self.login(client=Client()), LOGIN_ERROR)
        self.account.refresh_from_db()
        self.assertGreater(self.account.locked_until, timezone.now())
        self.account.locked_until = timezone.now() - timedelta(seconds=1)
        self.account.save()
        self.assertRedirects(self.login(), self.change_url)

    def test_unknown_and_wrong_password_errors_are_identical(self):
        unknown = self.login(email='unknown@example.com')
        wrong = self.login(password='incorrect')
        self.assertContains(unknown, LOGIN_ERROR)
        self.assertContains(wrong, LOGIN_ERROR)

    def test_csrf_is_required_for_login_and_password_change(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(self.login_url, {'email': self.account.email, 'password': self.initial}).status_code, 403)
        self.assertEqual(client.post(self.change_url, {}).status_code, 403)

    def test_revocation_invalidates_an_authenticated_guest_session(self):
        self.login()
        self.change()
        self.client.post(reverse('skool:onboarding'), {'action': 'accept_withdrawal_notice'})
        self.user.invitation.status = 'revoked'
        self.user.invitation.save()
        self.assertEqual(self.client.post(reverse('skool:mark_intro')).status_code, 302)
        self.assertNotIn('skool_user_id', self.client.session)

    def test_malformed_legacy_session_is_cleared(self):
        session = self.client.session
        session['skool_user_id'] = 'not-an-integer'
        session.save()
        self.assertEqual(self.client.get(reverse('skool:onboarding')).status_code, 200)
        self.assertNotIn('skool_user_id', self.client.session)
