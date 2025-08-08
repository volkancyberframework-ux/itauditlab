# core/templatetags/video_extras.py
import re
from urllib.parse import urlparse, parse_qs
from django import template

register = template.Library()

_YT_HOSTS = {"www.youtube.com","youtube.com","youtu.be","m.youtube.com","youtube-nocookie.com","www.youtube-nocookie.com"}
_PATTERNS = [re.compile(r"(?:v=|/embed/|/shorts/|youtu\.be/)([A-Za-z0-9_-]{6,})")]

def _start_seconds(q):
    if "start" in q:
        try: return int(q["start"][0])
        except: pass
    if "t" in q:
        t = q["t"][0]
        if t.isdigit(): return int(t)
        m = re.match(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$", t)
        if m:
            h,mn,s = m.groups()
            return (int(h or 0)*3600)+(int(mn or 0)*60)+int(s or 0)
    return 0

def _extract_id_and_start(url):
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if host not in _YT_HOSTS:
        return None, 0
    q = parse_qs(p.query or "")
    start = _start_seconds(q)
    if "v" in q and q["v"]:
        vid = q["v"][0]
        if re.match(r"^[A-Za-z0-9_-]{6,}$", vid): return vid, start
    for pat in _PATTERNS:
        m = pat.search(url)
        if m: return m.group(1), start
    return None, start

@register.filter
def youtube_embed(url: str):
    if not url: return ""
    vid, start = _extract_id_and_start(url)
    if not vid: return ""
    base = f"https://www.youtube-nocookie.com/embed/{vid}"
    return f"{base}?start={start}" if start else base
