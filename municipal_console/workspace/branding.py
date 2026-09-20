from django.conf import settings

def brand_context(request):
    tenant=getattr(request,'tenant',None)
    return {'brand_name':'Torbalı Belediyesi','brand_logo':'img/torbali-belediyesi.gif','brand_domain':tenant.subdomain+'.grcustasi.com' if tenant and tenant.subdomain else settings.TENANT_DOMAIN}
