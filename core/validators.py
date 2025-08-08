# core/validators.py
from urllib.parse import urlparse
from django.core.exceptions import ValidationError

YOUTUBE_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "youtu.be", "www.youtu.be",
    "youtube-nocookie.com", "www.youtube-nocookie.com",
}

def validate_youtube_url(value):
    try:
        host = (urlparse(value).hostname or "").lower()
    except Exception:
        raise ValidationError("Invalid URL.")
    if host not in YOUTUBE_HOSTS:
        raise ValidationError("Only YouTube URLs are allowed.")
