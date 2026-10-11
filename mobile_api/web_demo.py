"""Repeatable browser QA content without altering existing paths or progress."""
TITLE = 'Demo Web • Tüm Soru Tipleri'


def seed_web_demo(apps, schema_editor=None):
    Path = apps.get_model('mobile_api', 'LearningPath')
    Question = apps.get_model('mobile_api', 'Question')
    Audio = apps.get_model('mobile_api', 'AudioAsset')
    path, _ = Path.objects.get_or_create(title=TITLE, owner=None, defaults={
        'description': '10 soru tipi + kaydırmalı bilgi kartı. Görseli aç, ses kaydını dinle, kartları sürükle ve mikrofonla yanıt gönder. Web testi için ücretsiz demo.',
        'published': True, 'premium': False, 'minutes': 12, 'order': 0,
        'preferences': {'demo_all_types': True, 'web_all_types_demo': True},
    })
    audio, _ = Audio.objects.get_or_create(file='demo/mfa.m4a', defaults={'title': 'Demo • İkinci doğrulama'})
    content = [
        ('info', 'Bilgi kartı • Riski üç adımda anlat', '', [], [], 'Bilgi kartını oku ve devam et.'),
        ('choice', '1/10 • Tek seçim: Riski azaltan önleme ne denir?', '', [('a','Kontrol'),('b','Varlık'),('c','Tehdit')], ['a'], 'Kontrol, riskin olasılığını veya etkisini azaltır.'),
        ('multi_select', '2/10 • Çoklu seçim: Güvenli hesap kullanımı için iki önlemi seç.', '', [('a','Çok faktörlü doğrulama'),('b','Parolayı ekip sohbetinde paylaşmak'),('c','Her hesapta farklı parola')], ['a','c'], 'Çok faktörlü doğrulama ve farklı parolalar hesap güvenliğini artırır.'),
        ('fill_blank', '3/10 • Boşluk doldurma: Verilerin yetkisiz kişilere açıklanmaması ______ ilkesidir.', '', [], ['gizlilik'], 'Eksik kelime: gizlilik.'),
        ('text', '4/10 • Kısa yanıt: Senaryonun riskini iki kelimeyle yaz. İlk kelime: veri.', 'Müşteri kayıtları tek diskte ve yedeksiz tutuluyor. Disk bozulursa kayıtlar kurtarılamıyor.', [], ['veri kaybı','veri kaybi'], 'Risk: veri kaybı. Bu demo yalnızca belirtilen kısa yanıtı kontrol eder.'),
        ('image', '5/10 • Görsel: Hangi kullanıcının hesabı kapatılmalı?', 'Görseldeki çalışma ve hesap durumlarını karşılaştır.', [('a','Ayşe'),('b','Mehmet'),('c','Zeynep')], ['b'], 'Mehmet işten ayrılmış ancak hesabı açık kalmış. Hesabı kapatılmalıdır.'),
        ('audio', '6/10 • Ses: Kaydı dinle. Anlatılan kontrol hangisi?', 'Oynat düğmesiyle kaydı başlat. Duraklatmayı ve tekrar dinlemeyi de deneyebilirsin.', [('a','Çok faktörlü doğrulama'),('b','Yedekleme'),('c','Veri maskeleme')], ['a'], 'Paroladan sonra ikinci doğrulama istenmesi çok faktörlü doğrulamadır.'),
        ('scenario', '7/10 • Senaryo: En uygun kontrol hangisi?', 'Bir çalışan tedarikçi ödemesini hem oluşturuyor hem de tek başına onaylıyor.', [('a','Ödemeyi başka bir yetkiliye onaylatmak'),('b','Ekran rengini değiştirmek'),('c','Kontrolü kaldırmak')], ['a'], 'Görevler ayrılığı, ödeme oluşturma ve onaylama yetkilerini ayırır.'),
        ('sentence_order', '8/10 • Cümle kur: Parçaları doğru sıraya taşı.', 'İşten ayrılan çalışanların hesapları açık kalıyor.', [('impact','ve müşteri bilgilerinin ifşa olması'),('end','riski vardır.'),('cause','Eski çalışan hesaplarının açık kalması nedeniyle,'),('event','yetkisiz kişilerin sisteme erişmesi')], ['cause','event','impact','end'], 'Doğru sıra: neden → olay → etki → riski vardır.'),
        ('drag_select', '9/10 • Kart kaydır: Doğru riski cevap alanına taşı.', 'Yedek alınıyor ancak geri yükleme testi yapılmıyor.', [('b','Ofis ışıklarının azalması'),('a','Kesinti sırasında verilerin geri getirilememesi'),('c','Klavye renginin değişmesi')], ['a'], 'Geri yükleme testi yapılmaması, yedeklerin gerektiğinde kullanılamaması riskini doğurur.'),
        ('voice', '10/10 • Sesli veya yazılı yanıt: Riski kısa bir kayıtla anlat ya da iki kelimeyle yaz.', 'Müşteri verileri yedeksiz bir bilgisayarda tutuluyor. Mikrofona izin verip kısa bir kayıt yap; duraklatmayı, tekrar dinlemeyi ve göndermeyi dene. Yazılı alternatif: veri kaybı. Sesli yanıt yönetici incelemesine gider; otomatik doğru/yanlış değerlendirilmez.', [], ['veri kaybı','veri kaybi'], 'Örnek: Yedek bulunmaması nedeniyle disk arızasında müşteri verilerinin kaybolması ve hizmetlerin aksaması riski vardır.'),
    ]
    for order, (kind, prompt, context, options, answer, explanation) in enumerate(content):
        if path.questions.filter(kind=kind).exists():
            continue
        q = Question.objects.create(kind=kind, prompt=prompt, context=context,
            options=[{'id': key, 'text': text} for key, text in options], answer=answer,
            explanation=explanation, published=True, premium=False,
            base_xp=0 if kind == 'info' else 20, order=order,
            image='demo/access-review.png' if kind == 'image' else '',
            audio=audio if kind == 'audio' else None,
            card_pages=[
                {'title': '1 • Neden', 'body': '**Kontrol eksikliği** ile başla.\n\n*Yedekleme yapılmaması nedeniyle…*', 'reveal': 'Neden: Riski mümkün kılan durum.'},
                {'title': '2 • Olay', 'body': '**Ne gerçekleşebilir?**\n\n*…disk arızasında müşteri verilerinin kaybolması…*', 'reveal': 'Olay: Gerçekleşmesi belirsiz durum.'},
                {'title': '3 • Etki', 'body': '**İş sonucunu** ekle.\n\n*…ve hizmetlerin aksaması riski vardır.*', 'reveal': 'Neden → Olay → Etki.'},
            ] if kind == 'info' else [])
        q.paths.add(path)
    return path
