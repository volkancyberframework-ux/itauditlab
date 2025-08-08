import base64
import hashlib
import hmac
import time
from django.conf import settings

def generate_bunny_token(path: str, expiry_seconds=3600):
    expires = int(time.time()) + expiry_seconds
    raw = f"{path}{expires}".encode("utf-8")
    digest = hmac.new(settings.BUNNY_SECURITY_KEY.encode("utf-8"), raw, hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return f"{settings.BUNNY_STREAM_BASE}{path}?token={token}&expires={expires}"
