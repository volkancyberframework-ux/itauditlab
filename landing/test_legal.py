from django.test import TestCase, Client, override_settings
from .models import LandingVisit

@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class LegalConsentTests(TestCase):
    headers = {'HTTP_USER_AGENT': 'Mozilla/5.0 Safari/605.1.15'}

    def test_no_tracking_without_consent(self):
        response = self.client.get('/', **self.headers)
        self.assertNotIn('grc_vid', response.cookies)
        self.assertFalse(LandingVisit.objects.exists())
        self.assertContains(response, 'Çerezleri kabul ediyor musunuz?')
        self.assertIn('csrftoken', response.cookies)

    def test_accept_then_withdraw(self):
        self.assertEqual(self.client.post('/api/cerez-tercihi/', {'analytics': 'true'}).status_code, 200)
        self.client.get('/', **self.headers)
        self.assertEqual(LandingVisit.objects.count(), 1)
        response = self.client.post('/api/cerez-tercihi/', {'analytics': 'false'})
        self.assertEqual(response.cookies['grc_vid']['max-age'], 0)
        self.client.get('/', **self.headers)
        self.assertEqual(LandingVisit.objects.get().page_views, 1)

    def test_forged_consent_does_not_enable_tracking(self):
        self.client.cookies['grc_consent'] = 'true'
        self.client.get('/', **self.headers)
        self.assertFalse(LandingVisit.objects.exists())

    def test_csrf_and_invalid_choices(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/api/cerez-tercihi/', {'analytics': 'true'}).status_code, 403)
        client.get('/', **self.headers)
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post('/api/cerez-tercihi/', {'analytics': 'true', 'csrfmiddlewaretoken': token}).status_code, 200)
        self.assertEqual(self.client.post('/api/cerez-tercihi/', {'analytics': 'yes'}).status_code, 400)

    def test_documents(self):
        for slug in ('kvkk', 'gizlilik', 'cerez', 'kullanim'):
            response = self.client.get('/yasal/' + slug + '/')
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Volkan Güler')
            self.assertContains(response, 'data-cookie-settings')
        self.assertEqual(self.client.get('/yasal/unknown/').status_code, 404)
