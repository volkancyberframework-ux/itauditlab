from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import (
    Course,
    LearningProgram,
    LearningProgramStep,
    ProgramEnrollment,
    ProgramRelease,
)
from .program_automation import run_daily_programs


class DailyProgramAutomationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="student@example.com", email="student@example.com", password="test"
        )
        self.course = Course.objects.create(
            turkish_name="Test kursu",
            duration=timedelta(hours=1),
            difficulty="Beginner",
            description="Test",
            course_type=Course.CourseType.TEST,
        )
        self.program = LearningProgram.objects.create(slug="test", name="Test Programı")
        self.step = LearningProgramStep.objects.create(
            program=self.program, course=self.course, day_offset=3
        )
        self.enrollment = ProgramEnrollment.objects.create(
            user=self.user, program=self.program, start_date=date(2026, 8, 1)
        )

    @patch("core.program_automation.send_release_email")
    @patch("core.program_automation.send_welcome")
    def test_due_step_is_granted_and_mailed_once(self, welcome, release_mail):
        first = run_daily_programs(date(2026, 8, 4))
        second = run_daily_programs(date(2026, 8, 4))

        self.assertEqual(first["courses"], 1)
        self.assertEqual(second["courses"], 0)
        self.assertTrue(self.user.allowed_tests.filter(pk=self.course.pk).exists())
        self.assertEqual(ProgramRelease.objects.count(), 1)
        self.assertEqual(ProgramRelease.objects.get().status, ProgramRelease.Status.SENT)
        welcome.assert_called_once()
        release_mail.assert_called_once()

    @patch("core.program_automation.send_release_email", side_effect=RuntimeError("SMTP down"))
    @patch("core.program_automation.send_welcome")
    def test_failed_mail_is_retried_without_regranting(self, welcome, release_mail):
        first = run_daily_programs(date(2026, 8, 4))
        second = run_daily_programs(date(2026, 8, 5))

        self.assertEqual(first["courses"], 1)
        self.assertEqual(second["courses"], 0)
        self.assertEqual(release_mail.call_count, 2)
        self.assertEqual(ProgramRelease.objects.get().status, ProgramRelease.Status.FAILED)
