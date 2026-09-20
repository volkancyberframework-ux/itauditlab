from hashlib import sha256
from django.http import HttpResponse,HttpResponseNotModified,Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_safe
from .models import Organization

@require_safe
def organization_logo(request,organization_id):
    if getattr(request,'tenant',None) and request.tenant.pk!=organization_id:raise Http404
    organization=get_object_or_404(Organization,pk=organization_id)
    if not organization.logo_data:raise Http404
    content=bytes(organization.logo_data)
    tag='"'+sha256(content).hexdigest()+'"'
    response=HttpResponseNotModified() if request.headers.get('If-None-Match')==tag else HttpResponse(content,content_type='image/png')
    response['ETag']=tag
    response['Cache-Control']='public, max-age=0, must-revalidate'
    response['X-Content-Type-Options']='nosniff'
    return response
