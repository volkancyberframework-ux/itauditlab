from django.test import TestCase, Client
from django.core.cache import cache
from .models import MobileWaitlist

class MobileWaitlistTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_email_only_and_duplicate_is_normalized(self):
        url = '/mobil-bekleme-listesi/'
        response = self.client.get(url)
        self.assertContains(response, 'name="email"')
        self.assertNotContains(response, 'name="password"')
        for email in ['Demo@Example.com', 'demo@example.com']:
            response = self.client.post(url, {'email': email}, follow=True)
            self.assertContains(response, 'Kaydın alındı.')
        self.assertEqual(MobileWaitlist.objects.count(), 1)
        self.assertEqual(MobileWaitlist.objects.get().email, 'demo@example.com')

    def test_invalid_email_and_csrf_rejected(self):
        self.assertEqual(self.client.post('/mobil-bekleme-listesi/', {'email':'bad'}).status_code, 400)
        protected = Client(enforce_csrf_checks=True)
        self.assertEqual(protected.post('/mobil-bekleme-listesi/', {'email':'a@example.com'}).status_code, 403)
        protected.get('/mobil-bekleme-listesi/')
        self.assertEqual(protected.post('/mobil-bekleme-listesi/', {'email':'a@example.com',
            'csrfmiddlewaretoken': protected.cookies['csrftoken'].value}).status_code, 302)

    def test_landing_and_login_link_to_waitlist_and_badges(self):
        for url in ['/', '/login/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, '/mobil-bekleme-listesi/')
            self.assertContains(response, 'appstore.svg')
            self.assertContains(response, 'playstore.svg')

    def test_rate_limit_rejects_without_saving_extra_address(self):
        for i in range(10):
            self.assertEqual(self.client.post('/mobil-bekleme-listesi/', {'email':'same@example.com'}).status_code,302)
        self.assertEqual(self.client.post('/mobil-bekleme-listesi/', {'email':'same@example.com'}).status_code,429)
        self.assertEqual(MobileWaitlist.objects.count(),1)
