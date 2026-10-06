import os

os.environ.setdefault("SECRET_KEY", "mobile-tests-only-key-with-sufficient-length")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/grc-mobile-tests.sqlite3")
from itaudit.settings import *

ALLOWED_HOSTS = ["testserver", "localhost"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
MOBILE_VOICE_ROOT = "/tmp/grc-mobile-private-tests"

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
