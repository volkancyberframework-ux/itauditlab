"""Student's personal program calendar; reading it never grants course access."""
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.db.models import Prefetch
from django.utils import timezone

from .models import Course, Enrollment, LearningProgramStep, ProgramEnrollment


def student_program_calendar(user, today=None):
    today = today or timezone.now().astimezone(ZoneInfo('Europe/Istanbul')).date()
    enrollments = list(ProgramEnrollment.objects.filter(user=user).select_related('program').prefetch_related(
        Prefetch('program__steps', queryset=LearningProgramStep.objects.select_related('course')),
        'releases',
    ))
    if not enrollments:
        return []
    enrolled_ids = set(Enrollment.objects.filter(user=user).values_list('course_id', flat=True))
    test_ids = set(user.allowed_tests.values_list('id', flat=True))
    calendars = []
    for enrollment in enrollments:
        active = enrollment.is_active and enrollment.program.is_active
        releases = {release.step_id: release for release in enrollment.releases.all()}
        lessons = []
        for step in enrollment.program.steps.all():
            release_date = enrollment.start_date + timedelta(days=step.day_offset)
            release = releases.get(step.pk)
            opened = step.course_id in (test_ids if step.course.course_type == Course.CourseType.TEST else enrolled_ids)
            if opened:
                status = '✅ Açıldı'
            elif not active:
                status = '⏸️ Duraklatıldı'
            elif release_date <= today:
                status = '⏳ Açılması bekleniyor'
            else:
                status = '🔒 Açılacak'
            lessons.append({
                'title': step.course.turkish_name or step.course.english_name,
                'course_id': step.course_id,
                'date': release_date,
                'opened_at': release.access_granted_at if release else None,
                'opened': opened,
                'status': status,
            })
        opened_count = sum(lesson['opened'] for lesson in lessons)
        calendars.append({
            'name': enrollment.program.name,
            'start_date': enrollment.start_date,
            'active': active,
            'lessons': lessons,
            'opened_count': opened_count,
            'total': len(lessons),
            'percent': round(opened_count * 100 / len(lessons)) if lessons else 0,
        })
    return calendars
