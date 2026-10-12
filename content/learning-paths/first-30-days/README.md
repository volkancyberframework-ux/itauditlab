# İlk 30 Gün — teslim ve yayın

100 kayıt: 90 puanlanan soru + 10 bilgi kartı; 10 bölüm. Dil sade Türkçe. 9 gerçek PNG kanıt, 10 adet 2–4 dakikalık kayıt metni.

Kaynak: cases.tsv. Yapılandırılmış paket: package.json. Üretici build.py yalnız Python/Pillow ile kurgusal kanıt oluşturur. Sabit kimlikler grc-first30-q-001 … 100; DB kimlikleri LearningPath.preferences.first30_v1.questions içinde saklanır.

## Tip dönüşümü

19 choice, 10 multi_select, 10 fill_blank, 9 image, 22 scenario, 10 sentence_order, 10 drag_select, 10 info. Sesli soru/voice yok. Şartnamedeki 10 serbest profesyonel yazı görevi, mevcut tam metin eşleşmeli değerlendirmenin sınırlaması nedeniyle uygun profesyonel yanıtı seçme senaryosuna çevrildi. Anlamsal serbest metin değerlendirmesi veya kısmi puan iddiası yok. Mevcut XP sistemi korunur; doğru 10 XP, yanlış mevcut sisteme göre kesinti, bilgi kartı 0 XP.

## Güvenli yükleme

    python manage.py seed_first30 --path-id 26
    python manage.py seed_first30 --path-id 26 --apply

İlk komut dry-run; ikinci işlem yayına alır. 0030 veri migration'ı mevcut kalıcı ID 26'yı doğrulayarak aynı import'u yapar. ID 26 yoksa yeni kayıt varsaymaz. Başlık veya sahip uyuşmazlığı, registry dışı mevcut içerik, farklı paket sürümü ya da kırık registry işlemi durdurur. Diğer yollar ve öğrencilerin yanıt/puan/ilerleme kayıtları korunur. Tekrar çalıştırma yeni soru üretmez. Şema değişikliği yok.

9 görsel PrivateVoiceStorage'ın immutable bundled fallback'inde tutulur; Render pre-deploy aşamasında disk erişimi gerekmez. Dosyalar yetkili soru görseli API'sinden servis edilir; herkese açık media adresi üretilmez.

## Sesler

Metinler output/audio_scripts/grc_day_01.txt … grc_day_10.txt ve SES_KAYITLARI_TOPLU.md. Gerçek MP3 yüklenene kadar AudioAsset üretilmez, intro=NULL; metin bağlamı kullanılabilir. Gerçek kayıtlar gelince:

    python manage.py attach_first30_audio /path/to/mp3
    python manage.py attach_first30_audio /path/to/mp3 --apply

Tam 10 gerçek dosya doğrulanır, AudioAsset.file.save kullanılır; her bölümün yalnız ilk sorusuna intro bağlanır. Tekrar import mevcut intro'yu korur.

## Geri alma

İçeriği geçici gizlemek için kayıt silmeden:

    python manage.py migrate mobile_api 0029

0030 reverse yalnız bu paketin sorularını ve hedef yolu yayından kaldırır. Yanıtlar/puanlar/ilerleme ve dosyalar silinmez. Sonraki migrate yeniden görünür yapar. Diğer uygulamaların migration'larını geri almak gerekmez.

## Doğrulama

    python manage.py test mobile_api.test_first30 --settings=mobile_api.first30_test_settings

Dry-run, iki kez import, hedef dışı veriyi koruma, yanlış ID/overwrite reddi, 100 kaydın API akışından tamamlanması, doğru/yanlış yanıtlar, özel görsel indirme ve ilerlemenin korunması test edilir. Yerel test veritabanı /tmp altındadır; canlı bağlantı kullanılmaz.
