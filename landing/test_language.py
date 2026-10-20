import json
from pathlib import Path
from types import SimpleNamespace

from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.test import RequestFactory, SimpleTestCase

from .language import PublicLanguageMiddleware


class PublicLanguageTests(SimpleTestCase):
    def response(self, response=None, namespace='landing', name='home'):
        request = RequestFactory().get('/')
        request.resolver_match = SimpleNamespace(namespace=namespace, url_name=name, view_name=f'{namespace}:{name}')
        original = response if response is not None else HttpResponse('<html lang="tr"><head></head><body><form>Türkçe<input name="email"></form></body></html>')
        return PublicLanguageMiddleware(lambda request: original)(request)

    def test_public_page_preserves_form_and_injects_all_languages(self):
        response = self.response()
        self.assertContains(response, '<form>Türkçe<input name="email"></form>')
        self.assertContains(response, 'site-language.js', count=1)
        for language in ('tr', 'en', 'fr', 'es', 'ja', 'zh-CN', 'vi', 'ar'):
            self.assertContains(response, f'data-language="{language}"')

    def test_admin_analytics_json_errors_and_streams_are_untouched(self):
        for namespace, name in (('admin', 'index'), ('landing', 'traffic_dashboard'), ('core', 'dashboard')):
            self.assertNotContains(self.response(namespace=namespace, name=name), 'site-language.js')
        data = JsonResponse({'message': 'Türkçe'})
        self.assertIs(self.response(data), data)
        error = HttpResponse('Missing', status=404)
        self.assertIs(self.response(error), error)
        stream = StreamingHttpResponse(iter(['content']))
        self.assertIs(self.response(stream), stream)

    def test_catalog_urls_support_hashed_production_assets(self):
        from unittest.mock import patch
        def hashed_asset(path):
            self.assertFalse(path.endswith('/'))
            return '/static/' + path.replace('.json', '.abc123.json')
        with patch('landing.language.static', side_effect=hashed_asset):
            response = self.response()
        self.assertContains(response, '/static/i18n/en.abc123.json')
        self.assertContains(response, 'data-catalogs=')

    def test_content_length_is_updated(self):
        response = HttpResponse('<head></head><body></body>')
        response['Content-Length'] = len(response.content)
        result = self.response(response)
        self.assertEqual(int(result['Content-Length']), len(result.content))

    def test_catalogs_have_matching_keys_and_preserve_interpolation(self):
        base = Path(__file__).resolve().parent.parent / 'static/i18n'
        reference = json.loads((base / 'en.json').read_text())
        self.assertGreater(len(reference), 1000)
        import re
        for language in ('en', 'fr', 'es', 'ja', 'zh-CN', 'vi', 'ar'):
            catalog = json.loads((base / f'{language}.json').read_text())
            self.assertEqual(set(catalog), set(reference), language)
            for key, value in catalog.items():
                self.assertTrue(isinstance(value, str) and value.strip(), (language, key))
                count = len(re.findall(r'\$\{[^}]+\}', key))
                if count:
                    for index in range(count):
                        self.assertIn(f'GRCPLACEHOLDER{index}', value, (language, key))
