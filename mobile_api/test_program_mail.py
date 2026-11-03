from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from .models import LearningPath, Question, ProgramEmailDelivery, ProgramEmailCampaign
from .program_mail import public_paths, prepare_campaign, drain


class ProgramMailTests(TestCase):
    def setUp(self):
        LearningPath.objects.all().delete()
        get_user_model().objects.all().update(is_mobile=False)
        self.user = get_user_model().objects.create_user(username='mobile', email='Mobile@example.com', first_name='Ayşe', is_mobile=True, mobile_email_verified=True)

    def path(self, **kwargs):
        path = LearningPath.objects.create(title='Denetim', published=True, **kwargs)
        q = Question.objects.create(kind='choice', prompt='Soru', published=True)
        q.paths.add(path)
        return path

    def test_catalogue_is_private_named_and_repeat_safe(self):
        self.path()
        call_command('send_mobile_program_emails', catalogue=True)
        self.assertEqual(len(mail.outbox), 0)
        call_command('send_mobile_program_emails', catalogue=True, send=True)
        call_command('send_mobile_program_emails', catalogue=True, send=True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Merhaba Ayşe,', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ['mobile@example.com'])

    def test_exclusions_and_deduplication(self):
        self.path()
        self.path(preferences={'web_only': True})
        self.path(owner=self.user)
        LearningPath.objects.create(title='Boş', published=True)
        get_user_model().objects.create_user(username='duplicate', email='mobile@example.com', is_mobile=True, mobile_email_verified=True)
        get_user_model().objects.create_user(username='website', email='website@example.com')
        get_user_model().objects.create_user(username='unverified', email='unverified@example.com', is_mobile=True, mobile_email_verified=False)
        campaign = prepare_campaign('catalogue-test', public_paths())
        self.assertEqual(campaign.titles, ['Denetim'])
        self.assertEqual(campaign.programemaildelivery_set.count(), 1)

    def test_publication_with_content_sends_once_after_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            path = self.path()
        self.assertEqual(len(mail.outbox), 1)
        with self.captureOnCommitCallbacks(execute=True):
            path.save()
        self.assertEqual(len(mail.outbox), 1)

    def test_failure_retries_and_sent_rows_skip(self):
        self.path()
        campaign = prepare_campaign('retry', public_paths())
        with patch('mobile_api.program_mail.send_mail', side_effect=OSError):
            self.assertEqual(drain(campaign), 0)
        row = ProgramEmailDelivery.objects.get(campaign=campaign)
        self.assertIsNone(row.sent_at)
        self.assertEqual(drain(campaign), 1)
        self.assertEqual(drain(campaign), 0)

    def test_unpublished_before_retry_does_not_send(self):
        path = self.path()
        campaign = prepare_campaign(f'path-{path.pk}', public_paths(), path)
        LearningPath.objects.filter(pk=path.pk).update(published=False)
        self.assertEqual(drain(campaign), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_admin_catalogue_get_does_not_send_and_post_requires_csrf(self):
        from django.test import Client
        self.path()
        admin = get_user_model().objects.create_superuser(username='operator', email='operator@example.com', password='test')
        client = Client(enforce_csrf_checks=True)
        route = '/bulamazsinki/mobile_api/programemailcampaign/catalogue/'
        self.assertEqual(client.get(route).status_code, 302)
        client.force_login(admin)
        self.assertEqual(client.get(route).status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(client.post(route).status_code, 403)
        response = client.post(route, {'csrfmiddlewaretoken': client.cookies['csrftoken'].value})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
