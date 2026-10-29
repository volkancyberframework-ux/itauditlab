"""Inspect today's released course PDFs from the same storage URL learners use.

The scheduled worker has no web-service media disk, so a local exists() check
would incorrectly report every upload missing. Read only a bounded file prefix.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.utils import timezone

from .models import Course, ProgramRelease


def inspect_course_pdf(course):
    result = {'course_id': course.pk, 'course': str(course)}
    if not course.attachment:
        return {**result, 'status': 'missing', 'reason': 'Derse ek dosya yüklenmemiş.'}
    try:
        url = urljoin(settings.PUBLIC_BASE_URL.rstrip('/') + '/', course.attachment.url)
        with requests.get(url, headers={'Range': 'bytes=0-1023', 'Accept-Encoding': 'identity'},
                          stream=True, timeout=(3, 5), allow_redirects=False) as response:
            if response.status_code in (404, 410):
                return {**result, 'status': 'missing', 'reason': 'Ek dosyasına ulaşılamıyor; dosya bulunamadı.'}
            if response.status_code not in (200, 206):
                return {**result, 'status': 'unverified', 'reason': f'Dosya erişimi doğrulanamadı (HTTP {response.status_code}).'}
            prefix = b''
            for chunk in response.iter_content(chunk_size=1024):
                prefix += chunk[:1024-len(prefix)]
                if len(prefix) >= 1024:
                    break
            if prefix.lstrip(b'\xef\xbb\xbf \t\r\n').startswith(b'%PDF-'):
                return {**result, 'status': 'present', 'reason': ''}
            if 'text/html' in response.headers.get('Content-Type', '').lower():
                return {**result, 'status': 'unverified', 'reason': 'Dosya yerine web sayfası döndü; erişim kontrol edilmeli.'}
            return {**result, 'status': 'missing', 'reason': 'Ek dosyası PDF formatında değil.'}
    except Exception:
        # Never disclose storage URLs/tokens or interrupt course access/mail.
        return {**result, 'status': 'unverified', 'reason': 'Dosyaya erişim veya PDF kontrolü geçici olarak doğrulanamadı.'}


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
    if not courses:
        return {'pdf_checked': 0, 'pdf_missing': [], 'pdf_unverified': []}
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(inspect_course_pdf, courses))
    return {
        'pdf_checked': len(results),
        'pdf_missing': [row for row in results if row['status'] == 'missing'],
        'pdf_unverified': [row for row in results if row['status'] == 'unverified'],
    }
