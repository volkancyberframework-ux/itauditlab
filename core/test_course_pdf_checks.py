from datetime import datetime, timedelta, time
from io import StringIO
from unittest.mock import MagicMock, PropertyMock, patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from .course_pdf_checks import inspect_course_pdf, check_released_course_pdfs
from .models import Course, LearningProgram, LearningProgramStep, ProgramEnrollment, ProgramRelease
from .program_automation import run_daily_programs, format_daily_program_summary


@override_settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_ID='')
class CourseAttachmentChecksTests(TestCase):
    def setUp(self):
        self.day = timezone.localdate()
        self.user = get_user_model().objects.create_user(username='attachment-student', email='student@example.test')
        self.course = Course.objects.create(turkish_name='Firewall ve Segmentasyon', duration=timedelta(hours=1),
                                            difficulty='Beginner', description='Attachment fixture', course_type='test')
        self.program = LearningProgram.objects.create(slug='attachment-check-program', name='Bootcamp')
        self.step = LearningProgramStep.objects.create(program=self.program, course=self.course, day_offset=0)
        self.enrollment = ProgramEnrollment.objects.create(user=self.user, program=self.program, start_date=self.day)
        for target in ('send_welcome', 'send_release_email'):
            mock = patch('core.program_automation.' + target)
            mock.start(); self.addCleanup(mock.stop)

    def attach(self, name='course_attachments/lesson.pdf'):
        self.course.attachment = name; self.course.save(update_fields=['attachment'])

    def test_empty_attachment_alerts_without_blocking_release(self):
        stats = run_daily_programs(self.day)
        self.assertEqual(stats['courses'], 1); self.assertEqual(stats['failed'], 0)
        self.assertEqual(stats['pdf_checked'], 1)
        self.assertEqual(stats['pdf_missing'][0]['course_id'], self.course.pk)
        self.assertTrue(self.user.allowed_tests.filter(pk=self.course.pk).exists())
        self.assertEqual(ProgramRelease.objects.get(enrollment=self.enrollment, step=self.step).status, 'sent')
        report = format_daily_program_summary(stats, self.day)
        self.assertIn(f'🚨 Course ID: {self.course.pk} — Firewall ve Segmentasyon — Bu dersin ek dosya alanı boş.', report)
        self.assertLess(report.index('EK DOSYA EKSİĞİ'), report.index('Açılan içerik detayları'))
        self.assertNotIn('PDF', report)

    def test_every_file_type_is_sufficient_without_network_or_storage_access(self):
        with patch('requests.get', side_effect=AssertionError('No network check allowed')), \
             patch.object(type(self.course.attachment), 'url', new_callable=PropertyMock,
                          side_effect=AssertionError('No storage URL check allowed')):
            for name in ['lesson.pdf','lesson.docx','lesson.xlsx','lesson.zip','lesson.png','lesson.mp4','lesson-download']:
                with self.subTest(name=name):
                    self.attach('course_attachments/'+name)
                    self.assertEqual(inspect_course_pdf(self.course)['status'], 'present')
                    stats = run_daily_programs(self.day)
                    self.assertEqual(stats['pdf_missing'], [])
                    self.assertEqual(stats['pdf_unverified'], [])
                    self.assertIn('✅ Açılan derslerin ek dosya alanları dolu.', format_daily_program_summary(stats,self.day))

    def test_empty_or_whitespace_file_names_are_missing(self):
        for value in [None,'','   ']:
            self.attach(value)
            self.assertEqual(inspect_course_pdf(self.course)['status'],'missing')

    def test_same_course_for_multiple_students_is_reported_once(self):
        other = get_user_model().objects.create_user(username='attachment-second', email='second@example.test')
        ProgramEnrollment.objects.create(user=other, program=self.program, start_date=self.day)
        stats = run_daily_programs(self.day)
        self.assertEqual(stats['courses'], 2); self.assertEqual(stats['pdf_checked'], 1)
        self.assertEqual(len(stats['pdf_missing']), 1)

    def test_same_day_rerun_rechecks_field_without_reopening_or_remailing(self):
        first = run_daily_programs(self.day); second = run_daily_programs(self.day)
        self.assertEqual((first['courses'], second['courses']), (1, 0))
        self.assertEqual(second['emails'], 0); self.assertEqual(second['pdf_checked'], 1)
        self.assertEqual(second['pdf_missing'][0]['course_id'], self.course.pk)
        self.attach('course_attachments/exercise.xlsx')
        fixed = run_daily_programs(self.day)
        self.assertEqual(fixed['pdf_missing'], []); self.assertEqual(fixed['courses'], 0)

    def test_yesterdays_email_retry_is_not_todays_attachment_alarm(self):
        self.enrollment.start_date = self.day - timedelta(days=1)
        self.enrollment.welcome_sent_at = timezone.now(); self.enrollment.save()
        ProgramRelease.objects.create(enrollment=self.enrollment, step=self.step,
                                      access_granted_at=timezone.now()-timedelta(days=1), status='failed')
        stats = run_daily_programs(self.day)
        self.assertEqual(stats['courses'], 0); self.assertEqual(stats['pdf_checked'], 0)

    def test_local_day_boundary_and_future_lessons(self):
        tz = ZoneInfo('Europe/Istanbul'); start = datetime.combine(self.day, time.min, tzinfo=tz)
        release = ProgramRelease.objects.create(enrollment=self.enrollment, step=self.step,
                                                access_granted_at=start-timedelta(seconds=1), status='sent')
        with timezone.override(tz):
            self.assertEqual(check_released_course_pdfs(self.day)['pdf_checked'], 0)
            release.access_granted_at=start; release.save()
            self.assertEqual(check_released_course_pdfs(self.day)['pdf_checked'], 1)
            release.access_granted_at=start+timedelta(days=1); release.save()
            self.assertEqual(check_released_course_pdfs(self.day)['pdf_checked'], 0)

    def test_scheduled_command_keeps_warning_in_existing_telegram_summary(self):
        stats = run_daily_programs(self.day)
        with patch('core.management.commands.run_daily_programs.run_daily_programs',return_value=stats), \
             patch('core.management.commands.run_daily_programs.notify_telegram') as notify, \
             patch('core.management.commands.run_daily_programs.send_daily_report_email'), \
             patch('core.management.commands.run_daily_programs.send_daily_traffic_report'), \
             patch('core.management.commands.run_daily_programs.send_daily_meeting_digest'), \
             patch('core.management.commands.run_daily_programs.send_weekly_telegram_note'), \
             patch('core.student_monitoring.capture_snapshot',return_value=(MagicMock(reporting_date=self.day),True)):
            call_command('run_daily_programs',stdout=StringIO())
        notify.assert_called_once()
        text=notify.call_args.args[0]
        self.assertIn('Günlük GRC Ustası programı',text)
        self.assertIn(f'Course ID: {self.course.pk}',text)
        self.assertIn('Bu dersin ek dosya alanı boş.',text)
        self.assertNotIn('PDF',text)
