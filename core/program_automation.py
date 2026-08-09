import html
import logging

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import Course, ProgramEnrollment, ProgramRelease

logger = logging.getLogger(__name__)


def _display_name(user):
    return user.first_name.strip() or user.get_full_name().strip() or user.email.split("@", 1)[0]


def _email_shell(title, name, content):
    return f"""<!doctype html>
<html lang="tr"><body style="margin:0;background:#f3f6fb;font-family:Arial,sans-serif;color:#172033">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:32px 12px">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 8px 28px rgba(20,35,70,.10)">
<tr><td style="padding:28px 34px;background:#111d3b;color:#fff"><div style="font-size:13px;letter-spacing:1.5px;color:#7dd3fc">SİBERKOBİ</div><h1 style="font-size:25px;margin:8px 0 0">{html.escape(title)}</h1></td></tr>
<tr><td style="padding:32px 34px"><p style="font-size:17px;margin-top:0">Merhaba {html.escape(name)},</p>{content}
<p style="margin:28px 0 0">İyi çalışmalar,<br><strong>Volkan Güler</strong><br>Siberkobi</p></td></tr>
<tr><td style="padding:18px 34px;background:#f8fafc;color:#64748b;font-size:12px">Bu e-posta eğitim programındaki ilerleme planına göre otomatik gönderildi.</td></tr>
</table></td></tr></table></body></html>"""


def send_welcome(enrollment):
    steps = enrollment.program.steps.select_related("course").all()
    rows = "".join(
        f'<tr><td style="padding:8px;border-bottom:1px solid #e5e7eb">Gün {step.day_offset}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #e5e7eb">{html.escape(step.email_title or str(step.course))}</td></tr>'
        for step in steps
    )
    content = (
        f"<p><strong>{html.escape(enrollment.program.name)}</strong> programın başladı. "
        "İçeriklerin aşağıdaki kişisel takvimine göre otomatik açılacak.</p>"
        f'<table width="100%" cellspacing="0" style="border-collapse:collapse;margin:22px 0">{rows}</table>'
        '<p><a href="https://siberkobi.co/dashboard-student/" style="display:inline-block;background:#2563eb;color:#fff;text-decoration:none;padding:12px 20px;border-radius:8px">Eğitim paneline git</a></p>'
    )
    subject = f"{enrollment.program.name} eğitim takvimin"
    _send_email(enrollment.user.email, subject, _email_shell(subject, _display_name(enrollment.user), content))


def send_release_email(enrollment, releases):
    items = "".join(
        f'<li style="margin:9px 0">{html.escape(r.step.email_title or str(r.step.course))}</li>'
        for r in releases
    )
    content = (
        "<p>Programındaki yeni içerikler hesabına tanımlandı ve erişime açıldı.</p>"
        f'<ul style="padding-left:22px;margin:22px 0">{items}</ul>'
        "<p>İçerikleri dikkatlice incelemeni, ekleri kontrol etmeni, notlarını çıkarmanı ve gerçek bir denetçi gibi kanıt–risk–öneri ilişkisi kurmanı bekliyorum.</p>"
        '<p><a href="https://siberkobi.co/dashboard-student/" style="display:inline-block;background:#2563eb;color:#fff;text-decoration:none;padding:12px 20px;border-radius:8px">İçeriklere git</a></p>'
    )
    subject = "Yeni eğitim içeriklerin erişime açıldı"
    _send_email(enrollment.user.email, subject, _email_shell(subject, _display_name(enrollment.user), content))


def _send_email(recipient, subject, html_body):
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        raise RuntimeError("EMAIL_HOST_USER veya EMAIL_HOST_PASSWORD tanımlı değil")
    message = EmailMultiAlternatives(
        subject=subject,
        body="Yeni eğitim içerikleriniz açıldı. Detaylar için https://siberkobi.co adresini ziyaret edin.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)


def notify_telegram(text):
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.warning("Telegram bildirimi atlandı: ayarlar eksik")
        return
    response = requests.post(
        f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
        data={"chat_id": settings.TELEGRAM_CHAT_ID, "text": text},
        timeout=10,
    )
    response.raise_for_status()


def run_daily_programs(run_date=None):
    run_date = run_date or timezone.localdate()
    stats = {"students": 0, "courses": 0, "emails": 0, "failed": 0}
    enrollments = ProgramEnrollment.objects.filter(
        is_active=True, program__is_active=True, start_date__lte=run_date
    ).select_related("user", "program")

    for enrollment in enrollments:
        elapsed_days = (run_date - enrollment.start_date).days
        due_steps = enrollment.program.steps.filter(day_offset__lte=elapsed_days).select_related("course")
        releases = []

        for step in due_steps:
            release, _ = ProgramRelease.objects.get_or_create(enrollment=enrollment, step=step)
            if not release.access_granted_at:
                if step.course.course_type == Course.CourseType.TEST:
                    enrollment.user.allowed_tests.add(step.course)
                release.access_granted_at = timezone.now()
                release.status = ProgramRelease.Status.PENDING
                release.save(update_fields=("access_granted_at", "status"))
                stats["courses"] += 1
            if release.status != ProgramRelease.Status.SENT:
                releases.append(release)

        if not releases and enrollment.welcome_sent_at:
            continue

        stats["students"] += 1
        try:
            if not enrollment.welcome_sent_at:
                send_welcome(enrollment)
                enrollment.welcome_sent_at = timezone.now()
                enrollment.save(update_fields=("welcome_sent_at",))
                stats["emails"] += 1
            if releases:
                send_release_email(enrollment, releases)
                now = timezone.now()
                ProgramRelease.objects.filter(pk__in=[r.pk for r in releases]).update(
                    status=ProgramRelease.Status.SENT, email_sent_at=now, error_message=""
                )
                stats["emails"] += 1
        except Exception as exc:
            logger.exception("Program mail failed for %s", enrollment.user.email)
            ProgramRelease.objects.filter(pk__in=[r.pk for r in releases]).update(
                status=ProgramRelease.Status.FAILED, error_message=str(exc)[:2000]
            )
            stats["failed"] += 1

    return stats
