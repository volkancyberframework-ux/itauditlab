from datetime import datetime, timedelta, time
from io import StringIO
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import requests
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from .course_pdf_checks import inspect_course_pdf, check_released_course_pdfs
from .models import Course, LearningProgram, LearningProgramStep, ProgramEnrollment, ProgramRelease
from .program_automation import run_daily_programs, format_daily_program_summary


@override_settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_ID='', PUBLIC_BASE_URL='https://www.grcustasi.com')
class CoursePdfChecksTests(TestCase):
    def setUp(self):
        self.day = timezone.localdate()
        self.user = get_user_model().objects.create_user(username='pdf-student', email='student@example.test')
        self.course = Course.objects.create(turkish_name='Firewall ve Segmentasyon', duration=timedelta(hours=1),
                                            difficulty='Beginner', description='PDF check fixture', course_type='test')
        self.program = LearningProgram.objects.create(slug='pdf-check-program', name='Bootcamp')
        self.step = LearningProgramStep.objects.create(program=self.program, course=self.course, day_offset=0)
        self.enrollment = ProgramEnrollment.objects.create(user=self.user, program=self.program, start_date=self.day)
        for target in ('send_welcome', 'send_release_email'):
            mock = patch('core.program_automation.' + target)
            mock.start(); self.addCleanup(mock.stop)

    def response(self, status=200, data=b'%PDF-1.7\nfixture', content_type='application/pdf'):
        response = MagicMock()
        response.status_code = status; response.headers = {'Content-Type': content_type}
        response.iter_content.return_value = iter([data])
        response.__enter__.return_value = response
        return response

    def attach(self, name='course_attachments/lesson.PDF'):
        self.course.attachment = name; self.course.save(update_fields=['attachment'])

    @patch('core.course_pdf_checks.requests.get')
    def test_no_attachment_alerts_with_canonical_course_id_without_blocking_release(self, get):
        stats = run_daily_programs(self.day)
        self.assertEqual(stats['courses'], 1); self.assertEqual(stats['failed'], 0)
        self.assertEqual(stats['pdf_checked'], 1)
        self.assertEqual(stats['pdf_missing'][0]['course_id'], self.course.pk)
        self.assertEqual(stats['pdf_missing'][0]['course'], 'Firewall ve Segmentasyon')
        self.assertTrue(self.user.allowed_tests.filter(pk=self.course.pk).exists())
        self.assertEqual(ProgramRelease.objects.get(enrollment=self.enrollment, step=self.step).status, 'sent')
        report = format_daily_program_summary(stats, self.day)
        self.assertIn(f'🚨 Course ID: {self.course.pk} — Firewall ve Segmentasyon — Bu derste PDF yok.', report)
        self.assertLess(report.index('PDF EKSİĞİ'), report.index('Açılan içerik detayları'))
        get.assert_not_called()

    @patch('core.course_pdf_checks.requests.get')
    def test_real_pdf_prefix_is_present_even_without_pdf_extension(self, get):
        self.attach('course_attachments/lesson-download')
        get.return_value = self.response()
        result = inspect_course_pdf(self.course)
        self.assertEqual(result['status'], 'present')
        self.assertEqual(get.call_args.args[0], 'https://www.grcustasi.com/media/course_attachments/lesson-download')
        self.assertTrue(get.call_args.kwargs['stream'])
        self.assertEqual(get.call_args.kwargs['headers']['Range'], 'bytes=0-1023')

    @patch('core.course_pdf_checks.requests.get')
    def test_pdf_filename_without_pdf_bytes_is_missing(self, get):
        self.attach(); get.return_value = self.response(data=b'PK\x03\x04 ZIP file', content_type='application/zip')
        result = inspect_course_pdf(self.course)
        self.assertEqual(result['status'], 'missing')
        self.assertIn('PDF formatında değil', result['reason'])

    @patch('core.course_pdf_checks.requests.get')
    def test_missing_file_and_transient_errors_are_distinct(self, get):
        self.attach()
        for status in (404, 410):
            get.return_value = self.response(status=status)
            self.assertEqual(inspect_course_pdf(self.course)['status'], 'missing')
        for status in (301, 403, 500, 503):
            get.return_value = self.response(status=status)
            self.assertEqual(inspect_course_pdf(self.course)['status'], 'unverified')
        get.return_value = self.response(data=b'<html>login</html>', content_type='text/html')
        self.assertEqual(inspect_course_pdf(self.course)['status'], 'unverified')
        get.side_effect = requests.Timeout('private storage URL must not leak')
        result = inspect_course_pdf(self.course)
        self.assertEqual(result['status'], 'unverified'); self.assertNotIn('private', result['reason'])

    @patch('core.course_pdf_checks.requests.get')
    def test_reads_only_a_bounded_prefix_and_closes_response(self, get):
        self.attach(); response = self.response(data=b'%PDF-1.7' + b' ' * 1016)
        def chunks(**kwargs):
            yield b'%PDF-1.7' + b' ' * 1016
            raise AssertionError('Must not download the whole attachment')
        response.iter_content.side_effect = chunks; get.return_value = response
        self.assertEqual(inspect_course_pdf(self.course)['status'], 'present')
        response.__exit__.assert_called_once()

    @patch('core.course_pdf_checks.requests.get')
    def test_same_course_for_multiple_students_is_checked_and_reported_once(self, get):
        self.attach(); get.return_value = self.response()
        other = get_user_model().objects.create_user(username='pdf-second', email='second@example.test')
        ProgramEnrollment.objects.create(user=other, program=self.program, start_date=self.day)
        stats = run_daily_programs(self.day)
        self.assertEqual(stats['courses'], 2); self.assertEqual(stats['pdf_checked'], 1)
        self.assertEqual(stats['pdf_missing'], []); get.assert_called_once()

    @patch('core.course_pdf_checks.requests.get')
    def test_same_day_rerun_rechecks_missing_pdf_but_does_not_reopen_or_remail(self, get):
        first = run_daily_programs(self.day); second = run_daily_programs(self.day)
        self.assertEqual((first['courses'], second['courses']), (1, 0))
        self.assertEqual(second['emails'], 0); self.assertEqual(second['pdf_checked'], 1)
        self.assertEqual(second['pdf_missing'][0]['course_id'], self.course.pk)
        self.attach(); get.return_value = self.response()
        fixed = run_daily_programs(self.day)
        self.assertEqual(fixed['pdf_missing'], []); self.assertEqual(fixed['courses'], 0)

    def test_yesterdays_email_retry_does_not_become_todays_pdf_alarm(self):
        self.enrollment.start_date = self.day - timedelta(days=1)
        self.enrollment.welcome_sent_at = timezone.now(); self.enrollment.save()
        yesterday = timezone.now() - timedelta(days=1)
        ProgramRelease.objects.create(enrollment=self.enrollment, step=self.step, access_granted_at=yesterday, status='failed')
        stats = run_daily_programs(self.day)
        self.assertEqual(stats['courses'], 0); self.assertEqual(stats['pdf_checked'], 0)

    def test_local_day_boundary_and_future_lessons(self):
        tz = ZoneInfo('Europe/Istanbul')
        start = datetime.combine(self.day, time.min, tzinfo=tz)
        release = ProgramRelease.objects.create(enrollment=self.enrollment, step=self.step,
                                                access_granted_at=start - timedelta(seconds=1), status='sent')
        with timezone.override(tz):
            self.assertEqual(check_released_course_pdfs(self.day)['pdf_checked'], 0)
            release.access_granted_at = start; release.save()
            self.assertEqual(check_released_course_pdfs(self.day)['pdf_checked'], 1)
            release.access_granted_at = start + timedelta(days=1); release.save()
            self.assertEqual(check_released_course_pdfs(self.day)['pdf_checked'], 0)

    @patch('core.course_pdf_checks.requests.get', side_effect=requests.Timeout())
    def test_transient_pdf_failure_never_stops_access_or_student_mail(self, get):
        self.attach(); stats = run_daily_programs(self.day)
        self.assertEqual(stats['failed'], 0); self.assertEqual(stats['emails'], 2)
        self.assertEqual(stats['pdf_missing'], []); self.assertEqual(len(stats['pdf_unverified']), 1)
        report = format_daily_program_summary(stats, self.day)
        self.assertIn('PDF KONTROLÜ DOĞRULANAMADI', report); self.assertNotIn('Bu derste PDF yok.', report)

    def test_scheduled_command_embeds_alarm_in_existing_telegram_summary(self):
        stats = run_daily_programs(self.day)
        with patch('core.management.commands.run_daily_programs.run_daily_programs', return_value=stats), \
             patch('core.management.commands.run_daily_programs.notify_telegram') as notify, \
             patch('core.management.commands.run_daily_programs.send_daily_report_email'), \
             patch('core.management.commands.run_daily_programs.send_daily_traffic_report'), \
             patch('core.management.commands.run_daily_programs.send_daily_meeting_digest'), \
             patch('core.management.commands.run_daily_programs.send_weekly_telegram_note'), \
             patch('core.student_monitoring.capture_snapshot', return_value=(MagicMock(reporting_date=self.day), True)):
            call_command('run_daily_programs', stdout=StringIO())
        notify.assert_called_once()
        self.assertIn('Günlük GRC Ustası programı', notify.call_args.args[0])
        self.assertIn(f'Course ID: {self.course.pk}', notify.call_args.args[0])
        self.assertIn('Bu derste PDF yok.', notify.call_args.args[0])
