"""Single source of truth for bootcamp content and Stripe product metadata."""

BOOTCAMPS = (
    {
        "key": "cisa",
        "anchor": "cisa-bootcamp",
        "theme": "audit",
        "icon": "shield",
        "badge": "DENETİM YOLU",
        "path_label": "Denetçi / GRC Uzmanı",
        "title": "CISA Bootcamp",
        "subtitle": "IT Audit • GRC • Technology Risk",
        "description": "BT denetimi, GRC, teknoloji riski ve kontrol alanlarında uzmanlaşmak isteyenler için kapsamlı kariyer programı. CISA sınav hazırlığından gerçeğe uygun, simüle edilmiş denetim vakalarına ve iş bulma sürecine kadar uçtan uca ilerle.",
        "preparation": "Sadece sertifikaya değil, mülakata girdiğinde anlatacağın mesleki hikâyeye kadar hazırlanman için tasarlandı.",
        "features": ("40+ Saat Bootcamp", "5.000+ Soruluk Soru Bankası", "Gerçeğe Uygun Denetim Vakaları", "Vaka, Lab, Quiz ve Sınav Setleri", "Canlı Sınıflar", "Birebir Görüşmeler", "6 Ay Eğitim", "+6 Ay İş Bulma ve Kariyer Desteği"),
        "case_disclaimer": "Tüm vaka ve kurum adları eğitim amacıyla kurgulanmıştır. Gerçek kurumlarla herhangi bir bağlantısı veya ilgisi yoktur.",
        "duration": "12 Aylık Yolculuk",
        "duration_detail": "6 Ay Eğitim + 6 Ay İş Bulma Desteği",
        "price": 89_999,
        "price_display": "89.999 TL",
        "price_note": "Tek seferlik program ücreti",
        "cta": "CISA Bootcamp’e Katıl",
    },
    {
        "key": "cism",
        "anchor": "cism-bootcamp",
        "theme": "leadership",
        "icon": "compass",
        "badge": "YÖNETİCİLİK YOLU",
        "path_label": "Yönetici / CISO Yolu",
        "title": "CISM Bootcamp",
        "subtitle": "Security Management • GRC Leadership • CISO Path",
        "description": "Siber güvenlik yöneticisi olmak, mevcut kariyerini yönetim seviyesine taşımak veya gelecekte CISO yolunda ilerlemek isteyen profesyoneller için kapsamlı program.",
        "features": ("40+ Saat Bootcamp", "5.000+ Soruluk Soru Bankası", "Yönetim ve GRC Vakaları", "Quizler ve Deneme Sınavları", "Canlı Sınıflar", "Birebir Görüşmeler", "6 Ay Eğitim", "+6 Ay İş Bulma ve Kariyer Desteği"),
        "duration": "12 Aylık Yolculuk",
        "duration_detail": "6 Ay Eğitim + 6 Ay İş Bulma Desteği",
        "price": 89_999,
        "price_display": "89.999 TL",
        "price_note": "Tek seferlik program ücreti",
        "cta": "CISM Bootcamp’e Katıl",
    },
)

BOOTCAMPS_BY_KEY = {item["key"]: item for item in BOOTCAMPS}


OT_BOOTCAMP = {
    "key": "ot_security", "title": "OT Güvenliği Bootcamp — 12 Aylık Birebir Program",
    "description": "12 ay boyunca birebir çalışma modeliyle 150 saatlik öğrenme ve 150 saatlik uygulamalı aktivite içeren kapsamlı bir program.",
    "price": 119_999, "price_display": "119.999 TL",
}
BOOTCAMPS_BY_KEY[OT_BOOTCAMP["key"]] = OT_BOOTCAMP


GRC_PROGRAM = {
    "key": "grc_ustasi_80_saat", "title": "80 Saatlik GRC Ustası Yoğun Eğitim Programı",
    "description": "6 ay eğitim ve uygulama, 6 ay kariyer desteği, ömür boyu içerik erişimi.",
    "price": 89_999, "price_display": "89.999 TL",
}
BOOTCAMPS_BY_KEY[GRC_PROGRAM["key"]] = GRC_PROGRAM
PUBLIC_LANGUAGES = ('tr', 'en', 'fr', 'es', 'ja', 'zh-CN', 'vi', 'ar')


def program_quote(product_key, language='tr'):
    """Fixed language-based prices, independent of client amounts and FX rates."""
    product = BOOTCAMPS_BY_KEY[product_key]
    if language not in PUBLIC_LANGUAGES:
        language = 'tr'
    currency = 'try' if language == 'tr' else 'eur' if language in ('fr', 'es') else 'usd'
    ot = product_key == 'ot_security'
    amount = product['price'] if currency == 'try' else (2499 if ot else 1899) if currency == 'eur' else (2599 if ot else 1999)
    return {'amount': amount, 'currency': currency}


def public_program_prices():
    return {key: {language: program_quote(key, language) for language in PUBLIC_LANGUAGES}
            for key in BOOTCAMPS_BY_KEY}
