from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from .models import FirstLoginServiceConsent, ContactChangeNotice
from .service_consent import NOTICE_VERSION, NOTICE_TEXT, IMMEDIATE_LABEL, ACKNOWLEDGEMENT_LABEL

@override_settings(TELEGRAM_BOT_TOKEN='',TELEGRAM_CHAT_ID='')
class FirstLoginServiceConsentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('first-consent',email='first@example.test',password='Temporary-access-123!',is_first_login=True)
        self.client.force_login(self.user)
        self.url = reverse('first_login_service_consent')
        self.payload = {'notice_version':NOTICE_VERSION, 'immediate_performance':'yes', 'acknowledge':'yes'}

    def test_pending_user_cannot_skip_to_courses_or_password_change(self):
        for path in [reverse('dashboard_student'), reverse('force_password_change_popup'), reverse('course_single',args=[1])]:
            for method in [self.client.get,self.client.post]:
                self.assertRedirects(method(path),self.url,fetch_redirect_response=False)
        self.assertEqual(FirstLoginServiceConsent.objects.count(),0)

    def test_notice_is_visible_and_checkboxes_not_preselected(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'Cayma hakkı bulunmamaktadır.')
        self.assertContains(response, 'Ödenen tutar iade edilmez.')
        self.assertNotContains(response, ' checked')
        self.assertEqual(FirstLoginServiceConsent.objects.count(),0)

    def test_missing_or_stale_acknowledgement_is_not_saved(self):
        for payload in [{},dict(self.payload,acknowledge=''),dict(self.payload,immediate_performance=''),dict(self.payload,notice_version='old')]:
            self.assertEqual(self.client.post(self.url,payload).status_code,400)
        self.assertEqual(FirstLoginServiceConsent.objects.count(),0)

    def test_acceptance_is_persistent_idempotent_and_password_change_still_required(self):
        self.assertRedirects(self.client.post(self.url,self.payload),reverse('force_password_change_popup'),fetch_redirect_response=False)
        consent = FirstLoginServiceConsent.objects.get(user=self.user)
        self.assertEqual(consent.notice_text,'\n\n'.join((NOTICE_TEXT,IMMEDIATE_LABEL,ACKNOWLEDGEMENT_LABEL)))
        self.assertEqual(consent.version,NOTICE_VERSION)
        self.assertTrue(consent.immediate_performance and consent.no_refund_acknowledged)
        self.assertIsNotNone(consent.accepted_at)
        original = consent.accepted_at
        self.client.post(self.url,self.payload)
        consent.refresh_from_db(); self.assertEqual(consent.accepted_at,original)
        self.client.logout();self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('dashboard_student')),reverse('force_password_change_popup'),fetch_redirect_response=False)
        self.client.post(reverse('force_password_change_popup'),{'new_password':'Brand-New-Access-491!','confirm_password':'Brand-New-Access-491!'})
        self.user.refresh_from_db();self.assertFalse(self.user.is_first_login)
        self.assertEqual(self.client.get(reverse('dashboard_student')).status_code,200)

    def test_existing_completed_user_is_not_given_a_fake_acceptance(self):
        self.user.is_first_login=False;self.user.save(update_fields=['is_first_login'])
        self.assertRedirects(self.client.get(self.url),reverse('dashboard_student'),fetch_redirect_response=False)
        self.assertEqual(FirstLoginServiceConsent.objects.count(),0)

    def test_csrf_and_logout(self):
        secure = Client(enforce_csrf_checks=True);secure.force_login(self.user)
        self.assertEqual(secure.post(self.url,self.payload).status_code,403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code,302)
        self.assertEqual(FirstLoginServiceConsent.objects.count(),0)

    def test_contact_notice_does_not_create_a_redirect_loop_and_policy_is_readable(self):
        ContactChangeNotice.objects.create(user=self.user)
        self.assertEqual(self.client.get(self.url).status_code,200)
        self.assertEqual(self.client.get(reverse('landing:legal',args=['kullanim'])).status_code,200)

    def test_actual_login_redirects_to_notice(self):
        self.client.logout()
        response = self.client.post(reverse('login'),{'email':self.user.email,'password':'Temporary-access-123!'})
        self.assertRedirects(response,self.url,fetch_redirect_response=False)

    def test_admin_cannot_edit_consent_evidence(self):
        admin = get_user_model().objects.create_superuser('consent-admin','admin@example.test','Admin-Password-123!')
        consent = FirstLoginServiceConsent.objects.create(user=self.user,version=NOTICE_VERSION,notice_text=NOTICE_TEXT,immediate_performance=True,no_refund_acknowledged=True)
        self.client.force_login(admin)
        url = reverse('admin:core_firstloginserviceconsent_change',args=[consent.pk])
        self.assertEqual(self.client.get(url).status_code,200)
        self.assertEqual(self.client.post(url,{'notice_text':'edited'}).status_code,403)
        consent.refresh_from_db();self.assertEqual(consent.notice_text,NOTICE_TEXT)
