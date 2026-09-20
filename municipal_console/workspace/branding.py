from django.templatetags.static import static
from django.urls import reverse
from django.conf import settings
from io import BytesIO
from pathlib import Path

def organization_brand(organization=None):
    if organization and organization.logo_data:
        logo=reverse('organization_logo',args=[organization.pk])
    elif organization and organization.slug=='torbali-belediyesi':
        logo=static('img/torbali-belediyesi.gif')
    else:logo=static('img/organization.svg')
    return {'brand_name':organization.name if organization else 'Denetim Konsolu','brand_logo_url':logo,'brand_domain':f'{organization.subdomain}.{settings.TENANT_BASE_DOMAIN}' if organization and organization.subdomain else '', 'tenant_base_domain':settings.TENANT_BASE_DOMAIN}

def pdf_logo(organization):
    if organization.logo_data:return BytesIO(bytes(organization.logo_data))
    if organization.slug=='torbali-belediyesi':return str(settings.BASE_DIR/'static/img/torbali-belediyesi.gif')
    return None

def brand_context(request):
    return organization_brand(getattr(request,'tenant',None))

def it_label(audit):
    names=[m.user.get_full_name() or m.user.email for m in audit.membership_set.filter(role='it',user__is_active=True).select_related('user').order_by('user__first_name','user__pk')]
    return 'BT Sorumlusu'+(' ('+', '.join(names)+')' if names else ' (atanmadı)')
