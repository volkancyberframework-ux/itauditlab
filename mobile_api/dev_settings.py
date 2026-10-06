"""Isolated LAN backend for device testing. Never deploy this settings module."""

import os
import secrets
from pathlib import Path

_demo_root = Path(os.environ.get("GRC_DEMO_ROOT", "/tmp/grc-ustasi-device-demo"))
_demo_root.mkdir(parents=True, exist_ok=True)
_secret_file = _demo_root / "secret.key"
if not _secret_file.exists():
    _secret_file.write_text(secrets.token_urlsafe(48))
    _secret_file.chmod(0o600)
# Override production environment settings before importing the shared project.
os.environ["SECRET_KEY"] = _secret_file.read_text().strip()
os.environ["DATABASE_URL"] = f'sqlite:///{_demo_root / "db.sqlite3"}'
os.environ["DEBUG"] = "False"
from itaudit.settings import *

DEBUG = False
DATABASES = {
    "default": {
        "ENGINE": "mobile_api.sqlite_backend",
        "NAME": str(_demo_root / "db.sqlite3"),
        "OPTIONS": {"timeout": 20},
    }
}
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    os.environ.get("GRC_DEMO_HOST", "192.168.100.58"),
]
ROOT_URLCONF = "mobile_api.dev_urls"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
MOBILE_VOICE_ROOT = str(_demo_root / "private_media")
REVENUECAT_SECRET_KEY = ""
REVENUECAT_WEBHOOK_TOKEN = ""
TELEGRAM_BOT_TOKEN = ""
GRCUSTASI_TELEGRAM_BOT_TOKEN = ""
MIDDLEWARE = [
    m
    for m in MIDDLEWARE
    if m
    not in [
        "core.middleware.HiddenLoginAttemptTelegramMiddleware",
        "landing.middleware.LandingTrafficMiddleware",
    ]
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        }
    },
}
