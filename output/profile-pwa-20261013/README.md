# Profil yükleme kartı, Safari rehberi, iPhone kurulumu ve login temizliği

13 Ekim 2026. Son canlı runtime: b6e086b042144a7f22a6b8873aeabd0f2bf68567; Render Live, 2m17s. Giriş öncesindeki yüzen yükleme butonu kaldırıldı. Web'de giriş sonrası yalnız Profil seçenekleri içinde, mevcut Card/ListTile tasarımına uygun Uygulamayı yükle kartı var. Native uygulamada ve standalone PWA'da kart gösterilmez.

Dart web interop profil dokunuşundan doğrudan grcPwaInstall çağırır; Chrome/Android beforeinstallprompt mevcutsa user gesture içinde prompt çalışır. iPhone'da Safari son yükleme onayını programatik web butonundan vermez: profil kartı güncel Page Menu/Paylaş/Ana Ekrana Ekle rehberini açar. Rehber bunun Safari menüsü olduğunu açıkça belirtir ve Safari menüsüne erişmeden önce rehberi kapatan gerçek bir düğme sağlar. Adres kopyalama ayrı, çalışan bir düğmedir. Safari yolu iOS kullanıcı aracında beforeinstallprompt olsa bile önceliklidir. JS köprüsü yüklenemezse Flutter Türkçe fallback sheet gösterir; buton tepkisiz kalmaz.

8 Flutter profil/regression testi, analyze ve release web build başarılı. 2 PWA backend testi başarılı. Chrome'da gerçek derlenmiş Flutter web ile yerel, tamamen sahte API/hesap üzerinden giriş→Profil→kart→Safari rehberi, rehber kapatma ve Android prompt callback akışı doğrulandı. Giriş öncesi yükleme butonu yok. 390×844 görünüm ekranları profile-card.jpg ve iphone-guide.jpg dosyalarında. Fiziksel Safari üzerinden PWA ana ekran ekleme işlemi tarafımızdan yapılmadı; kullanıcı Safari kullandığını belirtti, rehber Apple belgelerine göre düzenlendi.

Kullanıcının bağlı fiziksel iPhone'una flutter run --release --no-pub ile güncel kaynak derlendi, mevcut geliştirme imzasıyla yüklendi ve açıldı. Xcode 19.4s, yükleme/açma 5.3s. DeviceCtl sadece GRC Ustası bundle ID'siyle sorgulandı; kurulu 1.0.1 (7) doğrulandı. Flutter bağlantısı detach edilerek uygulama durdurulmadı. Cihazdaki kurulum App Store yayını değildir. Mağaza sürümü gönderilmedi. Cihaz kimliği ve provisioning bilgileri bu rapora eklenmedi.

www.grcustasi.com/login/ sayfasının hem giriş kartındaki mobil tanıtımı hem alttaki _mobile_promo dahil etmesi kaldırıldı; App Store ve Google Play logolarının tamamı bu sayfadan çıkarıldı. İlk düzenlemede footer dahil etmesi kalmıştı; gerçek HTML kontrolüyle saptandı ve düzeltildi. Lokal render_to_string ve canlı anonymous HTTP200 HTML doğrulaması: appstore.svg, playstore.svg ve grc-store-badges yok; e-posta/parola alanları mevcut. Diğer sayfaların logoları değişmedi.

Canlı kontrol: login HTTP200, app healthz HTTP200; canlı pwa.js baytları yerel kaynakla aynı; canlı main.dart.js SHA256'si yerel release build ile aynı. Soru, ses, kullanıcı cevapları ve XP modellerinde değişiklik yapılmadı.

Apple rehberi: https://support.apple.com/en-eg/guide/iphone/iphea86e5236/ios
