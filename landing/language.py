"""Add the shared language UI only to public HTML; APIs/admin remain untouched."""
import json

from django.utils.html import format_html
from django.template.loader import render_to_string
from django.templatetags.static import static


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
        catalogs = {language: static(f'i18n/{language}.json')
                    for language in ('en', 'fr', 'es', 'ja', 'zh-CN', 'vi', 'ar')}
        assets = format_html(
            '<link rel="stylesheet" href="{}">'
            '<script defer src="{}" data-catalogs="{}"></script>',
            static('css/site-language.css'), static('js/site-language.js'),
            json.dumps(catalogs),
        )
        # Appended after existing deferred scripts so their initial copy is included.
        content = content.replace('</head>', assets + '</head>', 1)
        panel = render_to_string('landing/_language_switcher.html', request=request)
        response.content = content.replace('</body>', panel + '</body>', 1)
        if response.has_header('Content-Length'):
            response['Content-Length'] = len(response.content)
        return response
