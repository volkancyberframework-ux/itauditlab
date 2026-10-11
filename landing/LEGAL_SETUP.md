# GRC Ustası hukuki yapılandırma

11 Ekim 2026: Kamuya açık sayfalara çerez tercih ekranı, KVKK aydınlatması, gizlilik/çerez politikaları ve tüketici hakları açıklaması eklendi. Veri sorumlusu kullanıcı beyanıyla Volkan Güler — GRC Ustası olarak belirtildi. Hizmet Vietnam'dan yönetiliyor.

## Tamamlanması gereken işletme bilgileri

- Tebligat/yazışma alınabilen tam adres ve iletişim telefonu. Ev adresi kullanılacaksa kamuya açık olacağı bilinmelidir; Vietnam'daki ticari kullanım/kayıt uygunluğu ayrıca doğrulanmalıdır.
- Gerçek hizmet sağlayıcı, ödeme tahsil eden taraf, fatura düzenleyen taraf ve varsa işletme/vergi kayıtlarının eşleştirilmesi.
- Bu bilgiler sağlandıktan sonra ürün/siparişe özel ön bilgilendirme ve mesafeli hizmet sözleşmesi; ödeme öncesi gösterim, sürümlü onay kaydı ve kalıcı veri saklayıcısıyla müşteriye iletim. Genel tüketici bilgilendirmesi bunun yerine geçmez.
- Vietnam'daki işletme/vergi/çalışma ve veri koruma yükümlülüklerinin yerel uzmanla değerlendirilmesi.
- Türkiye'deki hedef müşteriler ve faaliyet kapsamına göre KVKK, VERBİS/temsilci, elektronik ticaret ve ticari elektronik ileti/İYS yükümlülüklerinin değerlendirilmesi.
- Render, Stripe, Skool, Telegram ve Vietnam'dan erişim dahil yurt dışı veri işlemleri için gerçek alıcıların, ülke bilgilerinin ve geçerli aktarım mekanizmalarının belgelenmesi; gereken sağlayıcı sözleşmelerinin tamamlanması.
- Veri türleri için somut saklama takvimi, silme süreçleri ve ilgili kişi başvuru prosedürünün işletmede uygulanması.

## Teknik davranış

- Analitik varsayılan kapalıdır. Sunucu, imzalı ve süresi geçmemiş `grc_consent` çerezini doğrular.
- `grc_vid` yalnızca açık analitik izni sonrası üretilir; ret/geri çekme ile silinir ve yeni ziyaretçi kayıtları durur.
- Tercih 180 gün geçerlidir. Politika sürümü değişince yeniden tercih istenir.
- Kamuya açık landing HTML yanıtları kişiye özel CSRF nedeniyle private/no-store olur.
- Hukuk sayfaları: `/yasal/kvkk/`, `/yasal/gizlilik/`, `/yasal/cerez/`, `/yasal/kullanim/`.

Kaynaklar:
- https://www.kvkk.gov.tr/Icerik/7353/Cerez-Uygulamalari-Hakkinda-Rehber
- https://www.kvkk.gov.tr/Icerik/2033/Aydinlatma-Yukumlulugu-
- https://www.kvkk.gov.tr/Icerik/8142/Kisisel-Verilerin-Yurt-Disina-Aktarilmasi-Rehberi
- https://tuketici.ticaret.gov.tr/yayinlar/tuketici-bilgi-rehberi/mesafeli-sozlesmeler-hakkinda-bilgilendirme

Bu uygulama işletmenin tüm hukuki yükümlülüklerinin tamamlandığı yönünde bir uygunluk belgesi değildir.
