from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse

@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class AuthenticationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('person@example.com','Initial-Password-384!')
    def signin(self, **extra):
        return self.client.post('/signin/', {'username':self.user.email, 'password':'Initial-Password-384!', **extra})
    def test_root_shows_signin(self):
        self.assertContains(self.client.get('/'), 'Tekrar hoş geldiniz.')
    @override_settings(ROOT_SIGNIN_ENABLED=False)
    def test_root_can_be_removed_without_removing_signin(self):
        self.assertEqual(self.client.get('/').status_code,404)
        self.assertEqual(self.client.get('/signin/').status_code,200)
    def test_first_login_requires_password_change(self):
        self.assertRedirects(self.signin(),'/password/change/')
        self.assertRedirects(self.client.get('/console/'),'/password/change/')
    def test_password_change_unlocks_console(self):
        self.signin()
        response=self.client.post('/password/change/', {'old_password':'Initial-Password-384!','new_password1':'New-Unique-Password-897!','new_password2':'New-Unique-Password-897!'})
        self.assertRedirects(response,'/console/')
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)
        self.assertTrue(self.user.check_password('New-Unique-Password-897!'))
    def test_anonymous_console_protected(self):
        self.assertEqual(self.client.get('/console/').status_code,302)
    def test_invalid_credentials_fail(self):
        response=self.signin(password='incorrect')
        self.assertContains(response,'E-posta veya parola hatalı')
        self.assertNotIn('_auth_user_id',self.client.session)
    def test_uppercase_email_supported(self):
        self.assertEqual(self.signin(username='PERSON@EXAMPLE.COM').status_code,302)
    def test_remember_uses_bounded_session(self):
        self.signin(remember='on')
        self.assertEqual(self.client.session.get_expiry_age(),43200)
    def test_default_session_expires_on_browser_close(self):
        self.signin()
        self.assertTrue(self.client.session.get_expire_at_browser_close())
    def test_csrf_required(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/signin/',{'username':self.user.email,'password':'Initial-Password-384!'}).status_code,403)
    def test_logout_requires_post(self):
        self.signin()
        self.assertEqual(self.client.get('/signout/').status_code,405)
        self.assertEqual(self.client.post('/signout/').status_code,302)
        self.assertNotIn('_auth_user_id',self.client.session)
    def test_external_next_cannot_redirect(self):
        self.user.must_change_password=False;self.user.save()
        response=self.client.post('/signin/?next=https://example.net/',{'username':self.user.email,'password':'Initial-Password-384!'})
        self.assertRedirects(response,'/console/')
    def test_login_attempts_are_limited(self):
        for _ in range(5):
            self.signin(password='wrong')
        response=self.signin()
        self.assertEqual(response.status_code,429)
        self.assertNotIn('_auth_user_id',self.client.session)
    def test_inactive_user_cannot_login(self):
        self.user.is_active=False;self.user.save()
        self.signin()
        self.assertNotIn('_auth_user_id',self.client.session)


@override_settings(ALLOWED_HOSTS=['.grcustasi.com'], STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class SharedDeploymentTests(TestCase):
    def test_central_www_signin_and_unknown_tenant(self):
        self.assertEqual(self.client.get('/signin/',HTTP_HOST='www.grcustasi.com').status_code,200)
        self.assertEqual(self.client.get('/signin/',HTTP_HOST='undefined.grcustasi.com').status_code,404)

    def test_bootstrap_import_keeps_password_and_never_overwrites_existing_user(self):
        import io,json
        from unittest.mock import patch
        from django.core.management import call_command
        from django.contrib.auth.hashers import make_password
        entries=[dict(email='admin@example.test',password=make_password('first-secret'),first_name='First',last_name='Admin')]
        with patch('sys.stdin',io.StringIO(json.dumps(entries))):call_command('import_platform_admins',stdout=io.StringIO())
        user=get_user_model().objects.get(email='admin@example.test')
        self.assertTrue(user.check_password('first-secret'))
        self.assertTrue(user.is_superuser)
        self.assertFalse(user.must_change_password)
        user.set_password('changed-secret');user.save()
        with patch('sys.stdin',io.StringIO(json.dumps(entries))):call_command('import_platform_admins',stdout=io.StringIO())
        user.refresh_from_db();self.assertTrue(user.check_password('changed-secret'))
