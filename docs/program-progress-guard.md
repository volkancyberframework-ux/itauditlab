# Programa özel ilerleme uyarısı

Yönetim > Core > Program enrollments: ilgili öğrenci/program kaydında **Önceki ders uyarısı ve ilk ihlalde hesap kapatma** kutusunu seçip kaydedin. Liste ekranından da değiştirilebilir. Mevcut kayıtların tamamında varsayılan kapalıdır; bu özellik yayınlandığında kimsenin hesabı kendiliğinden kapatılmaz.

## Öğrenci akışı

- Her yeni web oturumunda öğrenci panelinde veya ders sayfasında giriş uyarısı gösterilir. “Anladım” yalnızca oturumdaki uyarıyı okundu işaretler; ihlal oluşturmaz.
- Takvim ve otomatik ders açılışı değişmez. Önceki çalışmalar erişilebilir kalır.
- İşaretli aktif programın açılmış yeni dersine kayıt/ilk erişim sırasında daha önce açılmış, zorunlu ve muaf olmayan derslerin doğrulanmış eksik tamamlama kayıtları kontrol edilir. Sıra gün, adım sırası ve ID ile belirlenir. Başka programlar ve daha önce başlanmış dersler bu işlemi tetiklemez.
- **LessonEvidence.completion_known=True ve completed_at boş** ise önceki ders doğrulanmış eksik sayılır. Tamamlama durumu bilinmeyen kayıt yaptırım doğurmaz. Otomatik kayıt, görüntüleme veya mevcut izleme panelindeki erişim yüzdesi gerçek tamamlamanın kanıtı olarak kullanılmaz. Önceki dersi tamamladıysa yönetici Öğrenci İlerlemesi ve Müdahale ekranından tamamlanma kanıtını güncellemelidir.
- İkinci uyarı ders listesini, vazgeçme bağlantısını ve açık bir onay kutusunu içerir. **İlk ihlalde kapatma** öğrenci tarafından özellikle seçildi; 3 ihlal sayacı yoktur.
- Öğrenci kutuyu işaretleyip “Uyarıya rağmen devam et” gönderirse ana kullanıcı is_active=False olur, mevcut web oturumu kapatılır, JWT yenileme anahtarları kara listeye alınır. Ana site/mobil kimlik doğrulaması aynı kullanıcı aktiflik kontrolüne tabidir. Ayrı kullanıcı tablosu olan Denetim Konsolu bu özelliğin kapsamına girmez. Ders, program, ödeme ve geçmiş kayıtları silinmez.

Onay kullanıcıya, derse, uyarı sürümüne ve eksik derslerin anlık listesine imzayla bağlıdır; 30 dakika geçerlidir. Kutu işaretlenmeden veya imza/CSRF doğrulanmadan kapatma yapılamaz. Tamamlama kanıtı veya program işareti değişirse eski onayla kapatma yapılmaz. Tekrarlanan istekler aynı ihlali çoğaltmaz; kullanıcı satırı işlem içinde kilitlenir.

## Telegram ve sabah raporu

İşlem tamamlanınca mevcut yönetici Telegram kanalına “🚨 ALARM ALARM ALARM — ANLIK PROGRAM İHLALİ” gönderilir. Kullanıcı e-postası, hedef Course ID/adı, program kayıt ID’si, eksik dersler, Türkiye saati ve ihlal kayıt numarası yer alır. Gönderim hatası hesap durumunu geri almaz; olay veritabanında korunur, sır/gönderim URL’si loglanmaz.

Mevcut 05.00 Türkiye saati run_daily_programs komutu, o sabah 05.00 öncesinde oluşmuş, henüz bildirilmeyen olayları ayrı sabah mesajı olarak gönderir. Başarısız anlık bildirimler de yeniden denenir. Başarı zamanı ancak Telegram API ok=true dönerse kaydedilir. Mevcut ders/PDF/KPI/görüşme/haftalık raporların içerikleri değiştirilmedi.

İhlal kayıtları yönetimde **Program ilerleme ihlalleri** bölümünde salt okunur görünür. Kayıt e-posta ve ders/program bilgilerini anlık görüntü olarak korur. Yeniden açma için kullanıcı yönetiminden hesap etkinleştirilmeli, tamamlanma kanıtları ve program uyarı işareti değerlendirilmelidir; otomatik geri açma yapılmaz.

İade/cayma metni satın almada onaylanan sözleşmeye bağlantı verir; her öğrenci için koşulsuz bir “yasal hakkınız yoktur” iddiası oluşturmaz.

## Doğrulama

22 yeni akış/güvenlik testi ve ilgili giriş, program takvimi, izleme, PDF, haftalık rapor ve mobil KPI testleriyle toplam 121 test geçti. Önceden ilk girişe yönlenen izleme testi kullanıcısının fixture’ı normal öğrenci oturumunu yansıtacak şekilde düzeltildi. İki uyarı ekranı gerçek şablonlardan örnek verilerle görsel olarak incelendi. Canlı öğrenci hesabında kapatma denemesi veya gerçek Telegram test alarmı yapılmadı.
