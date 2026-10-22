"""Add the shared language UI only to public HTML; APIs/admin remain untouched."""
import json
import re
import html
from pathlib import Path
from functools import lru_cache

from .jurisdictions import preference, LANGUAGE_COUNTRIES, COUNTRY_NAMES, locale_url
from .legal_registry import UI
from .public_translation import translate_public_html

from .bootcamp_catalog import public_program_prices

from django.utils.html import format_html
from django.utils.cache import patch_vary_headers
from django.template.loader import render_to_string
from django.templatetags.static import static


@lru_cache(maxsize=8)
def metadata_catalog(language):
    return {} if language == 'tr' else json.loads((Path(__file__).resolve().parent.parent/'static/i18n'/f'{language}.json').read_text())


class PublicLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        match = getattr(request, 'resolver_match', None)
        public = match and (
            (match.namespace == 'landing' and match.url_name != 'traffic_dashboard')
            or match.view_name == 'login'
        )
        if (not public or response.streaming or response.status_code >= 400
                or not response.get('Content-Type', '').startswith('text/html')):
            return response
        content = response.content.decode(response.charset)
        if '</head>' not in content or '</body>' not in content:
            return response
        language, country = preference(request)
        config = {'countries': LANGUAGE_COUNTRIES, 'names': COUNTRY_NAMES,
                  'labels': {lang: copy[2] for lang,copy in UI.items()},
                  'languageLabels': dict(zip(LANGUAGE_COUNTRIES, ['Dil seç','Choose language','Choisir la langue','Elegir idioma','言語を選択','选择语言','Chọn ngôn ngữ','اختيار اللغة'])),
                  'errors': {lang: copy[16] for lang,copy in UI.items()},
                  'surface': 'home' if match.url_name in ('home','career_compass') else 'other',
                  'detailed': match.url_name == 'regulations'}
        seo_sources = {'title':html.unescape(re.search(r'<title>(.*?)</title>',content,re.S).group(1)) if '<title>' in content else 'GRC Ustası'}
        for key,pattern in [('description',r'<meta name="description" content="([^"]*)"'),('og:title',r'<meta property="og:title" content="([^"]*)"'),('og:description',r'<meta property="og:description" content="([^"]*)"')]:
            found=re.search(pattern,content)
            if found:seo_sources[key]=html.unescape(found.group(1))
        config['seo']={}
        for lang in LANGUAGE_COUNTRIES:
            copy=metadata_catalog(lang)
            config['seo'][lang]={key:copy.get(value,value) for key,value in seo_sources.items()}
        config['otPage'] = match.url_name == 'ot_bootcamp'
        config['prices'] = public_program_prices().get('ot_security', {})
        config['legalPage'] = match.url_name == 'regulations'
        config['headings'] = {lang: row[1] for lang,row in UI.items()}
        config['eyebrows'] = {lang: row[0] for lang,row in UI.items()}
        catalogs = {language: static(f'i18n/{language}.json')
                    for language in ('en', 'fr', 'es', 'ja', 'zh-CN', 'vi', 'ar')}
        assets = format_html(
            '<link rel="stylesheet" href="{}">'
            '<script defer src="{}" data-config="{}"></script>'
            '<script defer src="{}" data-catalogs="{}" data-prices="{}" data-rendered-language="{}"></script>',
            static('css/site-language.css'), static('js/site-jurisdiction.js'),json.dumps(config), static('js/site-language.js'),
            json.dumps(catalogs), json.dumps(public_program_prices()), language,
        )
        # Appended after existing deferred scripts so their initial copy is included.
        if match.namespace == 'landing' and match.url_name in ('home','corporate','ot_bootcamp','regulations'):
            content = re.sub(r'<link\b[^>]*rel=[\"\'](?:canonical|alternate)[\"\'][^>]*>', '', content, flags=re.I)
            seo = str(format_html('<link rel="canonical" href="{}">', locale_url(request.path,language,country)))
            for alternate, countries in LANGUAGE_COUNTRIES.items():
                for code in countries:
                    tag = ('en-150' if code == 'EU' else alternate if alternate == 'zh-CN' else alternate+'-'+code)
                    seo += str(format_html('<link rel="alternate" hreflang="{}" href="{}">', tag,locale_url(request.path,alternate,code)))
            seo += str(format_html('<link rel="alternate" hreflang="x-default" href="{}">', locale_url(request.path,'tr','TR')))
            if match.url_name == 'regulations':
                localized={'title':COUNTRY_NAMES[country]+' · '+UI[language][0]+' | GRC Ustası', 'description':UI[language][1]+' '+COUNTRY_NAMES[country]}
            else:
                localized=config['seo'][language].copy()
                if config['otPage']:
                    quote=config['prices'][language]
                    price=(f"{quote['amount']:,}".replace(',','.')+' TL') if language=='tr' else f"{quote['amount']:,} {quote['currency'].upper()}"
                    for key,value in localized.items():localized[key]=re.sub(r'119[.,]999.*$',price+'.',value)
            content = re.sub(r'<title>.*?</title>',str(format_html('<title>{}</title>',localized['title'])),content,flags=re.S)
            for key in ('description','og:title','og:description'):
                value=localized.get(key,localized.get('title') if key=='og:title' else localized.get('description',''))
                attribute='name' if key=='description' else 'property'
                content=re.sub(r'<meta\b[^>]*'+attribute+'="'+key+r'"[^>]*>', '',content,flags=re.I)
                seo+=str(format_html('<meta {}="{}" content="{}">',attribute,key,value))
            content=re.sub(r'<meta property="og:(?:locale|url)"[^>]*>','',content)
            seo+=str(format_html('<meta property="og:url" content="{}"><meta property="og:locale" content="{}">',locale_url(request.path,language,country),language.replace('-','_')+'_'+country if '-' not in language else language.replace('-','_')))
            assets = seo + str(assets)
        content = content.replace('</head>', str(assets) + '</head>', 1)
        panel = render_to_string('landing/_language_switcher.html', request=request)
        content = re.sub(r'<html\b[^>]*>', str(format_html('<html lang="{}" dir="{}">',language,'rtl' if language=='ar' else 'ltr')), content, count=1)
        patch_vary_headers(response, ('Cookie',))
        response['Content-Language'] = language
        content = content.replace('</body>', panel + '</body>', 1)
        response.content = translate_public_html(content, metadata_catalog(language)) if language != 'tr' else content
        if response.has_header('Content-Length'):
            response['Content-Length'] = len(response.content)
        return response
