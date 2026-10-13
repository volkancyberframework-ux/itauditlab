# Canlı teslim — 13 Ekim 2026

**CISA: Gerçek Bir IT Denetçisi Olabilir misin? 🎯 — ID 28**

Canlı veritabanına 100 soru kaydedildi. Domain 1–5 sırasında her bölümde 20 soru var. Sesli soru yok. Tek seçim 20, çoklu seçim 10, sıralama 20, risk kartı 20, boşluk doldurma 10, karar senaryosu 20. Tek seçim içinde 5 doğru/yanlış, çoklu seçim içinde 5 çift eşleştirme bulunur.

100 cevap anahtarı ve öğretici açıklama canlı kayıtlar üzerinden doğrulandı. Cevaplar tam metinlidir; kaynak, link ve sayfa referansı gösterilmez. Kullanıcıya özel yanlış seçenek gerekçesi, gerçek iş yorumu ve boşluk alternatifleri sunulur. Domain sonu doğru sayısı, oran, güçlü/gelişim konuları; finalde beş alanın sonucu ve mesleki ilgiye yönelik ölçülü değerlendirme vardır.

İkinci canlı import 0 yeni soru oluşturdu. Önceki 100 sorunun kimlik, içerik, seçenek, cevap, açıklama, ses ve giriş sesi alanlarının SHA-256 değeri yayın öncesiyle aynı. Hiçbir kullanıcı ilerlemesi, cevap veya XP kaydı silinmedi.

Render 48e95d9: **Live**, sağlık 200. Sunulan web JS dosyası doğrulanan yerel release ile aynı SHA-256 değerinde.

14 backend, 18 Flutter ekran testi başarılı; Flutter analyze temiz. Backend testleri bütün 100 cevabı, sıralı metin anahtarını, çoklu seçimi, yanlış sırayı, alternatif metni, kaldığı yerden devamı, yanlışla ilerlemeyi, bölüm özetlerini, veri çoğalmamasını ve diğer yolların korunmasını sınadı. Flutter testleri ilk altı türü, doğru/yanlışı ve eşleştirmeyi telefon genişliğinde sınadı. CISA kartına dokunma ve Başla ara ekranını atlama widget testleriyle doğrulandı. Önceki yolun ses ve renderer testleri de geçti.

Canlı hesaptaki manuel kart tıklaması için uygulama girişi bekleniyor. Güncellenmiş web sürümü hazır ve yayında. Native iOS/Android doğrudan açılış ve özet davranışı için yeni uygulama sürümü gerekir; kaynak hazır, mağaza dağıtımı bu görevde yapılmadı. Yeni içerik ve metin açıklaması mevcut native soru tipleriyle uyumludur.

## Değişiklikler

- content/learning-paths/cisa-auditor-simulator/build_content.py, package.json: özgün içerik ve deterministik paket.
- SOURCE_ANALYSIS.md: ana kitap incelemesi, 2019/güncel kapsam farkı, soru tipi eşlemeleri.
- QUALITY_REPORT.json, LIVE_REPORT.json: içerik/test/canlı kontrol raporları.
- mobile_api/cisa_simulator.py: sınırlandırılmış import, tam anahtar, kişisel geri bildirim, bölüm/final özeti.
- mobile_api/management/commands/seed_cisa_auditor_path.py: varsayılan dry-run ve --apply.
- mobile_api/migrations/0033_cisa_auditor_simulator.py: şema değişmeden yayın, tersine işlemde yalnız gizleme.
- mobile_api/views.py: yalnız CISA için 20 soruluk bölüm oturumu, aktif oturuma dönüş, yanlışla ilerleme, XP kaybetmeme.
- mobile_api/test_cisa_simulator.py: içerik, değerlendirme, ilerleme ve izolasyon.
- mobile/lib/main.dart: doğrudan açılış ve bölüm özeti.
- mobile/test/cisa_simulator_test.dart: kart/başlama ve tip render testleri.
- mobile_web/dist: doğrulanan Flutter web release.

## Güvenli yeniden çalıştırma

```sh
python manage.py seed_cisa_auditor_path
python manage.py seed_cisa_auditor_path --apply
```

Varsayılan dry-run; ikinci komut canlıda da idempotent olarak doğrulandı. Rollback veri silmez: yalnız slug registry ile doğrulanan yolun published alanı kapatılır; önceki Render sürümüne kod dönüşü mümkündür. Ayrıntı README.md içinde.
