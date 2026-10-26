from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_ID='')
class FirstLoginPasswordTests(TestCase):
    def setUp(self):
        self.old_password = 'Old-Access-73!safe'
        self.user = get_user_model().objects.create_user(
            username='password-required', email='required@example.com',
            password=self.old_password, is_first_login=True,
        )
        self.change_url = reverse('force_password_change_popup')
        self.client.force_login(self.user)

    def test_pending_session_cannot_bypass_change_with_get_or_post(self):
        for path in [reverse('dashboard_student'), reverse('course_single', args=[123]),
                     reverse('login'), reverse('landing:home')]:
            for method in [self.client.get, self.client.post]:
                with self.subTest(path=path, method=method.__name__):
                    response = method(path)
                    self.assertRedirects(response, self.change_url, fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_first_login)

    def test_password_page_and_logout_remain_available(self):
        response = self.client.get(self.change_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['show_password_change_popup'])
        self.assertEqual(self.client.get(reverse('logout')).status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_password_change_clears_flag_and_keeps_session(self):
        response = self.client.post(self.change_url, {
            'new_password': 'Fresh-Access-97!unique',
            'confirm_password': 'Fresh-Access-97!unique',
        })
        self.assertRedirects(response, reverse('dashboard_student'), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_first_login)
        self.assertTrue(self.user.check_password('Fresh-Access-97!unique'))
        self.assertEqual(str(self.client.session['_auth_user_id']), str(self.user.pk))
        self.assertEqual(self.client.get(reverse('dashboard_student')).status_code, 200)

    def test_invalid_passwords_do_not_clear_flag_or_change_password(self):
        for first, second in [('', ''), ('123', '123'), ('different', 'mismatch'),
                              (self.old_password, self.old_password)]:
            with self.subTest(first=first):
                response = self.client.post(self.change_url, {
                    'new_password': first, 'confirm_password': second,
                })
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['error'])
                self.user.refresh_from_db()
                self.assertTrue(self.user.is_first_login)
                self.assertTrue(self.user.check_password(self.old_password))

    def test_password_change_requires_csrf_and_authentication(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(self.change_url, {}).status_code, 403)
        client.logout()
        self.assertRedirects(client.get(self.change_url),
                             reverse('login') + '?next=' + self.change_url,
                             fetch_redirect_response=False)

    def test_completed_account_can_access_dashboard(self):
        self.user.is_first_login = False
        self.user.save(update_fields=['is_first_login'])
        self.assertEqual(self.client.get(reverse('dashboard_student')).status_code, 200)

    def test_actual_login_then_navigation_still_requires_password_change(self):
        self.client.logout()
        response = self.client.post(reverse('login'), {
            'email': self.user.email, 'password': self.old_password,
        })
        self.assertTrue(response.context['show_password_change_popup'])
        self.assertRedirects(self.client.get(reverse('dashboard_student')), self.change_url,
                             fetch_redirect_response=False)

    def test_password_change_invalidates_other_existing_sessions(self):
        other = Client()
        other.force_login(self.user)
        self.client.post(self.change_url, {
            'new_password': 'Fresh-Access-97!unique',
            'confirm_password': 'Fresh-Access-97!unique',
        })
        response = other.get(reverse('dashboard_student'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))
        self.assertNotIn('_auth_user_id', other.session)

    def test_admin_is_not_locked_out_by_legacy_first_login_flag(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)
