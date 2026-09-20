from django.templatetags.static import static
from django.urls import reverse
from django.conf import settings
from io import BytesIO
from pathlib import Path

def organization_brand(organization=None):
    if organization and organization.logo_data:
        from hashlib import sha256
        logo=reverse('organization_logo',args=[organization.pk])+'?v='+sha256(bytes(organization.logo_data)).hexdigest()[:12]
    elif organization and organization.slug=='torbali-belediyesi':
        logo=static('img/torbali-belediyesi.gif')
    else:logo=static('img/organization.svg')
    return {'brand_name':organization.name if organization else 'Denetim Konsolu','brand_logo_url':logo,'brand_domain':f'{organization.subdomain}.{settings.TENANT_BASE_DOMAIN}' if organization and organization.subdomain else '', 'tenant_base_domain':settings.TENANT_BASE_DOMAIN}

def pdf_logo(organization):
    if organization.logo_data:return BytesIO(bytes(organization.logo_data))
    if organization.slug=='torbali-belediyesi':return str(settings.BASE_DIR/'static/img/torbali-belediyesi.gif')
    return None

def brand_context(request):
    organization=getattr(request,'tenant',None)
    if not organization and getattr(request,'user',None) and request.user.is_authenticated:
        from .models import Audit
        audits=Audit.objects.filter(archived=False).select_related('organization')
        if not request.user.is_superuser:audits=audits.filter(membership__user=request.user)
        audit=audits.filter(pk=request.session.get('selected_audit')).first() or audits.order_by('pk').first()
        if audit:organization=audit.organization
    return organization_brand(organization)

def it_label(audit):
    names=[m.user.get_full_name() or m.user.email for m in audit.membership_set.filter(role='it',user__is_active=True).select_related('user').order_by('user__first_name','user__pk')]
    return 'BT Sorumlusu'+(' ('+', '.join(names)+')' if names else ' (atanmadı)')
