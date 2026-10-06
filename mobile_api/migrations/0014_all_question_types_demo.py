from django.db import migrations


def seed_demo(apps, schema_editor):
    Path = apps.get_model('mobile_api', 'LearningPath')
    Question = apps.get_model('mobile_api', 'Question')
    Audio = apps.get_model('mobile_api', 'AudioAsset')
    path, _ = Path.objects.get_or_create(title='Demo • Tüm Soru Tipleri', owner=None, defaults={
        'description': '10 farklı soru tipi, her birinden bir örnek: seç, yaz, gör, dinle, sürükle ve sesli yanıtla.',
        'published': True, 'premium': False, 'minutes': 10, 'order': 0,
        'preferences': {'demo_all_types': True},
    })
    audio, _ = Audio.objects.get_or_create(file='demo/mfa.m4a', defaults={'title': 'Demo • İkinci doğrulama'})
    content = [
        ('choice', '1/10 • Tek seçim: Riski azaltmak için uygulanan önleme ne denir?', '', [('a','Kontrol'),('b','Varlık'),('c','Tehdit')], ['a'], 'Kontrol, riskin olasılığını veya etkisini azaltan önlemdir.'),
        ('multi_select', '2/10 • Çoklu seçim: Güvenli hesap kullanımı için iki doğru önlemi seç.', '', [('a','Çok faktörlü doğrulama'),('b','Parolayı ekip sohbetinde paylaşmak'),('c','Her hesapta farklı parola')], ['a','c'], 'Çok faktörlü doğrulama ve farklı parolalar hesap güvenliğini artırır.'),
        ('fill_blank', '3/10 • Boşluk doldurma: Verilerin yetkisiz kişilere açıklanmaması ______ ilkesidir. Eksik kelimeyi yaz.', '', [], ['gizlilik'], 'Gizlilik, bilgiye yalnızca yetkili kişilerin erişmesini sağlar.'),
        ('text', '4/10 • Kısa yanıt: Senaryonun riskini iki kelimeyle yaz. İlk kelime: veri.', 'Müşteri kayıtları tek diskte tutuluyor ve hiçbir yedek bulunmuyor. Disk bozulursa kayıtlar geri getirilemiyor.', [], ['veri kaybı','veri kaybi'], 'Risk veri kaybıdır. Bu demo belirtilen kısa yanıtı kontrol eder.'),
        ('image', '5/10 • Görsel soru: Raporda hangi kullanıcının hesabı kapatılmalı?', 'Görseldeki çalışma durumu ve hesap durumunu karşılaştır.', [('a','Ayşe'),('b','Mehmet'),('c','Zeynep')], ['b'], 'Mehmet işten ayrılmış, fakat hesabı açık kalmış. Hesabı kapatılmalıdır.'),
        ('audio', '6/10 • Sesli içerik: Kaydı dinle. Anlatılan kontrol hangisi?', 'Oynat düğmesine basarak kısa senaryoyu dinleyebilirsin.', [('a','Çok faktörlü doğrulama'),('b','Yedekleme'),('c','Veri maskeleme')], ['a'], 'Paroladan sonra ikinci doğrulama istenmesi çok faktörlü doğrulama örneğidir.'),
        ('scenario', '7/10 • Senaryo: Bu durumda en uygun kontrol hangisi?', 'Bir çalışan hem tedarikçi ödemesi oluşturuyor hem de aynı ödemeyi tek başına onaylıyor.', [('a','Ödemeyi başka bir yetkiliye onaylatmak'),('b','Ekran rengini değiştirmek'),('c','Kontrolü kaldırmak')], ['a'], 'Görevler ayrılığı, ödeme oluşturma ve onaylama yetkilerini farklı kişilere verir.'),
        ('sentence_order', '8/10 • Cümle kurma: Dört parçayı sürükleyip doğru sıraya koy.', 'İşten ayrılan çalışan hesapları açık kalıyor.', [('impact','ve müşteri bilgilerinin ifşa olması'),('end','riski vardır.'),('cause','Eski çalışan hesaplarının açık kalması nedeniyle,'),('event','yetkisiz kişilerin sisteme erişmesi')], ['cause','event','impact','end'], 'Neden → olay → etki → riski vardır sırası açık bir risk cümlesi oluşturur.'),
        ('drag_select', '9/10 • Kart kaydırma: Kartları kaydır, doğru riski cevap alanına taşı.', 'Yedek alınıyor ancak hiç geri yükleme testi yapılmıyor.', [('b','Ofis ışıklarının azalması'),('a','Kesinti sırasında verilerin geri getirilememesi'),('c','Klavye renginin değişmesi')], ['a'], 'Geri yükleme testi yapılmaması, yedeklerin gerektiğinde kullanılamaması riskini doğurur.'),
        ('voice', '10/10 • Sesli yanıt: Bu senaryonun riskini kendi cümlenle anlat. Mikrofonla kısa bir kayıt gönder.', 'Müşteri verileri yedeksiz bir bilgisayarda tutuluyor. Neden, gerçekleşebilecek olay ve iş etkisini söyle. Kaydın yönetici incelemesine alınır; otomatik doğru/yanlış değerlendirmesi yapılmaz.', [], [], 'Örnek: Yedek bulunmaması nedeniyle, disk arızasında müşteri verilerinin kaybolması ve hizmetlerin aksaması riski vardır.'),
    ]
    for order, (kind, prompt, context, options, answer, explanation) in enumerate(content):
        if path.questions.filter(kind=kind).exists():
            continue
        q = Question.objects.create(kind=kind, prompt=prompt, context=context,
            options=[{'id': k, 'text': t} for k,t in options], answer=answer,
            explanation=explanation, published=True, premium=False, base_xp=20, order=order,
            image='demo/access-review.png' if kind == 'image' else '',
            audio=audio if kind == 'audio' else None)
        q.paths.add(path)


class Migration(migrations.Migration):
    dependencies = [('mobile_api', '0013_default_levels_and_badges')]
    operations = [migrations.RunPython(seed_demo, migrations.RunPython.noop)]
