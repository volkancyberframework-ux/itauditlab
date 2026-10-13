# Flutter, PWA ve ses kayıtları — 13 Ekim 2026

Canlı web/PWA: app.grcustasi.com. Son runtime commit: 710737b1a5203ac2b6b60d377c8709f9dd7060bc. İlk yayın 574a93b5c37d87d988fe7ea08fe268a09b99e851, 2m39s sonunda Live.

Flutter'da ortak QuestionImagePreview ve FullscreenImageViewer eklendi. Yetkili NetworkImage aynı provider ile önizleme ve tam ekranda kullanılır; 220px önizleme, çift dokunma, InteractiveViewer pinch/pan, wheel, zoom +/−, fit/reset, ESC/kapatma ve hata/yeniden deneme vardır. Viewer yeni route açtığı için soru durumu ve seçili cevap korunur. Mobil renderer tüm soru görsellerinde bu bileşeni kullanır. Flutter widget/regression testleri 20/20 geçti. Ek pan doğrulamasıyla viewer testleri yeniden geçti. Analyze temiz. Web release ve iOS release (codesigning kapalı) başarılı. App Store / Google Play'e yeni bir native mağaza sürümü gönderilmedi; mevcut mağaza uygulamaları ancak yeni mağaza sürümüyle bu kodu alır.

PWA: yükleme butonu canlı; Chrome/Android beforeinstallprompt varsa native istemi çağırır, diğer tarayıcılara yükleme rehberi verir. iPhone Safari Paylaş → Ana Ekrana Ekle rehberi gösterilir. Standalone/yüklü görünümde buton gizlenir. Manifest id/scope/start_url '/', standalone, Türkçe; 192/512 any ve maskable ikonlar. Service worker kendi sürümlü önbelleğini kullanır; online dosyaları öncelikle ağdan alır. API, media, bearer istekleri önbelleğe alınmaz. Offline açılış derslerin bağlantı gerektirdiğini gösterir. Root SW scope '/' header doğrulandı. Fiziksel iPhone/Android'de ana ekran kurulumu yapılmadı; Chrome fixture'da Android istemi, iPhone rehberi, ESC ve yüklü buton gizleme test edildi. Canlı buton Chrome'da görüldü. Root/manifest/SW/ikon/JS HTTP200; SWv2 baytları yerel sürümle aynı.

Sesler: /Users/volkanguler/Desktop/cases/mp3_1_2x içindeki 19 doğrulanmış 1,2× MP3 tek ZIP/multipart işlemle mevcut Django admin yetkileri ve CSRF üzerinden yüklendi. Ses verileri GitHub deposuna eklenmedi. ses1–ses18 mevcut ID22–39'da dolduruldu. Tanıtım yeni ID40'ta oluşturuldu. Question.audio/intro bağlantıları değiştirilmedi. Dosyalar özel kalıcı storage'da içerik hash'li adlarla saklandı; eski dosyalar silinmedi. 19 SHA256 yerel dönüşüm raporuyla eşleşti. Sonraki yeniden dağıtımın yeni instance'ında aynı 19 dosya yeniden okunarak kalıcılık doğrulandı.

Toplu işlem tüm ZIP adlarını, dosya sayısını, boyut/MP3 başlığını, SHA256'yi, 1,2× süre oranını ve benzersiz mevcut title'ları önce doğrular. İkinci yükleme aynı kaydı çoğaltmaz. Değişiklikler DB transaction içinde; eski adlar özel rollback manifestinde saklanır. restore_batch('rollback-<sha256>.json') yalnız mevcut dosya beklenen yeni dosyayla eşleşirse geri alır. Her değişiklik standart Django admin log'una işlendi. Form: /bulamazsinki/mobile_api/audioasset/bulk-recordings/.

Doğrulamalar: 15 Django testi (audio import/rollback/izin, mevcut web/AD akışı, PWA manifest/worker); 20 Flutter testi; 3 Node service-worker testi. Tüm ilgili kontroller başarılı. Öğrenme yolu26=100, yol28=100, AD yol30=75; eski 200 sorunun SHA256'si aynı: 755f65c1cf1ba7e5b97f63f37bf756e3fb89f88b7eb1ffe534347b039ad18e76. Son okuma cevap101, XP97, ilerleme12; kullanıcı aktivitesi korunmuştur.

Birincil platform belgeleri:
- https://api.flutter.dev/flutter/widgets/InteractiveViewer-class.html
- https://web.dev/learn/pwa/installation-prompt
- https://support.apple.com/en-eg/guide/iphone/iphea86e5236/ios
