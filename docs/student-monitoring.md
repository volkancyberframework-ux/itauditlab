# CORE Öğrenci İlerlemesi ve Müdahale

## Kullanım

CORE menüsündeki **Öğrenci İlerlemesi ve Müdahale** bağlantısı:
`/bulamazsinki/core/monitoringsettings/panel/`.

Görüntüleme için aktif staff hesabına `core.view_monitoringsettings`, işlemler için
`core.change_monitoringsettings` gerekir. Superuser bu izinlere sahiptir. Bütün özel
endpoint'ler sunucuda aynı izinleri denetler; POST işlemleri CSRF korumalıdır.

Varsayılan kural sonraki zorunlu dersin gerçekten erişime açılmasıdır. Gün kuralı,
son ders eşiği ve kritik sayısı / ortalama gecikme sınırı panelden değiştirilebilir.
Ayar değişiklikleri eski günlük özetleri değiştirmez. Tarihler yapılandırılmış
IANA yönetim saat diliminde gösterilir; veritabanı zamanları UTC'dir.

Mevcut CORE ders testleri tarayıcıda cevapları kontrol eder; sunucuda güvenilir
bir tamamlanma kaydı yoktur. Bu nedenle eski ziyaretler tamamlanmış sayılmaz.
Yetkili ders açılışları artık ayrı erişim kanıtı kaydeder. Yönetici öğrenci
ayrıntısında, doğrulama kanıtı ve zamanı ile tamamlandı / tamamlanmadığı doğrulandı /
bilinmiyor durumunu kaydeder. Tamamlanma veya erişim zamanı bilinmeyen dersler
gecikmiş varsayılmaz. Tamamlanma yüzdesi doğrulanmış tamamlanmaların zorunlu derslere
oranıdır; bilinmeyenler ayrıca görünür. Kaynak verisi eksikse gerçek ilerlemenin
bu yüzden tam olarak belirlenemediği açıkça gösterilir.

Program takvimi yaklaşan dersleri belirler. Gecikme hesabı planlanan tarihten
ziyade gerçek `ProgramRelease.access_granted_at`, video kayıt zamanı veya yetkili
ilk erişim kanıtını kullanır. Testlere eski manuel M2M erişimlerinde zaman bilgisi
yoktur; yönetici mevcut erişimin doğrulanmış zamanını gerekçeyle kaydedebilir.
Bu işlem hiçbir kullanıcıya yeni ders erişimi vermez.

İzleme duraklamaları ve muafiyetler yalnızca izleme kapsamını / gecikme süresini
etkiler. Mevcut program erişim otomasyonu ve üyelik erişimi değiştirilmez. Gerçek
program kaydı pasifse izlemede aktif kabul edilmez. Tamamlandı / arşiv / duraklatıldı
kayıtları varsayılan aktif görünümden çıkar; filtreyle yine incelenebilir.
Aynı ders farklı programlarda bir öğrenciye atanmışsa öğrenci toplamında bir kez
sayılır; programların kendi istatistikleri ayrı tutulur.

## E-posta

Öğrenci satırındaki **E-posta oluştur** gerçek verilerle taslak oluşturur. Çözülmemiş
müdahale varsa yeni taslak için açık onay gerekir. Önizleme ekranında metin düzenlenir.
**Kaydet ve e-posta uygulamasını aç**, taslağın düzenlenmiş halini kaydeder ve
URL-encoded `mailto:` ile varsayılan uygulamayı açmayı ister. Harici uygulamanın açılması
ve teslimat doğrulanamaz; gönderildi kabul edilmez. Uzun mailto metinleri için tam
metin alternatif olarak ekranda tutulur.

Kullanıcı harici uygulamada gerçekten gönderdikten sonra onay kutusunu işaretleyip
**Elle gönderildi işaretle** düğmesini kullanır. Öğrenci, program kayıt kimlikleri,
metin, yönetici, işaret zamanı, taslak ve gönderim işareti anındaki gerçek ilerleme /
ayarlar saklanır. Sonraki durumlar yanıt bekleniyor, yanıt alındı, görüşme planlandı,
çözüldü olabilir. Yanlış gönderim işareti ancak açıklamalı ve açık onaylı düzeltmeyle
geri alınabilir. Her işlem önce / sonra değerleriyle denetim izine yazılır.
Bu modül SMTP gönderimi, üyelik dondurma veya iş desteği iptali yapmaz.

## Günlük özet ve operasyon

Mevcut `run_daily_programs` komutu gerçek güncel veriyi günlük olarak kaydeder;
Render'daki mevcut günlük cron servisi kullanılır, yeni servis gerekmez.
Bağımsız güvenli tekrar / bugünkü özet:

```sh
python manage.py snapshot_student_monitoring
```

Aynı rapor günü ikinci kez çağrılırsa eski kayıt değişmez. Geçmiş günler hesaplanarak
uydurulmaz. İlk kurulumdan önceki günler grafikte **Kayıt yok** kalır. Grafikler yalnızca
kaydedilmiş günleri gösterir; kayıp günler sıfırla doldurulmaz veya çizgiyle birleştirilmez.
Gerekçeli bugünkü düzeltme için yetkili yönetici kimliği zorunludur:

```sh
python manage.py snapshot_student_monitoring --actor-id ADMIN_ID --correction-reason 'Belgelenmiş veri düzeltmesi'
```

Düzeltme öncesi bütün özet ve gerekçe denetim izinde saklanır. Geçmiş snapshot'lar
ve işlem kayıtları Django admin üzerinden düzenlenemez / silinemez.

## Yayın ve geri dönüş

Aynı Render web servisi, PostgreSQL ve günlük cron korunur. `0028` yalnızca yeni CORE
tabloları / indeksler ekler; mevcut öğrenci, program, erişim ve ders verilerini
silmez veya dönüştürmez. Web pre-deploy komutuna bugünün gerçek özetini kaydetme
adımı eklenmiştir. Render ayarları blueprint dışında tutuluyorsa mevcut migrate
adımından sonra aynı komut Shell üzerinden de güvenle çalıştırılabilir.

Kontrol sırası: `python manage.py migrate --plan`, `python manage.py migrate --noinput`,
statik dosyalar, sağlık kontrolü, yetkili panel / öğrenci ayrıntısı ve anonim erişim
reddi. Cron servisinin de aynı commit'i kullandığını doğrulayın.

Geri dönüş gerekirse Render'ın önceki başarılı sürümüne uygulama rollback yapın;
eklenen tabloları olduğu gibi bırakın. Tablo silen ters migration çalıştırmayın;
böylece oluşmuş ilerleme kanıtı, müdahale ve tarihçe korunur. Sorun giderildikten
sonra ileri yönde migration / yayın tekrarlanabilir. Günlük özet tekrarları idempotenttir.

## Doğrulama

`python manage.py test core` yeni modül, mevcut program erişimleri, takvim e-postaları
ve CORE arayüz regresyonlarını kapsar. Modül testleri her iki kural, son ders,
geç tamamlama, çoğul kayıtlar, muafiyet, duraklatma, eksik erişim, sabit sorgu sayısı,
izin / CSRF, kişiselleştirme, dış e-posta işareti ve immutable tarihçeyi kapsar.
