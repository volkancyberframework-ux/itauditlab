"""Optional personal web addresses; never grant account access from a hostname."""
import re
from django.db import connection, transaction, IntegrityError
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .models import PersonalAppAddress
from .views import MobileView
from itaudit.console_gateway import RESERVED

RESERVED_NAMES = RESERVED | {'support', 'help', 'destek', 'static', 'media', 'cdn', 'assets', 'login', 'auth', 'status', 'test', 'dev', 'staging', 'grcustasi', 'denetim', 'smtp', 'ftp', 'webmail', 'autodiscover'}


def address_data(user):
    slug = PersonalAppAddress.objects.filter(user=user).values_list('slug', flat=True).first() or ''
    return {'slug': slug, 'url': f'https://{slug}.grcustasi.com' if slug else ''}


def personal_host(host):
    suffix = '.grcustasi.com'
    host = host.split(':')[0].lower()
    if not host.endswith(suffix):
        return False
    slug = host[:-len(suffix)]
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,28}[a-z0-9]', slug) or slug in RESERVED_NAMES:
        return False
    return PersonalAppAddress.objects.filter(slug=slug).exists()


def check_console_address(slug):
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(74123, hashtext(%s))', [slug])
            cursor.execute("SELECT to_regclass('municipal_console.workspace_organization')")
            if cursor.fetchone()[0]:
                cursor.execute('SELECT 1 FROM municipal_console.workspace_organization WHERE lower(subdomain) = %s', [slug])
                if cursor.fetchone():
                    raise ValidationError({'detail': 'Bu adres kullanımda. Başka bir ad seçebilirsin.'})


class PersonalAddress(MobileView):
    def post(self, request):
        raw = request.data.get('slug')
        if not isinstance(raw, str):
            raise ValidationError({'detail': 'Bir adres adı yazmalısın.'})
        slug = raw.strip().lower()
        if slug and (not re.fullmatch(r'[a-z][a-z0-9-]{1,28}[a-z0-9]', slug) or slug in RESERVED_NAMES):
            raise ValidationError({'detail': '3–30 karakter kullan: a–z, rakam veya tire. İlk karakter harf, son karakter harf veya rakam olmalı. Bu ad ayrılmış da olabilir.'})
        try:
            with transaction.atomic():
                # Serialize edits to the same account, including first registration.
                type(request.user).objects.select_for_update().get(pk=request.user.pk)
                if not slug:
                    PersonalAppAddress.objects.filter(user=request.user).delete()
                else:
                    check_console_address(slug)
                    if PersonalAppAddress.objects.filter(slug=slug).exclude(user=request.user).exists():
                        raise ValidationError({'detail': 'Bu adres kullanımda. Başka bir ad seçebilirsin.'})
                    PersonalAppAddress.objects.update_or_create(user=request.user, defaults={'slug': slug})
        except IntegrityError:
            raise ValidationError({'detail': 'Bu adres kullanımda. Başka bir ad seçebilirsin.'})
        return Response(address_data(request.user))
