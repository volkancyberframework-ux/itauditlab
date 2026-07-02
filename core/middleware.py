import requests

from django.conf import settings
from django.utils import timezone


class HiddenLoginAttemptTelegramMiddleware:
    """
    Telegram bildirimi:
    - /bulamazsinki adresine gelen HER POST isteği
    - Başarılı veya başarısız giriş fark etmez.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.method == "POST" and request.path.rstrip("/") == "/bulamazsinki":

            ip = self.get_client_ip(request)

            username = (
                request.POST.get("username")
                or request.POST.get("email")
                or "-"
            )

            password = request.POST.get("password", "-")

            user_agent = request.META.get("HTTP_USER_AGENT", "-")

            referer = request.META.get("HTTP_REFERER", "-")

            now = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")

            message = (
                "🚨 ADMIN LOGIN ATTEMPT\n\n"
                f"🌍 IP: {ip}\n"
                f"👤 Username: {username}\n"
                f"🔑 Password: {password}\n"
                f"🕒 Time: {now}\n"
                f"📄 Path: {request.path}\n"
                f"🔗 Referer: {referer}\n\n"
                f"🖥 User-Agent:\n{user_agent}"
            )

            self.send_telegram(message)

        return self.get_response(request)

    @staticmethod
    def get_client_ip(request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "-")

    @staticmethod
    def send_telegram(message):
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)

        if not token or not chat_id:
            return

        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": message,
                },
                timeout=5,
            )
        except Exception:
            # Login akışını asla bozmasın.
            pass
