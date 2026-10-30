# Ders videosu pencereleri

Ders alt videoları ve kapaktaki video artık statik Bootstrap arka planı kullanır: dışarı tıklamak kapatmaz. Kapat düğmesi ve Escape kullanılabilir. Her iki giriş yolu aynı pencere davranışına sahiptir.

Önceki iki ayrı iframe sıfırlama akışı bu pencerelerden çıkarıldı. Oynatıcı ilk açılışta yüklenir, kapanırken Player.js ile duraklatılır; iframe sayfada kaldığı için yeniden açılışta konum korunur. Otomatik oynatma kapalıdır. Bu değişiklik sayfa yenilemeleri veya cihazlar arasında izleme konumu eşitlemez ve yeni bir izleme geçmişi kaydetmez. Diğer pencerelerin davranışı korunur.

16:9 video alanı, ekran yüksekliği sınırı, mobil kenar boşlukları ve kontrastlı 44 piksel kapatma düğmesi eklendi. Arayüz gerçek Django şablonundan masaüstünde ve 390×844 mobil ölçüsünde kontrol edildi; dışarı tıklamada açık kaldığı ve yeniden açılışta iframe kaynağının korunduğu doğrulandı. Görsel kontrolde örnek oynatıcı kullanıldı; gerçek ders videosu izlenmedi.

Doğrulama: `node --test tests/course-video.test.cjs` (4 test), `core.tests` (15 test, standart statik dosya deposuyla). SDK hazır olmadan kapatma ve SDK yüklenememesi durumları da kapsanır.
