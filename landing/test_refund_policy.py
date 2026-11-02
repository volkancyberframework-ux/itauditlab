from django.test import TestCase, override_settings
from .legal import DOCUMENTS
from .language import metadata_catalog

@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class RefundPolicyTests(TestCase):
    def test_home_and_policy_do_not_offer_refunds(self):
        home = self.client.get('/')
        self.assertContains(home, 'Ücret iadesi yoktur.')
        policy = self.client.get('/yasal/kullanim/')
        self.assertContains(policy, 'ücret iadesi yapılmaz')
        self.assertNotContains(policy, '6502')
        self.assertNotContains(policy, '14 günlük cayma')
        self.assertNotContains(policy, 'tüketici mahkemeleri')

    def test_legacy_terms_address_uses_the_current_policy(self):
        response = self.client.get('/terms-and-conditions/')
        self.assertRedirects(response, '/yasal/kullanim/')

    def test_all_languages_have_updated_refund_copy(self):
        policy = DOCUMENTS['kullanim'][1][2][1]
        faq = 'Ücret iadesi yoktur. Satın almadan önce program içeriğini ve katılım koşullarını incele.'
        for language in ('en', 'fr', 'es', 'ja', 'zh-CN', 'vi', 'ar'):
            with self.subTest(language=language):
                catalog = metadata_catalog(language)
                self.assertIn(policy, catalog)
                self.assertIn(faq, catalog)
                self.assertFalse(any('14 günlük cayma' in key for key in catalog))

    def test_english_policy_does_not_promise_fourteen_day_refunds(self):
        response = self.client.get('/yasal/kullanim/?lang=en&country=US')
        self.assertContains(response, 'does not offer refunds')
        self.assertNotContains(response, '14-day')
