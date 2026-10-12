# Doğrulama sonuçları

12 Ekim 2026, yerel SQLite test ortamı:

- Django: 5 test başarılı. 100 kayıt gerçek API akışından sırayla tamamlandı: 90 doğru cevap, 10 bilgi kartı. Kullanıcı ilerlemesi yeniden import sonrası korundu.
- Doğru/yanlış sıralama, eksik çoklu seçim, yanlış boşluk cevabı doğrulandı.
- 9 gerçek PNG dosyasının başlığı ve yetkili indirme API'si doğrulandı; anonim erişim reddedildi.
- Dry-run yazmadı; ikinci import 0 yeni kayıt. Hedef dışı yol, kayıt ve tercihler korundu. Yanlış ID ve kayıtlı olmayan mevcut içerik işlemi durdurdu.
- Flutter: 9 telefon genişliği render testi başarılı; kullanılan 8 soru tipi, geç intro yokluğu ve seçim/yazı etkileşimi doğrulandı. Flutter testinde görsel indirme taklit edilmedi; görsel baytları ve yetkilendirme backend testinde doğrulandı.
- 0030 veri migration'ı yerelde ileri, geri ve yeniden ileri çalıştı. Geri alma kayıt silmeden görünürlüğü kapattı; tekrar ileri 100 kaydı yeniden görünür yaptı. Sonraki import 0 yeni kayıt.
- 100 benzersiz external_id, 10 bölümde 10 kayıt. Tip dağılımı quality_report.json içinde. 10 intro metni 115 kelime/dakika hesabıyla 2–4 dakika.

Bu rapor yerel test sonuçlarını belirtir. Canlı yayın doğrulaması ayrıca yayın sonrası yönetim ekranından yapılır.
