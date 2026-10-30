"""Check whether released lessons have an attachment field populated.

Legacy PDF function/stat names are retained for the existing daily report callers.
File type, remote availability and file contents are deliberately not inspected.
"""
from datetime import datetime, time, timedelta

from django.utils import timezone

from .models import Course, ProgramRelease


def inspect_course_pdf(course):
    result = {'course_id': course.pk, 'course': str(course)}
    if not (course.attachment.name or '').strip():
        return {**result, 'status': 'missing', 'reason': 'Derse ek dosya yüklenmemiş.'}
    return {**result, 'status': 'present', 'reason': ''}


def check_released_course_pdfs(run_date, newly_opened_course_ids=()):
    """Include same-day reruns, not yesterday's email retries; check each course once."""
    start = datetime.combine(run_date, time.min, tzinfo=timezone.get_current_timezone())
    end = start + timedelta(days=1)
    course_ids = set(newly_opened_course_ids)
    course_ids.update(ProgramRelease.objects.filter(
        access_granted_at__gte=start, access_granted_at__lt=end,
    ).values_list('step__course_id', flat=True))
    courses = list(Course.objects.filter(pk__in=course_ids).only(
        'id', 'turkish_name', 'english_name', 'attachment',
    ).order_by('pk'))
    results = [inspect_course_pdf(course) for course in courses]
    return {
        'pdf_checked': len(results),
        'pdf_missing': [row for row in results if row['status'] == 'missing'],
        'pdf_unverified': [row for row in results if row['status'] == 'unverified'],
    }
