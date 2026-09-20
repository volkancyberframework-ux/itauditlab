# Çok kurumlu denetim konsolu

Bağımsız Django uygulaması; ITAudit ile aynı Git deposunda, aynı Render servisi ve PostgreSQL üzerinde, ayrı kullanıcı ve oturum tablolarıyla çalışır. Kurum adı, logo ve subdomain merkezi admin panelinden yönetilir. Kurum logoları veritabanında saklanır.

Ayrıntılı [kullanım ve Render kurulum kılavuzu](KULLANIM_KILAVUZU.md).

Yerel: `pip install -r requirements.txt`, `python manage.py migrate`, `python manage.py createsuperuser`, `python manage.py runserver 127.0.0.1:8765`.

Üretim: mevcut Render servisi otomatik olarak `/denetim/` yolunu açar. Merkezi yönetim `/denetim/admin/`: mevcut aktif ITAudit süper yöneticisinin e-postası ve ilk kurulumdaki parolası geçerlidir. Yeni veritabanı veya servis oluşturmayın. Wildcard DNS yalnızca kuruma özel subdomain kullanımı için gereklidir.

Test: `python manage.py test`. E-posta ve Telegram tekrar denemeleri: `python manage.py send_notifications`.

Gerçek yayında demo seed komutlarını çalıştırmayın. Mevcut denetim geçmişi migration ile korunur. Yeni son test onayı alanı varsayılan olarak kapalıdır; mevcut değerlendirmeler denetçi onayı bekler. Önceki bulgulara migration günü +30 gün son tarih atanır; gerçek planlara göre düzenleyin.

## Hazır denetimler ve erişim

Merkezi yönetimde **Denetim şablonları** ve **Kontrol kataloğu** bulunur. Migration, Belediye Denetimi (21 kontrol) ve Hastane Denetimi (22 kontrol) başlangıç şablonlarını yükler. Bunlar uyarlanabilir başlangıç kapsamlarıdır; eksiksiz mevzuat kontrol listesi değildir.

**Denetim ekle** ekranında kurum, başlık ve hazır şablonu seçin; aynı ekranda katalogdan ek kontrolleri ve denetim üyelerini/rollerini belirleyin. Kaydedildiğinde şablon kontrolleri denetime bağımsız kopyalanır. Şablon veya katalog sonradan değişse bile mevcut denetimin kontrolleri, yanıtları ve bulguları değişmez. Mevcut denetimde başka şablon seçmek yalnızca eksik kontrolleri ekler; kayıt silmez. Denetçi çalışma alanındaki **Katalogdan ek kontrol seç** bölümü de yeni kontrol eklemek içindir.

Denetçi BT yanıtını beklemeden değerlendirme yapabilir, saha denetimine geçebilir ve test ettiği bulguyu gerekçeyle kapatabilir. Uygun değerlendirme son test onayıyla kaydedildiğinde kontrolün açık bulgusu da kapanır. Kısmen uygun/uygun değil görüşlerinde Tasarım, Uygulama veya Tasarım ve uygulama seçimi zorunludur; uygun görüşte eksiklik seçilmez. Eski değerlendirmeler korunur, tekrar kayıtta yeni doğrulama uygulanır. BT sorumluları aynı denetimde önceki yanıtı silmeden yeni revizyon ekleyebilir.

Üyelikte **Stajyer denetçi görünümü (salt okunur)** işaretlenirse stajyer yalnızca o denetimde tüm denetçi verilerini, özel notları ve geçmişi görür. Değişiklik uçları sunucu tarafında engellenir. İşaretlenmezse mevcut sınırlı stajyer görünümü ve öneri akışı devam eder.

Tüm kullanıcılar (yönetici, denetçi, stajyer, BT ve kurum yöneticisi dahil) ilk erişimde gizlilik sözleşmesini okuyup kutuyu işaretlemeli ve **okudum, anladım** yazmalıdır. Onay zamanı ve metin sürümü hesapta saklanır. Mevcut kullanıcılar da bir kez onay verir. Sözleşme metni `templates/accounts/privacy.html`, sürümü `accounts/privacy.py` içindedir; metin değiştiğinde sürümü de güncelleyin.

Kurum logosunun alfa kanalı korunur; giriş, konsol ve admin logo kapsayıcıları transparandır. Kuruma özel giriş adresinde ve seçili denetimde kurum adı sekme başlığına, logo favicon'a yansır. Genel giriş adresi, kullanıcı/kurum henüz belirlenmediği için genel konsol markasını gösterir.

Yayında mevcut `prepare_console` adımı yeni migration'ları ve statik dosyaları uygular. Bağımsız kurulumda `python manage.py migrate` ve `python manage.py collectstatic --noinput` çalıştırın. Mevcut denetimler silinmez veya yeni şablonlara zorla bağlanmaz.

## Konsoldan kullanıcı oluşturma ve e-posta taslağı

Platform yöneticisi, konsol menüsündeki **Kullanıcı oluştur** ekranından ad, soyad, e-posta, kurum, denetim/proje, rol ve stajyerin salt okunur denetçi erişimini seçebilir. Genel konsolda tüm kurumlar; kurum subdomain'inde yalnızca o kurumun denetimleri listelenir. Aynı e-posta yeniden oluşturulmaz ve mevcut kullanıcının parolası değiştirilmez.

Yeni hesap için güvenli rastgele 12 karakterlik geçici parola oluşturulur; veritabanına yalnızca parola özeti kaydedilir. İlk başarılı giriş bu parolayı tüketir ve kullanıcıyı yeni parola belirleme ekranına gönderir. Yeni parola belirlenmeden çıkış yapılırsa yönetici parola sıfırlamalıdır. Eski hesapların giriş davranışı değişmez.

Hesap oluşturulunca varsayılan e-posta uygulamasına `mailto:` taslağı açılır; uygulama engellerse ekrandaki açma, kopyalama veya `.eml` indirme seçeneklerini kullanın. Uygulama davet e-postasını otomatik göndermez. Geçici parolayı içeren taslak sunucuda, oturumda veya işlem kayıtlarında saklanmaz; sayfadan ayrılmadan taslağı kaydedin.

Stajyer taslağı seçilen kurum türüne göre mevzuat/iyi uygulama kontrol listesi ve Excel sütunlarını içerir. Kurum yöneticisi taslağında haftalık ve aylık durum bilgilendirmesi ifadesi bulunur; bu değişiklik periyodik e-posta gönderimi planlamaz. Kurum subdomain'i varsa davet doğrudan o subdomain'deki projeye, yoksa genel konsoldaki projeye bağlanır.

Yönetici rol geçişleri artık üretimde de seçilen rolün işlemlerini yapabilir; tüm kayıtlar giriş yapan yöneticiye atfedilir. Salt okunur stajyer üyelikleri değişiklik yapamaz. Kontrol tablosundaki filtreler ve sütun sıralamaları görünür veriler üzerinde çalışır; dashboard toplamları bütün denetimi göstermeye devam eder.
