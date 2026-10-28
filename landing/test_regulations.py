from copy import deepcopy
from unittest.mock import patch
from datetime import date
from django.core.exceptions import ValidationError
from django.test import TestCase, RequestFactory
from django.urls import reverse
from .jurisdictions import preference, LANGUAGE_COUNTRIES
from .legal_registry import DATA, get_regulations
from .models import LegalRegulation, LegalRevision
from .legal_sources import validate_source_url

class LegalRegistryTests(TestCase):
    def test_every_supported_country_has_only_native_reviewed_records(self):
        for language,countries in LANGUAGE_COUNTRIES.items():
            for country in countries:
                with self.subTest(language=language,country=country):
                    rows=get_regulations(country,language)
                    self.assertTrue(rows)
                    for row in rows:
                        self.assertEqual(row['country_code'],country)
                        self.assertEqual(row['review_state'],'verified')
                        self.assertTrue(row['official_source_url'].startswith('https://'))
                        self.assertTrue(row['last_verified_at'])
                        self.assertTrue(row['audit_requirements'])
        self.assertEqual(get_regulations('VN','tr'),[])
        self.assertEqual(get_regulations('ZZ','en'),[])

    def test_seed_data_passes_editorial_validation_and_has_revision(self):
        for row in LegalRegulation.objects.all():row.full_clean()
        self.assertEqual(LegalRegulation.objects.count(),len(DATA))
        self.assertEqual(LegalRevision.objects.count(),len(DATA))

    def test_draft_upcoming_and_international_guidance_are_distinct(self):
        records={row['id']:row for country,lang in [('CL','es'),('US','en'),('FR','fr')] for row in get_regulations(country,lang)}
        self.assertEqual(records['cl-privacy-new']['status'],'upcoming')
        self.assertEqual(records['us-circia']['status'],'draft')
        self.assertEqual(records['fr-nis2']['status'],'draft')
        self.assertEqual(records['us-nist']['category'],'guidance')
        self.assertNotIn('es-nis2',[r['id'] for r in get_regulations('ES','es')])

    def test_editorial_unpublish_never_falls_back_to_seed(self):
        LegalRegulation.objects.filter(pk='vn-cyber').update(published=False)
        self.assertNotIn('vn-cyber',[r['id'] for r in get_regulations('VN','vi')])
        LegalRegulation.objects.filter(pk='vn-privacy').update(review_state='needs_review')
        self.assertNotIn('vn-privacy',[r['id'] for r in get_regulations('VN','vi')])

    def test_unsafe_or_incomplete_sources_cannot_be_published(self):
        row=LegalRegulation.objects.get(pk='us-sec')
        for url in ['http://www.sec.gov/a','https://127.0.0.1/a','https://www.sec.gov.evil.example/a','https://user:password@www.sec.gov/a','https://www.sec.gov:444/a']:
            with self.subTest(url=url),self.assertRaises(ValidationError):validate_source_url(url)
        row.last_verified_at=None
        with self.assertRaises(ValidationError):row.full_clean()
        row.last_verified_at=date.today();row.effective_date=date(2099,1,1)
        with self.assertRaises(ValidationError):row.full_clean()

    def test_preferences_validate_country_and_preserve_language(self):
        factory=RequestFactory()
        request=factory.get('/?lang=es&country=CL')
        self.assertEqual(preference(request),('es','CL'))
        request=factory.get('/?lang=vi&country=TR')
        self.assertEqual(preference(request),('vi','VN'))
        request=factory.get('/')
        request.COOKIES={'grc-language':'fr','grc-country-fr':'BE'}
        self.assertEqual(preference(request),('fr','BE'))

    def test_server_rendered_content_metadata_and_sitemap_all_locales(self):
        for language,countries in LANGUAGE_COUNTRIES.items():
            for country in countries:
                response=self.client.get('/mevzuat/',{'lang':language,'country':country})
                self.assertEqual(response.status_code,200)
                self.assertContains(response,f'data-country="{country}"')
                self.assertContains(response,'rel="canonical"',count=1)
                self.assertContains(response,'hreflang="es-CL"',count=1)
                self.assertEqual(response['Content-Language'],language)
                if country=='VN':
                    section=response.content.decode().split('data-legal-section')[1].split('</section>')[0]
                    self.assertNotIn('7545',section)
                    self.assertNotIn('KVKK',section)
        sitemap=self.client.get('/sitemap.xml')
        self.assertContains(sitemap,'country=CL')
        self.assertEqual(sitemap.content.count(b'<url>'),42)

    def test_home_uses_jurisdiction_and_keeps_forms(self):
        for path in ['/']:
            response=self.client.get(path,{'lang':'es','country':'MX'})
            self.assertContains(response,'data-country="MX"')
            self.assertContains(response,'LFPDPPP')
            self.assertNotContains(response,'class="law-number"')
        self.assertContains(self.client.get('/'),'data-program-checkout="cisa"')

    def test_fragment_is_read_only_and_never_cached(self):
        response=self.client.get('/api/mevzuat/?lang=es&country=AR&detail=1')
        self.assertEqual(response.json()['country'],'AR')
        self.assertIn('25.326',response.json()['html'])
        self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(self.client.post('/api/mevzuat/').status_code,405)

    @patch('landing.management.commands.check_legal_sources.fingerprint',return_value='newhash')
    def test_source_checks_never_change_publication_or_legal_verification(self,fingerprint):
        from django.core.management import call_command
        from io import StringIO
        row=LegalRegulation.objects.get(pk='us-sec');row.source_hash='oldhash';row.save()
        before=(row.published,row.review_state,row.last_verified_at,deepcopy(row.translations))
        call_command('check_legal_sources',country='US',limit=100,stdout=StringIO())
        row.refresh_from_db()
        self.assertEqual((row.published,row.review_state,row.last_verified_at,row.translations),before)
        self.assertIn('changed',row.link_status)
        self.assertEqual(row.source_hash,'oldhash')


class PublicCopyTranslationTests(TestCase):
    def test_server_copy_preserves_scripts_brands_and_form_values(self):
        from .public_translation import translate_public_html
        source='<html><head><script>const test=1<2&&true;</script></head><body><a class="brand">GRC Ustası</a><p>Merhaba</p><input name="email" value="Merhaba" placeholder="Merhaba"><div translate="no">Merhaba</div></body></html>'
        result=translate_public_html(source,{'Merhaba':'Hello','GRC Ustası':'Wrong brand'})
        self.assertIn('const test=1<2&&true;',result)
        self.assertIn('<p>Hello</p>',result)
        self.assertIn('value="Merhaba" placeholder="Hello"',result)
        self.assertIn('<a class="brand">GRC Ustası</a>',result)
        self.assertIn('<div translate="no">Merhaba</div>',result)
    def test_native_body_is_available_without_javascript(self):
        response=self.client.get('/?lang=es&country=CL')
        self.assertNotContains(response,'Bu alan sana ne kadar uygun?')
        self.assertContains(response,'Ley 21.663')
        self.assertContains(response,'data-rendered-language="es"')
        self.assertContains(response,'<html lang="es" dir="ltr">')
    def test_html_translation_cannot_inject_catalog_markup(self):
        from .public_translation import translate_public_html
        result=translate_public_html('<p>Metin</p>',{'Metin':'<img src=x onerror=alert(1)>'})
        self.assertNotIn('<img',result)
        self.assertIn('&lt;img',result)
    def test_deleted_and_moved_records_do_not_resurrect(self):
        LegalRegulation.objects.filter(pk='vn-cyber').update(country_code='TR')
        self.assertNotIn('vn-cyber',[r['id'] for r in get_regulations('VN','vi')])

    def test_non_turkish_ot_metadata_has_correct_currency(self):
        for language in ('en','fr','es','ja','zh-CN','vi','ar'):
            response=self.client.get('/ot-guvenligi-bootcamp/',{'lang':language})
            import re,html
            meta=html.unescape(re.search(r'<meta name="description" content="([^"]*)"',response.content.decode()).group(1))
            self.assertIn('EUR' if language in ('fr','es') else 'USD',meta)
            self.assertNotIn('119.999',meta)
            self.assertNotIn('liras turcas',meta)
            self.assertNotIn('ليرة تركية',meta)
    def test_server_translates_interpolated_copy_with_reordered_placeholders(self):
        from .public_translation import translate_public_html
        result=translate_public_html('<em>10 Saat · 14 Ders</em>',{'${hours} Saat · ${lessons} Ders':'GRCPLACEHOLDER1 lessons / GRCPLACEHOLDER0 hours'})
        self.assertIn('14 lessons / 10 hours',result)
