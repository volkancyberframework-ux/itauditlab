"""Source health checks report changes; they never approve or rewrite legal copy."""
import hashlib
import ipaddress
import socket
from urllib.parse import urlsplit, urljoin
import requests
from .legal_registry import DATA

OFFICIAL_HOSTS = frozenset(urlsplit(row['official_source_url']).hostname for row in DATA)

def validate_source_url(url):
    from django.core.exceptions import ValidationError
    parts=urlsplit(url)
    if parts.scheme != 'https' or parts.hostname not in OFFICIAL_HOSTS or parts.username or parts.password or parts.port not in (None,443):
        raise ValidationError('Yalnızca kayıtlı resmî kaynak alan adları ve HTTPS kullanılabilir.')

def fingerprint(url):
    validate_source_url(url)
    session=requests.Session()
    session.trust_env=False
    session.headers['User-Agent']='GRCUstasi-SourceReview/1.0 (+https://www.grcustasi.com/mevzuat/)'
    for _ in range(4):
        validate_source_url(url)
        addresses=socket.getaddrinfo(urlsplit(url).hostname,443,type=socket.SOCK_STREAM)
        if any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
            raise ValueError('Non-public source address')
        with session.get(url,timeout=(5,15),allow_redirects=False,stream=True) as response:
            if response.status_code in (301,302,303,307,308):
                url=urljoin(url,response.headers['Location']);continue
            response.raise_for_status()
            digest=hashlib.sha256();size=0
            for chunk in response.iter_content(65536):
                size+=len(chunk)
                if size>8_000_000:raise ValueError('Source exceeds 8 MB')
                digest.update(chunk)
            return digest.hexdigest()
    raise ValueError('Too many redirects')
