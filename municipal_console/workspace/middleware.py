from django.http import HttpResponseNotFound
from .models import Organization

class TenantMiddleware:
    def __init__(self, get_response): self.get_response=get_response
    def __call__(self, request):
        host=request.get_host().split(':')[0].lower()
        request.tenant=None
        if host.endswith('.grcustasi.com'):
            name=host[:-len('.grcustasi.com')]
            request.tenant=Organization.objects.filter(subdomain=name).first()
            if not request.tenant:
                return HttpResponseNotFound('Bu kurum adresi tanımlanmamış.')
        return self.get_response(request)
