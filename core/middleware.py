import requests

from django.conf import settings
from django.utils import timezone


class HiddenLoginAttemptTelegramMiddleware:
    """
    /bulamazsinki altındaki tüm POST denemelerini Telegram'a bildirir.
    Başarılı / başarısız fark etmez.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        path = request.path.rstrip("/")

        if request.method == "POST" and path.startswith("/bulamazsinki"):

            ip = self.get_client_ip(request)

            username = (
                request.POST.get("username")
                or request.POST.get("email")
                or "-"
            )

            # Güvenlik için şifreyi düz metin göndermiyoruz
            password_entered = "YES" if request.POST.get("password") else "NO"

            user_agent = request.META.get("HTTP_USER_AGENT", "-")
            referer = request.META.get("HTTP_REFERER", "-")
            full_path = request.get_full_path()

            now = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")

            message = (
                "🚨 ADMIN LOGIN ATTEMPT\n\n"
                f"🌍 IP: {ip}\n"
                f"👤 Username: {username}\n"
                f"🔑 Password entered: {password_entered}\n"
                f"🕒 Time: {now}\n"
                f"📄 Path: {full_path}\n"
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

        real_ip = request.META.get("HTTP_X_REAL_IP")
        if real_ip:
            return real_ip.strip()

        return request.META.get("REMOTE_ADDR", "-")

    @staticmethod
    def send_telegram(message):
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")

        if not token or not chat_id:
            print("TELEGRAM ERROR: TOKEN or CHAT_ID missing")
            return

        try:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": message,
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )

            if response.status_code != 200:
                print("TELEGRAM ERROR:", response.status_code, response.text)

        except Exception as e:
            print("TELEGRAM EXCEPTION:", e)
