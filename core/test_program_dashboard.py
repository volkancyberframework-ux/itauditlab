from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Course, Enrollment, LearningProgram, LearningProgramStep, ProgramEnrollment, ProgramRelease
from .program_dashboard import student_program_calendar


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class ProgramDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='calendar', password='test', is_first_login=False)
        self.program = LearningProgram.objects.create(name='Denetçi Programı', slug='calendar')
        self.enrollment = ProgramEnrollment.objects.create(user=self.user, program=self.program, start_date=date(2026, 10, 20))
        self.steps = []
        for index in range(3):
            course = Course.objects.create(turkish_name=f'Ders {index}', duration=timedelta(hours=1), course_type=Course.CourseType.TEST)
            self.steps.append(LearningProgramStep.objects.create(program=self.program, course=course, day_offset=index * 7))

    def test_actual_access_and_planned_dates(self):
        self.user.allowed_tests.add(self.steps[0].course)
        ProgramRelease.objects.create(enrollment=self.enrollment, step=self.steps[0], access_granted_at=timezone.now(), status=ProgramRelease.Status.FAILED)
        calendar = student_program_calendar(self.user, date(2026, 10, 28))[0]
        self.assertEqual([lesson['status'] for lesson in calendar['lessons']], ['✅ Açıldı', '⏳ Açılması bekleniyor', '🔒 Açılacak'])
        self.assertEqual(calendar['lessons'][2]['date'], date(2026, 11, 3))
        self.assertEqual(calendar['opened_count'], 1)
        self.assertEqual(calendar['percent'], 33)

    def test_paused_and_empty_programs(self):
        self.enrollment.is_active = False
        self.enrollment.save()
        self.assertEqual(student_program_calendar(self.user)[0]['lessons'][0]['status'], '⏸️ Duraklatıldı')
        LearningProgramStep.objects.all().delete()
        calendar = student_program_calendar(self.user)[0]
        self.assertEqual(calendar['total'], 0)
        self.assertEqual(calendar['percent'], 0)

    def test_video_enrollment_is_open(self):
        course = self.steps[0].course
        course.course_type = Course.CourseType.VIDEO
        course.save()
        Enrollment.objects.create(user=self.user, course=course)
        self.assertTrue(student_program_calendar(self.user)[0]['lessons'][0]['opened'])

    def test_dashboard_popup_and_user_isolation(self):
        other = get_user_model().objects.create_user(username='other')
        secret = LearningProgram.objects.create(name='Başkasının gizli programı', slug='secret')
        ProgramEnrollment.objects.create(user=other, program=secret, start_date=date(2026, 1, 1))
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard_student'))
        self.assertContains(response, 'Programlarım ve Ders Takvimim')
        self.assertContains(response, 'Denetçi Programı')
        self.assertContains(response, '03.11.2026')
        self.assertContains(response, 'Salı')
        self.assertNotContains(response, 'Başkasının gizli programı')
        self.assertEqual(len(response.context['program_calendars']), 1)

    def test_no_program_no_button_and_login_required(self):
        self.enrollment.delete()
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard_student'))
        self.assertNotContains(response, 'id="programCalendarModal"')
        self.client.logout()
        self.assertEqual(self.client.get(reverse('dashboard_student')).status_code, 302)
