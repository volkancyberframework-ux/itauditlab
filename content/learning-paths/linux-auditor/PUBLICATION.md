# Yayın kapsamı

- Linux: 80 soru / 80 görsel, 5×16 bölüm, native ve web premium listesi.
- 0036 migration mevcut ücretli üyelere ilerleme kaydı açar. Gelecekte ücretli olan hesaplar ortak yayın sayesinde otomatik erişir.
- CISA, CISM, GRC 80 saat, OT ve eski /kamplar/ checkoutları, sunucuda tutulan ödeme tutarı/döviz/session kaydıyla ömür boyu üyelik hakkını bağlar.
- Mevcut /mobiluygulama/webhook Stripe checkout.session.completed ve async_payment_succeeded bildirimlerini imza ve mod doğrulamasından sonra işler. Mevcut endpoint bu olayları almaya devam etmelidir. Ana program ödeme dönüşü ayrıca sunucu Stripe API'sinden doğrulama yapar; sorgu parametresinden ödeme veya kimlik kabul edilmez.
- Travel kendi imzalı ödeme endpointinde üyeliği tanımlar. Eski ödeme linki kullanılıyorsa aynı doğrulanmış Travel callback gerekir.
- E-posta normalize edilerek var olan hesap eşleştirilir. Birden çok veya devre dışı hesapta otomatik işlem reddedilir. Yeni hesapta rastgele ilk şifre, zorunlu değişim ve e-posta doğrulama korunur. Üyelik e-postası hatası üyeliği geri almaz; yönetim panelinde yeniden denenebilir.
- Skool websitesi metni: tek seferlik 249 USD. Skool hizmetinin kendi fiyat ayarı değiştirilmez.

Önceden yapılmış farklı bootcamp ödemeleri için toplu geriye dönük hak tanımlaması bu yayının parçası değildir. Mevcut ücretli mobil kullanıcıların Linux erişimi bu sınırlamadan etkilenmez.
