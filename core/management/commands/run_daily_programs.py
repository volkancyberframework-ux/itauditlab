from django.core.management.base import BaseCommand
from django.utils import timezone

from core.program_automation import (
    notify_telegram,
    run_daily_programs,
    send_daily_report_email,
)
from landing.traffic import send_daily_traffic_report
from skool.digest import send_daily_meeting_digest


class Command(BaseCommand):
    help = "Vadesi gelen program içeriklerini açar, mail ve Telegram özeti gönderir."

    def handle(self, *args, **options):
        run_date = timezone.localdate()
        stats = run_daily_programs(run_date)
        status = "✅ Başarılı" if not stats["failed"] else "⚠️ Kısmi hata"
        summary = (
            f"{status} — Günlük GRC Ustası programı\n"
            f"📅 {run_date:%d.%m.%Y}\n"
            f"👥 İşlenen öğrenci: {stats['students']}\n"
            f"📚 Açılan içerik: {stats['courses']}\n"
            f"✉️ Gönderilen mail: {stats['emails']}\n"
            f"❌ Hata: {stats['failed']}"
        )
        if stats["details"]:
            detail_lines = ["", "📋 Açılan içerik detayları"]
            for item in stats["details"]:
                mail_icon = "✅" if item["mail"] == "gönderildi" else "❌"
                detail_lines.extend([
                    "",
                    f"👤 {item['email']}",
                    f"📚 {item['course']}",
                    f"{mail_icon} Mail: {item['mail']}",
                ])
            summary += "\n" + "\n".join(detail_lines)
        else:
            summary += "\n\nBugün açılacak yeni içerik bulunmuyor."
        self.stdout.write(summary)
        notify_telegram(summary)
        send_daily_report_email(summary, run_date)
        try:
            sent = send_daily_traffic_report(run_date - timezone.timedelta(days=1))
            self.stdout.write('Günlük trafik raporu gönderildi.' if sent else 'Günlük trafik raporu zaten gönderilmiş.')
        except Exception as exc:
            # Eğitim erişim otomasyonunu trafik raporundaki geçici bir sorun yüzünden durdurma.
            self.stderr.write(self.style.WARNING(f'Trafik raporu gönderilemedi: {exc}'))
        try:
            sent = send_daily_meeting_digest(run_date)
            self.stdout.write('Günlük görüşme özeti gönderildi.' if sent else 'Günlük görüşme özeti zaten gönderilmiş.')
        except Exception as exc:
            # Eğitim erişim otomasyonunu Telegram'daki geçici bir sorun yüzünden durdurma.
            self.stderr.write(self.style.WARNING(f'Görüşme özeti gönderilemedi: {exc}'))
        if stats["failed"]:
            raise RuntimeError(f"{stats['failed']} öğrenci için mail gönderilemedi")
