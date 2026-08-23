import requests

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "GRC Ustası Telegram botunun webhook adresini kurar ve doğrular."

    def handle(self, *args, **options):
        token = getattr(settings, "GRCUSTASI_TELEGRAM_BOT_TOKEN", "")
        secret = getattr(settings, "GRCUSTASI_TELEGRAM_WEBHOOK_SECRET", "")
        base = getattr(settings, "PUBLIC_BASE_URL", "https://www.grcustasi.com").rstrip("/")
        if not token:
            raise CommandError("GRCUSTASI_TELEGRAM_BOT_TOKEN tanımlı değil.")
        if not secret:
            raise CommandError("GRCUSTASI_TELEGRAM_WEBHOOK_SECRET tanımlı değil.")

        endpoint = f"https://api.telegram.org/bot{token}"
        webhook_url = f"{base}/api/skool/telegram/"
        response = requests.post(
            f"{endpoint}/setWebhook",
            data={"url": webhook_url, "secret_token": secret, "allowed_updates": '["message"]'},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise CommandError(payload.get("description", "Telegram webhook kurulamadı."))

        info_response = requests.get(f"{endpoint}/getWebhookInfo", timeout=15)
        info_response.raise_for_status()
        info = info_response.json().get("result", {})
        if info.get("url") != webhook_url:
            raise CommandError("Telegram farklı bir webhook adresi döndürdü.")
        self.stdout.write(self.style.SUCCESS(f"Webhook hazır: {webhook_url}"))
        if info.get("last_error_message"):
            self.stdout.write(self.style.WARNING(f"Son Telegram hatası: {info['last_error_message']}"))
