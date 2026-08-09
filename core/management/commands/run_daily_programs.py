from django.core.management.base import BaseCommand
from django.utils import timezone

from core.program_automation import notify_telegram, run_daily_programs


class Command(BaseCommand):
    help = "Vadesi gelen program içeriklerini açar, mail ve Telegram özeti gönderir."

    def handle(self, *args, **options):
        run_date = timezone.localdate()
        stats = run_daily_programs(run_date)
        status = "✅ Başarılı" if not stats["failed"] else "⚠️ Kısmi hata"
        summary = (
            f"{status} — Günlük Siberkobi programı\n"
            f"📅 {run_date:%d.%m.%Y}\n"
            f"👥 İşlenen öğrenci: {stats['students']}\n"
            f"📚 Açılan içerik: {stats['courses']}\n"
            f"✉️ Gönderilen mail: {stats['emails']}\n"
            f"❌ Hata: {stats['failed']}"
        )
        self.stdout.write(summary)
        notify_telegram(summary)
        if stats["failed"]:
            raise RuntimeError(f"{stats['failed']} öğrenci için mail gönderilemedi")
