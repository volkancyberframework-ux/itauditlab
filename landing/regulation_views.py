from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET
from django.views.decorators.cache import never_cache
from django.utils.html import escape
from . import legal_registry
from .jurisdictions import LANGUAGE_COUNTRIES, locale_url

@require_GET
@never_cache
def fragment(request):
    ctx=legal_registry.context(request,request.GET.get('detail')=='1')
    ctx['legal_show_outcome']=request.GET.get('surface')=='home'
    return JsonResponse({'html':render_to_string('landing/_regulations.html',ctx,request=request),
                         'language':ctx['legal_language'],'country':ctx['legal_country']})

@require_GET
def page(request):
    return render(request,'landing/regulations.html',legal_registry.context(request,True))

@require_GET
def sitemap(request):
    urls=[]
    for path in ('/','/kurumsal/','/ot-guvenligi-bootcamp/','/mevzuat/'):
        for language,countries in LANGUAGE_COUNTRIES.items():
            for country in countries:
                urls.append('<url><loc>'+escape(locale_url(path,language,country))+'</loc></url>')
    return HttpResponse('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(urls)+'</urlset>',content_type='application/xml')

@require_GET
def robots(request):
    return HttpResponse('User-agent: *\nDisallow: /bulamazsinki/\nDisallow: /api/\nDisallow: /odeme/\nSitemap: https://www.grcustasi.com/sitemap.xml\n',content_type='text/plain')
