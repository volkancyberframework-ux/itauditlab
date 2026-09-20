# Denetim konsolu kullanım kılavuzu

## 1. Mevcut siteden hemen başlayın

Konsol **mevcut ITAudit Render servisini ve PostgreSQL veritabanını** kullanır. Yeni servis, veritabanı veya cron kurmayın. Mevcut yayın komutu değişmez; yayın sırasında konsol tabloları otomatik hazırlanır. ITAudit tabloları değiştirilmez. Aynı veritabanındaki ayrı tablo alanı, kullanıcıların ve oturumların birbirine karışmasını önler.

1. Yayın tamamlandığında **https://www.grcustasi.com/denetim/admin/** adresini açın.
2. Mevcut ITAudit süper yönetici hesabınızın **e-posta adresi ve parolasıyla** giriş yapın. Aktif süper yöneticiler ilk kurulumda bağımsız konsol hesaplarına aktarılır. Sonraki parola değişiklikleri iki sistem arasında eşitlenmez; normal ITAudit üyeleri aktarılmaz.
3. **Organizations** altında kurumunuzu, logonuzu ve istediğiniz subdomain adını kaydedin.
4. **Users**, **Audits / Memberships** ve **Controls** üzerinden kullanıcıları, denetimi ve kontrolleri ekleyin.
5. Kullanıcılar DNS beklemeden **https://www.grcustasi.com/denetim/** adresinden giriş yapabilir.

Mevcut `DATABASE_URL`, `SECRET_KEY`, SMTP ve Telegram ortam değişkenleri kullanılır. Mevcut SMTP/Telegram bilgileri eksikse ilgili gönderimler bu bilgiler tamamlanana kadar bekler. Bildirim kuyruğu aynı servis içinde yaklaşık dakikada bir yeniden denenir. Ayrı Render servisi veya veritabanı oluşturulmaz.

## 2. Tüm kurumlar için tek wildcard DNS kurulumu

Yalnızca Torbalı değil, panelde tanımladığınız bütün geçerli kurum etiketleri desteklenir: `torbalibld.grcustasi.com`, `ornekfirma.grcustasi.com`, vb.

1. Mevcut ITAudit web servisinde **Settings → Custom Domains** bölümüne `*.grcustasi.com` ekleyin.
2. DNS sağlayıcınızda aşağıdaki CNAME kayıtlarını oluşturun. Hedefleri **Render'ın gösterdiği tam değerlerden** kopyalayın:

| Tür | Ad / Host | Hedef |
| --- | --- | --- |
| CNAME | `*` | Mevcut ITAudit servisinin `itauditlab.onrender.com` adresi |
| CNAME | `_acme-challenge` | Render'ın verdiği `….verify.renderdns.com` değeri |
| CNAME | `_cf-custom-hostname` | Render'ın verdiği `….hostname.renderdns.com` değeri |

3. Render'a dönüp doğrulayın ve wildcard TLS sertifikasının hazır olmasını bekleyin.
4. **Kök `@` ve `www` kayıtlarını değiştirmeyin.** Mevcut site ITAudit'te kalır. Kök alan şu anda Render'a yönleniyor; wildcard için Render bunu gerektirir. Mevcut özel subdomain kayıtları wildcard'dan önceliklidir. Örneğin eski bir `torbalibld` kaydı varsa doğru konsol hedefine yönlenmelidir.
5. Aynı DNS etiketindeki mevcut doğrulama kayıtlarını körlemesine silmeyin. Çakışma varsa Render'ın ilgili alan adı ekranındaki doğrulama adımları esas alınır.

Bu işlemden sonra her yeni kurum için DNS kaydı eklemek gerekmez. Yalnızca merkezi panelde subdomain seçersiniz. **Panelde isim değiştirmek DNS API çağrısı yapmaz; önceden çalışan wildcard kurulumunu kullanır.** Eski kurum adresi uygulamada artık tanınmaz. Tanımlanmamış subdomain'ler 404 döner.

Geçerli etiketler küçük harf, sayı ve tire içerir; başta/sonda tire olmaz. `www`, `admin`, `api`, `mail`, `core`, `akademi`, `itauditlab` ayrılmıştır. Subdomain benzersiz olmalıdır.

Resmî kaynak: [Render özel ve wildcard alan adları](https://render.com/docs/custom-domains).

## 3. Kurum oluşturun ve logonuzu yükleyin

**Merkezi yönetim → Organizations → Ekle**:

- **Kurum adı:** Görünmesini istediğiniz ad.
- **Kurum kayıt kodu / slug:** Örneğin `ornek-firma`. Sabit kayıt kimliği olarak kullanın.
- **Subdomain:** Yalnızca `ornekfirma` yazın; tam URL veya `.grcustasi.com` eklemeyin.
- **Kurum logosu:** PNG, JPEG veya GIF, en fazla 2 MB ve 16 megapiksel. Mevcut logo önizlemesi panelde görünür.

Logo güvenli PNG biçimine dönüştürülerek veritabanına kaydedilir. GIF'in ilk karesi kullanılır. Giriş, konsol ve PDF'ler kurum markasını kullanır. Logo yüklenmezse genel kurum simgesi görünür; Torbalı demo kurumunun mevcut logosu varsayılan olarak korunur.

## 4. Kullanıcıları oluşturun

**Accounts → Users → Ekle** bölümünde e-posta, ad, soyad ve başlangıç parolası girin. Adları doldurursanız konsolda **BT Sorumlusu (Ahmet, Volkan)** gibi görünür; adı olmayan hesap için e-posta gösterilir.

Normal denetim kullanıcılarına `is_staff` veya `is_superuser` vermeyin. Bu kullanıcılar `/admin/` yerine kendi kurumlarının konsoluna giriş yapar. İlk girişte parola değiştirmeleri gerekir. Başlangıç parolasını kullanıcıyla güvenli şekilde paylaşın; otomatik davet e-postası gönderilmez.

## 5. Denetimi oluşturun ve ekip atayın

**Workspace → Audits → Ekle**:

1. Kurumu seçin, denetimin adını yazın.
2. Gerçek kullanımda **is_demo kapalı**, **archived kapalı** olsun.
3. Aynı sayfanın Memberships bölümünde kullanıcıları ve rollerini ekleyin. Sonradan Memberships ekranından da düzenleyebilirsiniz.
4. Kaydedin. Yeni denetim Faz 1'de başlar; fazlar denetim konsolundan ilerletilir.

| Rol | Yetki |
| --- | --- |
| BT sorumlusu | Kontrol yanıtı, giderim/itiraz, risk kabulü talebi |
| Denetçi | Görüş, test ve son onay; bulgu inceleme, tarih düzenleme ve kapanış |
| Kurum yöneticisi | Yönetim görünümü; risk kabulü talebini onaylama |
| Stajyer | Açık kontrol tanımları, kontrol önerisi ve test rehberi hazırlama |
| Platform yöneticisi | Merkezi yönetim, kurum/ekip/kontrol yönetimi ve denetim işlemleri |

Birden fazla denetimi olan kullanıcı üstteki **Aktif denetim** seçimini kullanır. Kurum subdomain'inde başka kurumun denetimleri görünmez.

Adminin **Kullanıcı gözünden bakın** seçenekleri canlı ortamda salt okunur önizlemedir. Gerçek BT veya denetçi işlemini test etmek için ilgili kullanıcıyla giriş yapın. Yerel demo önizlemesinde işlemler kaydedilebilir.

## 6. Kontrolleri ekleyin

**Workspace → Controls → Ekle**:

- Denetim, benzersiz kontrol kodu, başlık ve açıklama.
- Çerçeve, tema ve risk seviyesi.
- **Beklenen kanıtlar / test rehberi:** İstenecek belge, kayıt, ekran görüntüsü ve test adımları. Örneğin: “Son üç aya ait erişim listesi; ayrılan personelden üç örnek seçilip hesap kapatma tarihleri karşılaştırılacak.”
- Stajyerin tanımı görmesini istiyorsanız `intern_visible` işaretleyin.

**Her fazda yeni kontrol eklenebilir.** Yeni kontrol Başlanmadı olur. Kontrol önerisini onaylamak da yeni kontrol oluşturur. Yeni kontrolün atanacağı denetimi dikkatle seçin; kayıttan sonra denetimi değiştirilemez.

Faz 1–3'te yeni kontrol e-postası gönderilmez. **Faz 4'te yeni kontrol eklendiğinde**, o denetime atanmış aktif BT sorumlularının her birine kontrol başlığı, kodu, açıklaması, risk seviyesi, beklenen kanıtları ve bağlantısı e-posta ile gönderilir. Mevcut kontrolü düzenlemek yeni kontrol e-postası göndermez.

Mevcut kontrol tanımı değişirse denetçinin son test onayı kaldırılır. Kanıt alanı şu anda bir rehber metnidir; dosya yükleme modülü değildir.

## 7. BT yanıtı ve denetçi görüşü

BT sorumlusu listede **Yanıtla** bölümünü açarak sayfadan ayrılmadan kayıt yapabilir. Kontrol detayında da aynı işlem vardır.

| Durum | Açıklama |
| --- | --- |
| Yapılıyor | Zorunlu. Neyin, kim tarafından ve nasıl uygulandığını kısaca yazın. |
| Kısmen yapılıyor | İsteğe bağlı. Uygulanan ve eksik kalan kısmı yazabilirsiniz. |
| Yapılmıyor | İsteğe bağlı. |
| Uygulanamaz | Zorunlu. Kontrolün neden kapsam dışında olduğunu açıklayın. |

Açıklama kutusundaki rehber seçime göre değişir. Doğruluk beyanı her yanıtta zorunludur. Her gönderim ayrı geçmiş kaydı oluşturur. Başka bir BT kullanıcısının mevcut yanıtını değiştiremezsiniz.

Denetçi **ilk fazdan itibaren**, randevu beklemeden görüş ve gerekçe yazabilir. Görüş, yönetici ve denetim ekibine görünür; BT sorumlusu ve stajyer bu özel görüşü görmez. Bulgu/giderim önerisi BT ile paylaşılır; ekip özel notu yönetici PDF'ine de dahil edilmez.

Denetçi testi bitirdiğinde **“Kontrolü test ettim; bu değerlendirmeye son onayımı veriyorum”** kutusunu işaretler. İşaretlenmeyen görüş son onay değildir. BT yanıtı daha sonra değişirse görüş metni korunur, son onay kaldırılır; denetçi tekrar test edip onaylar.

## 8. Dört faz

1. **BT yanıtları:** BT yanıtları toplanır. Denetçi aynı anda çalışabilir. Tüm kontroller yanıtlanmadan Faz 2'ye geçilmez.
2. **Saha denetimi:** Gün/saat önerilir, karşı taraf onaylar. Yeni kontroller dahil BT yanıtları ve denetçinin son test onayları tamamlanınca Faz 3'e geçilir.
3. **Bulgu giderme:** Açık bulgular giderilir veya yönetici tarafından risk kabulüyle sonuçlandırılır. Tüm yanıt ve test onayları güncel olmalı; açık bulgu kalmamalıdır.
4. **Sürekli kontrol:** Sistem yaşamaya devam eder. Yeni kontroller, yanıt sürümleri, testler ve bulgular eklenir. Bu fazdaki yeni kontroller için BT e-postası çalışır.

## 9. Bulgu kararları ve son tarihler

Kısmen uygun veya uygun değil denetçi görüşü kontrol bağlantılı bulgu oluşturur. Her bulgunun son tarihi vardır. Yeni bulguda denetçi tarih belirtmezse **30 gün sonrası** atanır; tarih panelden düzenlenebilir. Süresi geçmiş açık bulgular işaretlenir.

BT sorumlusu şu işlemleri seçebilir:

- **Bulguyu kabul ediyorum:** Bulguyu kabul eder; kapatmaz.
- **Risk giderilecek:** Giderim planı ve son tarih zorunludur.
- **Eksikliği giderdim:** Test/kanıt özetiyle denetçi incelemesine gönderir.
- **Yapılmayacak · risk kabulü talep et:** Neden giderilmeyeceğini açıklar. Tek başına bulguyu kapatmaz.
- **İtiraz:** Gerekçeyi kaydeder.

Denetçi giderimi test ederek veya itirazı uygun bularak kapatır; reddedebilir, son tarihi değiştirebilir ve sonuçlanmış bulguyu yeniden açabilir. **Risk kabulü**, kurum yöneticisi veya platform yöneticisi onayıyla sonuçlanır; “giderildi” sayılmaz, ayrı gösterilir. Karar geçmişi korunur.

## 10. Raporlar ve bildirim takibi

Kontroller ve Bulgular başlıklarında PDF indirme düğmeleri bulunur. PDF'ler seçilen denetime ve kullanıcının rolüne göre hazırlanır; başka kurumun verileri eklenmez.

Merkezi yönetimde:

- **Notifications:** Telegram teslim zamanı ve deneme sayısı.
- **Control emails:** Faz 4 yeni kontrol e-postaları, alıcı, içerik ve teslim zamanı.
- Teslim zamanı boşsa mesaj henüz gönderilmemiştir. Seçili kayıtlar için yeniden gönderme işlemi vardır. Aynı servis içindeki bildirim işçisi bekleyen kayıtları yaklaşık dakikada bir dener.

Telegram ve SMTP yapılandırması eksikse “gönderildi” kabul edilmez. Ağ hatalarında tekrar gönderim nadiren mükerrer mesaja yol açabilir. Üyeliği kaldırılmış veya pasifleştirilmiş kullanıcıya bekleyen yeni kontrol e-postası gönderilmez.

## Hızlı başlangıç sırası

**Mevcut yönetici ile /denetim/admin/ → kurum + logo → kullanıcılar → denetim + üyelikler → kontroller → /denetim/ üzerinden giriş.**

Kurumlara özel adresleri açmak için wildcard DNS adımını sonradan tamamlayabilirsiniz.
