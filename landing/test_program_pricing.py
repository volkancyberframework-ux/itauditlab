import json
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from .bootcamp_catalog import PUBLIC_LANGUAGES, public_program_prices


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class ProgramPricingTests(TestCase):
    @override_settings(STRIPE_SECRET_KEY='sk_test_placeholder')
    def test_every_program_language_uses_fixed_currency_and_server_amount(self):
        for product in ('', 'grc_ustasi_80_saat', 'cisa', 'cism', 'ot_security'):
            for language in PUBLIC_LANGUAGES:
                with self.subTest(product=product, language=language), patch('stripe.checkout.Session.create') as create:
                    create.return_value.id='cs_pricing_'+str(product or 'grc')+'_'+language
                    create.return_value.url='https://checkout.stripe.com/pricing-test'
                    response=self.client.post(reverse('landing:checkout'),{'product':product,'language':language,'price':'1','currency':'jpy','unit_amount':'1'})
                    self.assertEqual(response.status_code,302)
                    ot=product=='ot_security'
                    currency='try' if language=='tr' else 'eur' if language in ('fr','es') else 'usd'
                    amount=(119999 if ot else 89999) if currency=='try' else (2499 if ot else 1899) if currency=='eur' else (2599 if ot else 1999)
                    data=create.call_args.kwargs
                    price=data['line_items'][0]['price_data']
                    self.assertEqual((price['unit_amount'],price['currency']),(amount*100,currency))
                    self.assertEqual(data['metadata']['price_amount'],str(amount))
                    self.assertEqual(data['metadata']['currency'],currency)
                    self.assertEqual(data['metadata']['product'],product or 'grc_ustasi_80_saat')
                    self.assertEqual(data['metadata']['mobile_membership'],'lifetime')
                    self.assertIn('bootcamp_checkout_id',data['metadata'])
                    self.assertEqual(data['locale'],{'zh-CN':'zh','ar':'en'}.get(language,language))
                    key=product or 'grc_ustasi_80_saat'
                    self.assertEqual(public_program_prices()[key][language],{'amount':amount,'currency':currency})

    @override_settings(STRIPE_SECRET_KEY='sk_test_placeholder')
    def test_unknown_language_defaults_to_turkish_price(self):
        with patch('stripe.checkout.Session.create') as create:
            create.return_value.id='cs_unknown_language'
            create.return_value.url='https://checkout.stripe.com/pricing-test'
            self.client.post(reverse('landing:checkout'),{'product':'ot_security','language':'../../usd'})
        self.assertEqual(create.call_args.kwargs['line_items'][0]['price_data']['unit_amount'],11999900)
        self.assertEqual(create.call_args.kwargs['line_items'][0]['price_data']['currency'],'try')

    def test_all_money_surfaces_are_structured_and_translation_excluded(self):
        from html.parser import HTMLParser
        class Prices(HTMLParser):
            def __init__(self): super().__init__(); self.keys=[]; self.forms=[]
            def handle_starttag(self,tag,attrs):
                attrs=dict(attrs)
                if tag=='form' and 'data-program-checkout' in attrs:
                    self.forms.append(attrs['data-program-checkout'])
                if 'data-program-price' in attrs:
                    self.keys.append(attrs['data-program-price'])
                    assert attrs.get('translate')=='no'
        for url,expected in [('/', ['ot_security','grc_ustasi_80_saat','cisa','cism','ot_security']),('/ot-guvenligi-bootcamp/',['ot_security'])]:
            response=self.client.get(url)
            parser=Prices();parser.feed(response.content.decode())
            self.assertEqual(sorted(parser.keys),sorted(expected))
            self.assertEqual(sorted(parser.forms),sorted(['grc_ustasi_80_saat','cisa','cism'] if url=='/' else ['ot_security']))
            self.assertContains(response,'data-prices=')
            self.assertContains(response,'site-theme.js')
