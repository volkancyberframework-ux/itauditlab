# Siberkobi katılım talepleri — ödeme alınmaz

## Aktif akış

`/siberkobi-cip/` e-posta ve çip adedi alan bir talep formudur. Yeni kayıt **beyan edilen katılım talebidir**, ödeme onayı veya kesin ortaklık kaydı değildir. Form bunu gönderimden önce açıklar; sonuç ekranı, e-posta ve Telegram mesajı da aynı durumu belirtir.

- Yeni talep: `POST /siberkobi-cip/talep/live/`.
- Özel sonuç: `/siberkobi-cip/sonuc/<rastgele-UUID>/`.
- Aynı e-posta birden fazla talep oluşturabilir. Bir talepte birden fazla çip seçilebilir.
- Her çip talebi bir sıra tüketir. Aynı kişinin birden fazla çipi varsa oranları toplanır.
- Dönem başına 43 çip talebi, formun gönderilip veritabanına kaydedildiği sırayla numaralanır. Bu sıra **ödeme sırası değildir**.
- İlk üç sıra için %0,50 / %0,25 / %0,25; sonraki 40 sıra için ilk görseldeki geometrik formül kullanılır. Formülün 4. sıra sonucu %0,10150026’dır. Tam dağıtım %2 olacak şekilde 20 basamakla saklanır; ekranda 8 basamak gösterilir.
- Talep sayacı ve kayıtlar `ChipRequestRound` / `ChipParticipationRequest` tablolarındadır. Eski `ChipCampaign` / `ChipPurchase` ödeme defteri değiştirilmez.

## Ödeme kaldırıldı

Bu özellik için ödeme butonu, ücret gösterimi ve Stripe yönlendirmesi kaldırılmıştır. Eski `/checkout/<mode>/` ve `/webhook/<mode>/` adresleri 410 döndürür; Stripe API çağrısı yapmaz. Yeni form için Stripe anahtarı veya webhook gerekmez. `CHIP_LIVE_PAYMENTS_ENABLED` bu formu etkilemez ve eski ödeme URL’sini açmaz. Önceki ödeme kayıtları yalnızca geçmişi korumak için tutulur.

E-posta tek başına ödeme kanıtı sayılmaz. Bu form geçmiş ödemeleri e-posta adresiyle aramaz, başka bir kişinin özel kaydını açıklamaz ve girilen e-postanın sahibini doğruladığını iddia etmez. Her yeni talep yeni ve tahmin edilemez bir sonuç bağlantısı üretir.

## Bildirimler

Katılımcıya talep sırası/adet/geçici pay ve özel bağlantı e-postayla gider. Yönetici Telegram mesajında açıkça “KATILIM TALEBİ — ÖDEME DOĞRULANMADI” durumu görülür. E-posta ve Telegram başarı zamanları ayrı tutulur; başarısız bildirimler yönetim panelinden ve günlük görevden tekrar denenir.

`python manage.py reconcile_siberkobi_chips` artık yalnızca bekleyen **talep bildirimlerini** dener; ödeme almaz ve Stripe’tan ödeme kontrolü yapmaz. Normal tekrar gönderimlerinde aynı bildirim yeniden üretilmez; harici sağlayıcı kabulü ile yerel kayıt arasındaki çökme aralığında mutlak exactly-once garantisi verilemez.

## Yönetim ve sıfırlama

- Talepler: `/bulamazsinki/landing/chipparticipationrequest/`.
- Talep dönemleri ve formu kapatma: `/bulamazsinki/landing/chiprequestround/`.
- Sıfırlama/arşivleme: `/bulamazsinki/landing/chiprequestround/archive/`.

Yalnızca süper kullanıcı CSRF korumalı formda “TALEPLERİ ARŞİVLE” onayıyla yeni dönem başlatabilir. Eski kayıtlar silinmez, eski sonuç bağlantıları arşiv durumunu gösterir ve eski form sekmeleri yeniden gönderilemez. Gerçek ödeme kayıtları ve onaylanmış hak sahipliği sayacı değişmez. Test talepleri ayrı bir dönemdedir.

43 sınırı PostgreSQL satır kilidiyle; tekrar gönderim ise dönem ve tarayıcıya verilen nonce üzerindeki benzersiz kısıtla korunur. CSRF, geçerli e-posta/adet kontrolü ve IP/e-posta başına istek sınırlaması uygulanır. Yeni sonuç sayfasında yalnızca mevcut talep ve öncekiler görünür; önceki e-postalar maskelidir. Özel bağlantı önbelleğe ve arama motoruna kapalıdır.
