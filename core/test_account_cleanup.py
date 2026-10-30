from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .account_cleanup import delete_reviewed, eligible
from .models import LearningProgram, ProgramEnrollment, Course, LessonEvidence
from mobile_api.models import LearningSession, AccountDeletionRequest

@override_settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_ID='', STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class CleanupTests(TestCase):
    def setUp(self):
        self.admin=get_user_model().objects.create_superuser('cleanupadmin','admin@test.com','test-password-123')
        self.user=get_user_model().objects.create_user('cleanup',email='cleanup@test.com',is_first_login=False)
        self.url=reverse('admin:guarded_account_cleanup')
        self.client.force_login(self.admin)

    def test_protections(self):
        self.assertTrue(eligible(self.user))
        for email in ('guler.volkan@yahoo.com','volkancyberframework@gmail.com'):
            self.user.email=email;self.assertFalse(eligible(self.user))
        self.user.email='cleanup@test.com';self.user.mobile_full_access=True;self.assertFalse(eligible(self.user))
        self.user.mobile_full_access=False;self.user.mobile_paid_until=timezone.now()+timedelta(days=1);self.assertFalse(eligible(self.user))
        self.user.mobile_paid_until=None
        p=LearningProgram.objects.create(slug='cleanup',name='Cleanup',is_active=False)
        ProgramEnrollment.objects.create(user=self.user,program=p,start_date=timezone.localdate(),is_active=False)
        self.assertFalse(eligible(self.user))

    def test_preview_does_not_delete_then_confirm_deletes_nonfinancial_protected_evidence(self):
        c=Course.objects.create(duration=timedelta(hours=1))
        LessonEvidence.objects.create(user=self.user,course=c)
        AccountDeletionRequest.objects.create(user=self.user)
        response=self.client.post(self.url,{'emails':self.user.email})
        self.assertEqual(response.context['evidence_count'],1)
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())
        response=self.client.post(self.url,{'confirm':'yes','token':response.context['token']})
        self.assertEqual(response.context['deleted'],['cleanup@test.com'])
        self.assertFalse(get_user_model().objects.filter(pk=self.user.pk).exists())
        self.assertFalse(LessonEvidence.objects.filter(user_id=self.user.pk).exists())

    def test_recheck_and_signed_selection(self):
        response=self.client.post(self.url,{'emails':self.user.email})
        token=response.context['token']
        self.user.mobile_full_access=True;self.user.save()
        response=self.client.post(self.url,{'confirm':'yes','token':token})
        self.assertEqual(response.context['deleted'],[])
        self.assertEqual(len(response.context['skipped']),1)
        self.assertEqual(self.client.post(self.url,{'confirm':'yes','token':'invalid'}).status_code,403)

    def test_non_superuser_denied_and_get_never_deletes(self):
        self.client.force_login(self.user)
        self.assertIn(self.client.post(self.url,{'emails':self.user.email}).status_code,(302,403))
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url,{'confirm':'yes'}).status_code,200)
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_payment_and_subscription_are_preserved(self):
        from mobile_api.models import MobilePayment, Subscription
        now=timezone.now()
        payment=MobilePayment.objects.create(user=self.user,checkout_session_id='cleanup',payment_intent_id='cleanup',stripe_event_id='cleanup',paid_at=now,access_until=now)
        self.assertFalse(eligible(self.user))
        deleted,skipped=delete_reviewed(self.admin,[self.user.pk])
        self.assertEqual(deleted,[]);self.assertTrue(MobilePayment.objects.filter(pk=payment.pk).exists())
        payment.delete()
        Subscription.objects.create(user=self.user,provider='apple',transaction_id='cleanup',status='expired',expires_at=now,verified_at=now)
        self.assertFalse(eligible(self.user))

    def test_unknown_protected_relation_rolls_back_evidence_and_keeps_user(self):
        from .models import StudentIntervention
        c=Course.objects.create(duration=timedelta(hours=1))
        evidence=LessonEvidence.objects.create(user=self.user,course=c)
        StudentIntervention.objects.create(student=self.user,subject='Review',body='Protected record')
        deleted,skipped=delete_reviewed(self.admin,[self.user.pk])
        self.assertEqual(deleted,[]);self.assertEqual(len(skipped),1)
        self.assertTrue(LessonEvidence.objects.filter(pk=evidence.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())
