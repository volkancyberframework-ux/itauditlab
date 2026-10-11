from django.test import TestCase, override_settings
from .models import MobileWaitlist


@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class MobileWaitlistTests(TestCase):
    def test_old_links_redirect_and_no_longer_collect_email(self):
        for method in (self.client.get, self.client.post):
            response = method('/mobil-bekleme-listesi/', {'email': 'demo@example.com'})
            self.assertRedirects(response, '/')
        self.assertFalse(MobileWaitlist.objects.exists())
