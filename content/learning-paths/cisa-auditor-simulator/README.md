# CISA Denetçi Simülasyonu

100 özgün Türkçe soru, beş Domain × 20. Ses yok. Cevap ekranlarında kaynak/sayfa referansı yok.

## İçeri aktarma

```sh
python manage.py seed_cisa_auditor_path
python manage.py seed_cisa_auditor_path --apply
```

İlk komut dry-run, ikinci komut yazmadır. Yeni yol slug registry ile bulunur; kullanıcı kayıtları veya başka yollar silinmez. Aynı paket ikinci kez kayıt oluşturmaz. Kayıtsız aynı başlık, değişmiş içerik, farklı cevap kaynağı veya bozuk ilişkilerde yazma engellenir.

`0033_cisa_auditor_simulator` veri migration'ı standart Render migrate adımında yayımlar. Şema değişikliği yok. Normal uygulama rolleri/üyelik erişimi korunur.

## Kullanıcı akışı

Güncellenmiş Flutter web sürümünde kart doğrudan görev ekranını açar. Aktif oturum varsa ilk cevaplanmamış göreve dönülür. Her oturum aynı Domain'in en fazla 20 sorusunu içerir. Yanlışlar da ilerletir, XP düşürmez; başarı gerçek doğru sayısıyla hesaplanır. Bölüm sonunda özet ve sonraki Domain düğmesi, sonunda beş yetkinlik özeti vardır. Diğer yolların davranışı korunur.

Native iOS/Android uygulamasının bu yeni doğrudan açılış ve özet görünümünü alması için yeni Flutter uygulama sürümü dağıtılması gerekir. Sunucu içeriği ve cevap açıklaması mevcut native renderer'larda çalışır; web dağıtımı bu kaynaklarla birlikte hazırlanır. Bu görev App Store yayını yapmaz.

## Geri alma

Uygulama kodu Render'ın önceki başarılı sürümüne döndürülebilir. İçeriği güvenle gizlemek için yalnız registry ile doğrulanan yolun `published=False` yapılması yeterlidir. Migration reverse bunu yapar; soru, cevap, XP ve ilerleme silmez. Yeniden ileri migrate veya `--apply` aynı yolu tekrar görünür yapar.

## Dosyalar

`build_content.py`: özgün vaka kaynakları ve editoryal ikinci geçiş.
`package.json`: deterministik uygulama paketi.
`SOURCE_ANALYSIS.md`: kitap/güncel kapsam farkı ve tip eşlemeleri; kullanıcı cevap ekranına aktarılmaz.
`QUALITY_REPORT.json`: dağılım ve her sorunun kontrol kaydı.
`mobile_api/cisa_simulator.py`: importer, tam cevap anahtarı ve özet.
`mobile_api/views.py`: yalnız bu yola özgü oturum/ilerleme davranışı.
`mobile/lib/main.dart`: doğrudan açılış ve özet gösterimi.

Testler: backend içerik/cevap/ilerleme/yinelenmeme/izolasyon; Flutter altı tip, doğru/yanlış ve eşleştirme görünümü. Önceki yolun ses ve renderer testleri de çalıştırıldı.
