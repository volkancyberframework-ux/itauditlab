# Siberkobi çip katılımı

## Mevcut durum

Uygulama gerçek tahsilata kapalı hazırlanmıştır. Test ve gerçek ödeme defterleri ayrıdır. Mevcut eğitim ödemelerinin Stripe anahtarları kullanılmaz. Gerçek hisse/kâr payı içeren işlem, ödeme sağlayıcısına yalnızca dijital topluluk erişimi olarak tanıtılmaz. Ürün adı ve Stripe açıklaması gerçek niteliği açıklar.

- Paylaşılacak tek adres: `/siberkobi-cip/`.
- Test adresi: `/siberkobi-cip/test/`.
- Yönetim: `/bulamazsinki/landing/chipcampaign/`.
- Kayıtlar: `/bulamazsinki/landing/chippurchase/`.
- Test sıfırlama: `/bulamazsinki/landing/chipcampaign/test-reset/` (yalnızca süper kullanıcı, CSRF ve yazılı onay).

## Stripe test kurulumu

1. `python manage.py migrate --noinput`.
2. Ortamda `CHIP_STRIPE_TEST_KEY` ve `CHIP_STRIPE_TEST_WEBHOOK_SECRET` tanımlanır. İkisi de Stripe test ortamına ait olmalı.
3. Test webhook hedefi: `https://www.grcustasi.com/siberkobi-cip/webhook/test/`.
4. Olaylar: `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.expired`.
5. Yönetimde **Test** kampanyasında “Bağlantı açık” işaretlenir.
6. Stripe'ın test kartıyla, Stripe test ekranında ödeme denenir. Gerçek kartla gerçek ödeme yapılmaz. Test bildirimleri açıkça `[TEST]` etiketlidir; ödeme e-postasına ve mevcut yönetici Telegram hedefine gider.

## Tahsis ve kapasite

39900 euro cent, tek adet, kartla ödeme; fiyat ve ürün açıklaması sunucuda belirlenir. Ödeme Stripe'tan doğrulanmadan sıra/pay oluşturulmaz. Sıra, ödemenin uygulamada doğrulanıp veritabanına kaydedildiği sıradır; ödeme oturumu açılış sırası değildir. Sağlayıcının geciken olaylarının evrensel kronolojik sırası vaat edilmez. Kampanya satırına PostgreSQL `SELECT FOR UPDATE` kilidi ve benzersiz sıra/session/payment-intent kısıtları uygulanır.

İlk üç pay yüzde 0.5, 0.25, 0.25. Sonraki 40 pay görseldeki formülle 20 ondalık basamakla saklanır; son payda yalnızca 20 basamak yuvarlama artığı düzeltilerek toplam tam %2 tutulur. Gösterim 8 basamaktır. Görselde 4. sıra %0,10150018 yazsa da formül %0,10150026 verir; formül esas alınmıştır. Üretim veritabanı PostgreSQL NUMERIC olmalıdır; SQLite'ın kayan noktalı saklaması finansal defter için uygun değildir.

43 kontenjan, onaylanmış ödemeler **ve** açık Stripe oturumları birlikte sayılarak korunur. Açık oturum 31 dakika tutulur. Bir yer, yalnızca doğrulanmış `expired` Stripe durumu/olayıyla bırakılır; yerel süre geçmesi tek başına yeterli değildir. İlk Stripe yanıtı kaybolursa aynı idempotency anahtarı tekrar kullanılabilir. Mutabakat görevi kayıp yanıtta Stripe oturumlarını metadata ile tarar. Belirsiz ödemeler kontenjanı tüketmeye devam eder; ikinci ödeme istenmez.

Her başarılı 399 EUR ödeme bir çip/katılımdır; aynı e-postanın ikinci kez alımına otomatik engel konulmamıştır. İstenirse iş kuralı ayrı tanımlanmalıdır.

Kapatma yeni ödeme başlatılmasını durdurur; daha önce başlatılmış geçerli oturumların başarılı ödemeleri kayıtlanır. Gerçek hakların kesinleşmesi sözleşme/hukuki işlemlere bağlıdır; ekrandaki hesaplama hukuki hisse devri yerine geçmez.

## Bildirim ve mutabakat

Doğrulanan ödeme sonrası katılımcıya sıra/pay/özel sonuç bağlantısı e-postayla gider. Yöneticiye ad, e-posta, sıra, yüzde ve tutar mevcut Telegram botuyla gider. İki kanalın başarı zamanları ayrı tutulur. Normal tekrar olayları ikinci tahsis ya da ikinci bildirim üretmez. Harici SMTP/Telegram kabulü ile yerel kayıt arasındaki çökme aralığında mutlak exactly-once garantisi verilemez.

`python manage.py reconcile_siberkobi_chips` yalnızca mevcut ödemeleri kontrol eder ve bekleyen bildirimleri dener; yeni kart tahsilatı oluşturmaz. Mevcut `run_daily_programs` de bunu çalıştırır. Hızlı operasyon için komut ayrıca çalıştırılabilir. Yönetimde seçili ödemelerin bildirimleri tekrar denenebilir.

Özel sonuç bağlantısı rastgele UUID içerir, arama motoruna ve önbelleğe kapalıdır, referrer göndermez. Kişi kendi ödeme e-postasını açık, önceki kişilerin isim/e-postalarını maskeli görür. Kendisinden sonraki katılımlar özel listesine eklenmez.

## Test sıfırlama

Sıfırlama eski test neslini arşivler, sayacı sıfırlar ve test bağlantısını kapatır. Önceki test ödemeleri/bildirimler silinmez, gönderilmiş e-postalar geri alınmaz. Eski test nesline geç gelen webhook yeni sayaca eklenmez. Stripe'taki test kayıtları aynen kalır. Gerçek ödeme defterini sıfırlayan/silen bir işlem yoktur.

## Gerçek ödeme

Gerekli sağlayıcı uygunluğu ve şirket/katılım metinleri netleştirildikten sonra ayrı `CHIP_STRIPE_LIVE_KEY`, `CHIP_STRIPE_LIVE_WEBHOOK_SECRET`, `CHIP_LIVE_PAYMENTS_ENABLED=True` ve yönetimde **Gerçek ödeme** kampanyasının açık olması gerekir. Webhook hedefi `/siberkobi-cip/webhook/live/`. Varsayılanlar kapalıdır. Sağlayıcı anahtarları dokümana veya kaynak koduna yazılmaz.
