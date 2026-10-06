import re
from django.core.exceptions import ValidationError


def whatsapp_number(value):
    if not value or not value.strip():
        return ''
    value = value.strip()
    if not re.fullmatch(r'\+?[0-9 ()-]+', value):
        raise ValidationError('Telefon numarasını ülke koduyla yazın. Örnek: +32 476 073 171.')
    digits = re.sub(r'[^0-9]', '', value)
    if digits.startswith('00'):
        digits = digits[2:]
    if not re.fullmatch(r'[1-9][0-9]{7,14}', digits):
        raise ValidationError('Telefon numarasını ülke koduyla yazın. Örnek: +32 476 073 171.')
    return digits


def validate_whatsapp_number(value):
    whatsapp_number(value)


def contact_data():
    from .models import MobileSettings
    settings = MobileSettings.objects.filter(pk=1).first()
    try:
        phone = whatsapp_number(settings.whatsapp_phone) if settings else ''
    except ValidationError:
        phone = ''
    return {'name': 'Volkan', 'phone': phone, 'whatsapp_url': f'https://wa.me/{phone}' if phone else None}
