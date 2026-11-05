# Siberkobi e-posta ile yaklaşık sıra kaydı

`/siberkobi-cip/` yalnızca ödeme sırasında kullanılan e-posta adresini alır. Kullanıcıdan çip adedi istenmez; istemcinin quantity parametresi yok sayılır ve her yeni kayıt bir yaklaşık sıra oluşturur. Önceden oluşturulmuş çoklu kayıtlar değiştirilmez.

Sayfa, sonuç ekranı ve kayıt e-postası şu açıklamayı kullanır: “Kesin pay tutarınız size e-posta olarak gönderilecektir. Bu sistem yalnızca yaklaşık sıranızı gösterir. Ödeme sistemi üzerinden doğrulama yapıldıktan sonra final liste paylaşılacaktır.”

Ekranda ve genel durum yanıtında hesaplanan yüzde gösterilmez. Bu sürüm ödeme doğrulaması veya final pay dağıtımı yapmaz; doğrulama ve kesin listenin gönderimi ayrı bir süreçtir. Kayıt e-postası yalnızca yaklaşık sıra bilgisidir. Telegram mesajı da ödeme doğrulanmadığını belirtir. Eski pay hesapları geçmişi korumak için veritabanında tutulur, kesinleşmiş pay olarak sunulmaz.

Ödeme alma ve Stripe yönlendirmesi kaldırılmıştır. Önceki `/checkout/<mode>/` ve `/webhook/<mode>/` adresleri ödeme başlatmaz. Gerçek ödeme defteri ve onay sayacı değişmez.

- Kayıtlar: `/bulamazsinki/landing/chipparticipationrequest/`.
- Formu açma/kapatma: `/bulamazsinki/landing/chiprequestround/`.
- Dönemi arşivleyip sayacı sıfırlama: `/bulamazsinki/landing/chiprequestround/archive/` (süper kullanıcı, yazılı onay, CSRF).

Arşivleme eski kayıtları silmez. Eski sekmelerden yeni döneme kayıt gönderilemez. 43 sıralık dönem sınırı, PostgreSQL satır kilidi, tekrar gönderim koruması, e-posta kontrolü ve istek sınırı korunur. Her sonuca özel rastgele UUID bağlantısı üretilir; önceki e-postalar maskeli gösterilir. Genel durum yanıtı veya yalnızca e-posta adresiyle geçmiş özel kayıtlar aranmaz.

`python manage.py reconcile_siberkobi_chips` mevcut günlük görev üzerinden yalnızca bekleyen kayıt e-postası ve Telegram bildirimlerini tekrar dener; kesin pay e-postası göndermez. Kesin payın ve final listenin ayrıca doğrulanıp hazırlanması gerekir.
