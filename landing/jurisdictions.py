"""Language is presentation; jurisdiction is an independent, explicit preference."""
from urllib.parse import urlencode

LANGUAGE_COUNTRIES = {'tr': ('TR',), 'en': ('US','GB','EU'), 'fr': ('FR','BE'),
                      'es': ('ES','CL','MX','AR'), 'ja': ('JP',), 'zh-CN': ('CN',),
                      'vi': ('VN',), 'ar': ('SA',)}
COUNTRY_NAMES = {'TR':'Türkiye','US':'United States','GB':'United Kingdom','EU':'European Union',
                 'FR':'France','BE':'Belgique','ES':'España','CL':'Chile','MX':'México',
                 'AR':'Argentina','JP':'日本','CN':'中国','VN':'Việt Nam','SA':'المملكة العربية السعودية'}

def preference(request):
    language = request.GET.get('lang', request.COOKIES.get('grc-language', 'tr'))
    if language not in LANGUAGE_COUNTRIES:
        language = 'tr'
    allowed = LANGUAGE_COUNTRIES[language]
    country = request.GET.get('country', request.COOKIES.get('grc-country-'+language, allowed[0])).upper()
    return language, country if country in allowed else allowed[0]

def locale_url(path, language, country):
    return 'https://www.grcustasi.com' + path + '?' + urlencode({'lang':language,'country':country})
