from django.db import migrations


def seed_workshop(apps, schema_editor):
    Path = apps.get_model('mobile_api', 'LearningPath')
    Question = apps.get_model('mobile_api', 'Question')
    path, _ = Path.objects.get_or_create(title='Risk Atölyesi • Sürükle ve Kur', owner=None, defaults={
        'description': 'Kartları kaydır, riski seç, cümle parçalarını taşı. 6 etkileşimli görevle risk yazmayı dene.',
        'published': True, 'premium': False, 'minutes': 10, 'order': 0,
    })
    account = 'Bir şirkette işten ayrılan çalışanların kullanıcı hesapları kapatılmıyor. Bu hesaplar müşteri kayıtlarına erişebiliyor.'
    backup = 'Kurum her gece yedek alıyor, ancak son bir yıldır hiç geri yükleme testi yapmamış. Kritik sipariş sistemi bu yedeklere bağlı.'
    payment = 'Muhasebede aynı çalışan hem tedarikçi ödemesi oluşturabiliyor hem de bu ödemeyi tek başına onaylayabiliyor. Bağımsız bir kontrol bulunmuyor.'
    content = [
        ('drag_select', account, 'Bu senaryonun riskini bul. Kartları kaydır ve uygun riski yukarı taşı.',
         [('b', 'Çalışanların yeni bir bilgisayar istemesi'), ('a', 'Yetkisiz erişim sonucu müşteri bilgilerinin ifşa olması'), ('c', 'Ekran çözünürlüğünün düşmesi'), ('d', 'Yazıcıların daha yavaş çalışması')], ['a'],
         'Açık kalan hesaplar bir kontrol eksikliğidir. Risk, yetkisiz erişim gerçekleşmesi ve müşteri bilgilerinin ifşa olmasıdır.'),
        ('sentence_order', account, '4 doğru parçayı seçip sıralayarak risk cümlesini kur. İki parça bu senaryoya ait değil.',
         [('impact', 've müşteri bilgilerinin ifşa olması'), ('decoy1', 'ekranların renk ayarlarının değişmesi'), ('end', 'riski vardır.'), ('cause', 'İşten ayrılan çalışan hesaplarının açık kalması nedeniyle,'), ('decoy2', 've ofis mobilyalarının yenilenmesi'), ('event', 'yetkisiz kişilerin sistemlere erişmesi')], ['cause', 'event', 'impact', 'end'],
         'İşten ayrılan çalışan hesaplarının açık kalması nedeniyle, yetkisiz kişilerin sistemlere erişmesi ve müşteri bilgilerinin ifşa olması riski vardır. Neden → olay → etki sırası riski anlaşılır kılar.'),
        ('drag_select', backup, 'Yedekleme başarılı görünüyor. Asıl risk hangi kartta?',
         [('b', 'Yedek dosyalarının isimlerinin uzun olması'), ('c', 'Ekrandaki başarılı göstergesinin yeşil olması'), ('a', 'Kesinti sırasında verilerin geri getirilememesi ve siparişlerin durması'), ('d', 'Ofisteki sandalye sayısının azalması')], ['a'],
         'Yedeğin alınmış olması geri getirilebildiğini kanıtlamaz. Test eksikliği kurtarma başarısızlığına ve iş kesintisine yol açabilir.'),
        ('sentence_order', backup, '4 parçayla bu senaryonun risk cümlesini oluştur.',
         [('end', 'riski vardır.'), ('event', 'bir kesinti sırasında verilerin geri getirilememesi'), ('cause', 'Geri yükleme testlerinin yapılmaması nedeniyle,'), ('impact', 've iş süreçlerinin uzun süre durması')], ['cause', 'event', 'impact', 'end'],
         'Geri yükleme testlerinin yapılmaması nedeniyle, bir kesinti sırasında verilerin geri getirilememesi ve iş süreçlerinin uzun süre durması riski vardır.'),
        ('text', 'Müşteri kayıtları tek bir diskte tutuluyor. Hiç yedek yok. Diskin fiziksel olarak arızalanması durumunda kayıtları geri getirecek başka bir kaynak bulunmuyor.',
         'Bu senaryonun riskini iki kelimeyle yaz. İpucu: ilk kelime “veri”.', [], ['veri kaybı', 'veri kaybi'],
         'Bu senaryonun riski veri kaybıdır. Yedek bulunmaması nedeniyle, disk arızasında müşteri kayıtlarının kaybolması ve iş süreçlerinin aksaması riski vardır. Bu demo kısa risk adını kontrol eder; serbest açıklamaları otomatik yorumlamaz.'),
        ('sentence_order', payment, 'Kontrol eksikliği, olay ve etkiyi birleştir. 4 parçayla risk cümlesini kur.',
         [('impact', 've kurumun finansal kayba uğraması'), ('end', 'riski vardır.'), ('event', 'sahte ödemelerin tespit edilmeden gerçekleşmesi'), ('cause', 'Ödeme oluşturma ve onaylama yetkilerinin aynı kişide olması nedeniyle,')], ['cause', 'event', 'impact', 'end'],
         'Ödeme oluşturma ve onaylama yetkilerinin aynı kişide olması nedeniyle, sahte ödemelerin tespit edilmeden gerçekleşmesi ve kurumun finansal kayba uğraması riski vardır. Görevler ayrılığı bu riski azaltır.'),
    ]
    for order, (kind, context, prompt, options, answer, explanation) in enumerate(content):
        if path.questions.filter(order=order).exists():
            continue
        question = Question.objects.create(kind=kind, context=context, prompt=prompt,
            options=[{'id': key, 'text': text} for key, text in options], answer=answer,
            explanation=explanation, hint='Kontrol eksikliğini, gerçekleşebilecek olayı ve iş etkisini ayır.',
            published=True, premium=False, base_xp=25, order=order)
        question.paths.add(path)


class Migration(migrations.Migration):
    dependencies = [('mobile_api', '0009_alter_question_answer_alter_question_kind')]
    operations = [migrations.RunPython(seed_workshop, migrations.RunPython.noop)]
