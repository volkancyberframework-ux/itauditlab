from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.core import signing
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings, Client
from django.urls import reverse
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from .models import (Course, Enrollment, LearningProgram, LearningProgramStep, ProgramEnrollment,
                     ProgramRelease, LessonEvidence, ProgramProgressViolation, MonitoringLessonOverride)
from .progress_guard import (blockers, issue_confirmation, disable_after_confirmation, deliver_instant,
                             send_morning_violations, entry_context)


@override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}},
                   TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_ID='')
class ProgressGuardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('guard', email='guard@example.test', password='Password-test-333',
                                                        is_first_login=False, is_turkish=True)
        self.program = LearningProgram.objects.create(slug='guard', name='GRC Test')
        self.old = Course.objects.create(duration=timedelta(hours=1),turkish_name='Önceki ders', dashboard_activated=True, is_turkish=True)
        self.new = Course.objects.create(duration=timedelta(hours=1),turkish_name='Yeni ders', dashboard_activated=True, is_turkish=True)
        self.first = LearningProgramStep.objects.create(program=self.program,course=self.old,day_offset=0)
        self.second = LearningProgramStep.objects.create(program=self.program,course=self.new,day_offset=1)
        self.enrollment = ProgramEnrollment.objects.create(user=self.user,program=self.program,
                            start_date=timezone.localdate()-timedelta(days=2),progress_warning_enabled=True)
        for step in [self.first,self.second]:
            ProgramRelease.objects.create(enrollment=self.enrollment,step=step,access_granted_at=timezone.now()-timedelta(days=1))
        self.evidence = LessonEvidence.objects.create(user=self.user,course=self.old,completion_known=True,evidence='Tamamlanmadığı doğrulandı.')
        self.client.force_login(self.user)

    def token(self):
        return issue_confirmation(self.user,self.new,blockers(self.user,self.new))

    def confirm(self, **extra):
        data={'continue_despite_warning':'yes','confirmation_token':self.token()};data.update(extra)
        return self.client.post(reverse('program_progress_confirm',args=[self.new.pk]),data)

    def test_default_off_and_flagged_program_scope(self):
        self.assertTrue(blockers(self.user,self.new))
        self.enrollment.progress_warning_enabled=False;self.enrollment.save()
        self.assertFalse(blockers(self.user,self.new))
        other=Course.objects.create(duration=timedelta(hours=1),turkish_name='Başka ders')
        self.assertFalse(blockers(self.user,other))
        self.assertFalse(ProgramEnrollment._meta.get_field('progress_warning_enabled').default)

    def test_completed_unknown_exempt_and_unopened_do_not_sanction(self):
        self.evidence.completion_known=False;self.evidence.save()
        self.assertFalse(blockers(self.user,self.new))
        self.evidence.completion_known=True;self.evidence.completed_at=timezone.now();self.evidence.save()
        self.assertFalse(blockers(self.user,self.new))
        self.evidence.completed_at=None;self.evidence.save()
        override=MonitoringLessonOverride.objects.create(enrollment=self.enrollment,step=self.first,exempt=True)
        self.assertFalse(blockers(self.user,self.new));override.delete()
        ProgramRelease.objects.filter(step=self.second).update(access_granted_at=None)
        self.assertFalse(blockers(self.user,self.new))

    def test_existing_lesson_and_staff_are_exempt(self):
        LessonEvidence.objects.create(user=self.user,course=self.new,first_accessed_at=timezone.now())
        self.assertFalse(blockers(self.user,self.new))
        self.user.is_staff=True
        self.assertFalse(blockers(self.user,self.new))

    def test_entry_warning_and_acknowledgement_never_disable(self):
        response=self.client.get(reverse('dashboard_student'))
        self.assertContains(response,'programProgressEntryModal')
        self.assertEqual(self.client.post(reverse('program_progress_ack'),{'acknowledged':'yes'}).status_code,302)
        self.assertNotContains(self.client.get(reverse('dashboard_student')),'id="programProgressEntryModal"')
        self.client.logout();self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('dashboard_student')),'id="programProgressEntryModal"')
        self.user.refresh_from_db();self.assertTrue(self.user.is_active)
        self.assertFalse(ProgramProgressViolation.objects.exists())

    def test_enroll_post_only_displays_confirmation(self):
        response=self.client.post(reverse('dashboard_student'),{'course_id':self.new.pk})
        self.assertContains(response,'İKİNCİ UYARI')
        self.assertContains(response,'hemen devre dışı')
        self.assertFalse(Enrollment.objects.filter(user=self.user,course=self.new).exists())
        self.user.refresh_from_db();self.assertTrue(self.user.is_active)

    def test_automatic_video_enrollment_and_deep_link_cannot_bypass(self):
        Enrollment.objects.create(user=self.user,course=self.new)
        response=self.client.get(reverse('course_single',args=[self.new.pk]))
        self.assertContains(response,'İKİNCİ UYARI')
        self.assertFalse(LessonEvidence.objects.filter(user=self.user,course=self.new).exists())
        self.assertTrue(self.user.is_active)

    def test_question_api_does_not_bypass_confirmation(self):
        self.new.course_type='test';self.new.save();self.user.allowed_tests.add(self.new)
        self.assertEqual(self.client.get(reverse('course_random_question',args=[self.new.pk])).status_code,409)
        self.user.refresh_from_db();self.assertTrue(self.user.is_active)

    @patch('core.progress_guard.deliver_instant',return_value=True)
    def test_first_explicit_confirmation_disables_and_revokes_refresh(self,send):
        RefreshToken.for_user(self.user)
        with self.captureOnCommitCallbacks(execute=True):
            response=self.confirm()
        self.assertEqual(response.status_code,403)
        self.user.refresh_from_db();self.assertFalse(self.user.is_active)
        self.assertNotIn('_auth_user_id',self.client.session)
        event=ProgramProgressViolation.objects.get()
        self.assertEqual(event.programs[0]['incomplete'][0]['course_id'],self.old.pk)
        self.assertEqual(BlacklistedToken.objects.filter(token__user=self.user).count(),OutstandingToken.objects.filter(user=self.user).count())
        send.assert_called_once_with(event.pk)
        self.assertFalse(Enrollment.objects.filter(user=self.user,course=self.new).exists())

    def test_invalid_missing_or_unchecked_confirmation_does_not_disable(self):
        for extra in [{'confirmation_token':'tampered'},{'continue_despite_warning':''},{'confirmation_token':issue_confirmation(self.user,self.old,blockers(self.user,self.old))}]:
            self.assertEqual(self.confirm(**extra).status_code,400)
        self.user.refresh_from_db();self.assertTrue(self.user.is_active)
        self.assertFalse(ProgramProgressViolation.objects.exists())

    def test_expired_confirmation_does_not_disable(self):
        import time
        token = self.token()
        with patch('django.core.signing.time.time', return_value=time.time()+1801):
            self.assertEqual(self.confirm(confirmation_token=token).status_code,400)
        self.user.refresh_from_db();self.assertTrue(self.user.is_active)

    def test_evidence_change_invalidates_old_confirmation(self):
        token=self.token();self.evidence.completed_at=timezone.now();self.evidence.save()
        self.assertEqual(self.confirm(confirmation_token=token).status_code,302)
        self.user.refresh_from_db();self.assertTrue(self.user.is_active)

    def test_flag_removed_invalidates_old_confirmation(self):
        token=self.token();self.enrollment.progress_warning_enabled=False;self.enrollment.save()
        self.assertEqual(self.confirm(confirmation_token=token).status_code,302)
        self.assertFalse(ProgramProgressViolation.objects.exists())

    @patch('core.progress_guard.deliver_instant',return_value=True)
    def test_replayed_confirmation_is_idempotent(self,_):
        token=self.token()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertIsNotNone(disable_after_confirmation(self.user,self.new,token))
            self.assertIsNone(disable_after_confirmation(self.user,self.new,token))
        self.assertEqual(ProgramProgressViolation.objects.count(),1)

    def make_event(self):
        import uuid
        return ProgramProgressViolation.objects.create(user=self.user,email=self.user.email,course_id_snapshot=self.new.pk,
                    course_title=str(self.new),programs=blockers(self.user,self.new),confirmation_id=uuid.uuid4())

    @patch('core.progress_guard.telegram',return_value=False)
    def test_delivery_failure_keeps_retryable_audit_record(self,send):
        event=self.make_event();self.assertFalse(deliver_instant(event.pk))
        event.refresh_from_db();self.assertIsNone(event.instant_sent_at)

    @patch('core.progress_guard.telegram',return_value=True)
    def test_morning_alert_next_day_once_and_retries_instant(self,send):
        event=self.make_event();today=timezone.localdate()
        self.assertEqual(send_morning_violations(today),0)
        self.assertEqual(send_morning_violations(today+timedelta(days=1)),1)
        self.assertEqual(send_morning_violations(today+timedelta(days=1)),0)
        self.assertEqual(send.call_count,2)
        self.assertIn('ALARM ALARM ALARM',send.call_args_list[0].args[0])
        self.assertIn('Sabah ihlal bildirimi',send.call_args_list[1].args[0])

    @patch('core.program_automation.send_welcome')
    @patch('core.program_automation.send_release_email')
    @patch('core.course_pdf_checks.inspect_course_pdf',return_value={'status':'present','course_id':1,'course':'Test'})
    def test_flag_does_not_stop_daily_releases_or_disable(self,*_):
        from .program_automation import run_daily_programs
        ProgramRelease.objects.all().delete()
        run_daily_programs(timezone.localdate())
        self.assertEqual(ProgramRelease.objects.filter(access_granted_at__isnull=False).count(),2)
        self.user.refresh_from_db();self.assertTrue(self.user.is_active)
        self.assertFalse(ProgramProgressViolation.objects.exists())

    @patch('core.progress_guard.telegram', return_value=False)
    def test_failed_instant_alert_does_not_undo_disabling(self, _):
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.confirm().status_code, 403)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIsNone(ProgramProgressViolation.objects.get().instant_sent_at)

    def test_confirmation_requires_csrf(self):
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.user)
        response = secure.post(reverse('program_progress_confirm', args=[self.new.pk]),
                               {'confirmation_token':self.token(),'continue_despite_warning':'yes'})
        self.assertEqual(response.status_code,403)
        self.user.refresh_from_db();self.assertTrue(self.user.is_active)

    @patch('core.progress_guard.deliver_instant',return_value=True)
    def test_other_browser_session_loses_access(self, _):
        other=Client();other.force_login(self.user)
        with self.captureOnCommitCallbacks(execute=True): self.confirm()
        self.assertEqual(other.get(reverse('dashboard_student')).status_code,302)

    def test_prior_incomplete_work_can_still_be_opened(self):
        Enrollment.objects.create(user=self.user,course=self.old)
        self.assertEqual(self.client.get(reverse('course_single',args=[self.old.pk])).status_code,200)
        self.assertFalse(ProgramProgressViolation.objects.exists())

    def test_another_users_confirmation_is_rejected(self):
        other=get_user_model().objects.create_user('another',email='another@example.test',password='Password-test-33')
        token=issue_confirmation(other,self.new,blockers(self.user,self.new))
        self.assertEqual(self.confirm(confirmation_token=token).status_code,400)
        self.user.refresh_from_db();self.assertTrue(self.user.is_active)
