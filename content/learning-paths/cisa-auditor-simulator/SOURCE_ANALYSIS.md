# Kaynak ve kapsam analizi — 13 Ekim 2026

Ana kaynak: kullanıcı tarafından sağlanan CISA Review Manual, 27th Edition, ISACA, 2019; ISBN 978-1-60420-767-5. PDF 992 sayfa, metin okunabilir. Kitabın içindekiler bölümü ve denetim kanıtı, örnekleme, raporlama, yönetişim, risk yönetimi, hizmet sağlayıcıları, iş gerekçesi, test, veri taşıma, BIA, yedekleme, DR, IAM, sınıflandırma ve kriptografi açıklamaları incelendi. `tmp/pdfs/cisa.txt` mevcut metin çıkarımı, asıl PDF ile başlık/baskı kontrolü yapıldı.

Ek `dump.pdf` 942 sayfa ve 1.332 soruluk sınav soru bankası etiketi taşıyor. Bu dosyadaki soru ve cevaplar içeriğe aktarılmadı; teknik doğruluk için ana kitap ve resmî kapsam kullanıldı. Üretilen bütün kurumlar, kişiler, işlem kayıtları ve vakalar kurgusaldır.

## Beş alan

1. Denetim süreci: etik, bağımsızlık, yetki, iş süreçleri, kontrol türleri, risk ve önemlilik, planlama, uzman kullanımı, örnekleme, kanıt, veri analizi, çalışma kâğıdı, raporlama, kalite ve takip.
2. Yönetişim ve yönetim: stratejik uyum, kurul/yönetim ayrımı, politika, organizasyon ve görev ayrılığı, mimari, risk sahipliği ve yanıtları, kaynak ve yatırım yönetimi, dış kaynak/bulut sorumluluğu, performans, kalite.
3. Edinim ve geliştirme: proje yönetimi, iş gerekçesi, gereksinimler, SDLC/çevik çalışma, kontrol tasarımı, test türleri, kabul, sürüm kimliği, veri dönüşümü, geçiş, geri dönüş ve uygulama sonrası fayda.
4. Operasyon ve dayanıklılık: varlıklar, toplu işler, arayüzler, kullanıcı uygulamaları, kapasite, olay/problem, yama ve değişiklik, hizmet düzeyi, veri bütünlüğü, BIA, yedek/restore, BCP/DR, RTO/RPO ve tatbikat.
5. Varlık koruma: veri sınıflandırma, fiziksel kontroller, IAM, ayrıcalık ve işten ayrılma, ağ ayrımı, şifreleme/anahtar, sertifika, bulut yapılandırması, mobil cihaz, DLP, farkındalık, güvenlik testleri, izleme, müdahale ve adli kanıt.

## Baskı farkı

2019 kapsam ağırlıkları: 21/17/12/23/27. Güncel resmî ISACA kapsamı 18/18/12/26/26; Domain adları/sırası korunuyor. Güncel yapıda mahremiyet ve veri yönetişimi/sınıflandırma Domain 2'de açık alt başlıklar; Domain 4'te operasyon logları, gölge IT ve kullanıcı uygulamaları daha açık adlandırılıyor. Bu paket sınav ağırlığı taklidi değildir: kullanıcı isteği doğrultusunda her alanda eşit 20 özgün mesleki vaka bulunur. Kitabın prensipleri esas alındı; çağdaş bulut/DevOps ortamlarına uygulandı. Mahremiyet yönetişimi D2, teknik sınıflandırma ve erişim D5 olarak ayrıldı.

Resmî doğrulama: https://www.isaca.org/credentialing/cisa/cisa-exam-content-outline (13 Ekim 2026). Bu belge geliştirme içindir. Kaynak adı, bağlantı ve sayfa numarası cevap ekranlarına eklenmez.

## Tasarım ve eşleme

Her Domain 6 başlangıç, 8 orta, 6 ileri soru içerir. Tek/çoklu seçim, sıralama, risk kartı, boşluk ve karar senaryosu dönüşümlü gelir. Beş doğru/yanlış → `choice`; beş iki doğru çift eşleştirmesi → `multi_select`. Ayrı eşleştirme widget'ı veya yeni enum eklenmedi. Görsel/ses alanı ve sesli yanıt kullanılmaz; kanıtlar okunabilir metin olarak bağlamda bulunur. `info` cevaplı soru değildir; `text` serbest profesyonel rubriği mevcut otomatik değerlendirmeye uygun olmadığından kullanılmadı.

Her seçeneğe ayrı gerekçe yazıldı. Cevap anahtarı değerlendirmede kullanılan aynı ID/metin listesinden oluşturulur. Sıralama bütün adımları, eşleştirme iki tarafı, çoklu seçim tüm doğruları, boşluk alternatifleri tam gösterir.

İlerleme bu yolda cevaplanan soruyla ilerler, yanlışlar eğitim geri bildirimi alır. Başarı özeti gerçek son denemelerin doğruluğundan hesaplanır. Diğer yolların doğru-cevapla ilerleme kuralı korunur. Domain geçişi, mevcut bölümün 20 görevi bitince gerçekleşir. Aktif oturum tekrar açılır; cevaplanmamış ilk göreve dönülür.
