# Active Directory: Denetçi Gözüyle — web yayını

75 özgün Türkçe soru, beş bölümde 15'er soru. 30 başlangıç, 35 orta, 10 ileri. 20 görsel karar, 10 çoklu seçim, 10 test (5 doğru/yanlış dahil), 10 senaryo, 5 kısa yazılı yanıt, 10 sıralama, 10 risk kartı. Eşleştirmeler mevcut çoklu seçim türüyle temsil edilir. Yeni mobil soru türü eklenmedi. Sesli soru yok.

Her soruda 2560×1440 ayrı sentetik Windows/AD yönetim ekranı vardır. Bunlar gerçek ortamdan alınmış ekran görüntüleri değildir. Tüm kullanıcılar, domainler ve loglar kurgusaldır; görüntünün altında açıkça belirtilir. Görseller cevap metninin ekran görüntüsü değildir: konsol ağacı, nesne tabloları, özellikler, GPO, olay alanları ve denetim çalışma kâğıtları gösterilir.

## Web mimarisi

Flutter kaynakları ve derlenmiş dağıtım dosyaları değiştirilmedi. Python yalnız app.grcustasi.com HTML yanıtına ortak CSS/JS ekler. Web adaptörü mevcut API oturumunu açar, görselli öğrenme yollarını HTML çalışma ekranında gösterir; mevcut hesap, yetki, XP ve ilerleme modellerini kullanır. Görüntüleyici ayrı dialog olduğu için cevap taslağı korunur. Diğer yollar aynı API üzerinden çalışır. Yeni AD yolu yalnız web listesinde yayınlanır; native listeye eklenmez. Üyelik koşulları mevcut yollarla aynıdır.

Web oturumu aynı süre ve yetkide, HttpOnly/Secure/SameSite=Strict yenileme çereziyle mevcut istemciyle birlikte döndürülür. Cookie üzerinden yenilemede Origin doğrulanır. Mobil giriş/yenileme endpointleri değiştirilmedi. Görseller yetkili API üzerinden orijinal PNG baytlarıyla yüklenir.

## İçerik ve tutarlılık

Harun (IT Müdürü), Selin (Denetim Yöneticin), Derya (IAM Sorumlusu), Eren (Endpoint Sorumlusu). İlk dört bölüm corp.local eğitim ortamıdır. Son bölüm 850 çalışanlı NovaBank'ın 13 Ekim 2026 denetimidir: novabank.local ve test child domain. 14 aktif eski çalışan hesabı standart yetkidedir; destek.ozge ve svc.payroll ayrı ayrı yüksek ayrıcalık bulgularıdır. Merve'nin bölüm değişikliği eski Finance_Edit üyeliğiyle uzlaştırılır. Parola ölçütü 14, domain değeri 8; PSO yok. WS044 pilot GPO filtre grubunda değil. APP02 svc.batch başarısız girişleri kesin saldırı diye sunulmaz. NB-DC01 02.16 grup değişikliği ile CH-108 02.18 onayı ayrı kaynak kayıtlarıdır; nedensellik veya veri sızıntısı iddiası yok. Son sorular aynı bulguların sahiplerini ve yeniden test kanıtlarını kullanır.

## Yeniden üretme ve import

```
python content/learning-paths/ad-auditor/build_content.py
python content/learning-paths/ad-auditor/render_evidence.py
python manage.py seed_ad_auditor_path                 # dry-run
python manage.py seed_ad_auditor_path --apply          # açıkça uygulama
```

0034 migration aynı importu kullanır. Kalıcı external_id→PK registry ve paket/görsel digest kontrol edilir. İkinci çalıştırma 0 soru ekler; değişmiş veya paylaşılan mevcut içerik otomatik üzerine yazılmaz. Diğer içerik, kullanıcı cevapları, XP ve ilerleme silinmez.

## Geri alma

Tercih edilen geri alma: önceki uygulama commitini Render'da yeniden yayınlamak. 0034 ters migration yalnız AD web_published bayrağını kapatır; hiçbir soru veya kullanıcı kaydı silmez. Sonradan --apply yeniden açabilir. Görsel manifesti aynı pakete bağlıdır; paket ve görüntüleri ayrı güncellemeyin.

## Doğrulama

Django: mobile_web.test_ad_web, mobile_web.test_web, mobile_api.test_cisa_simulator, mobile_api.test_first30_recordings: 19 test başarılı. AD test akışı 75 sorunun tamamını doğru cevapla, 5 bölüm özeti ve final sonucu, XP/ilerleme kayıtları, yanlış cevap, tekrar gönderim, resume, üyelik, native listeden izolasyon, 75 yetkili görsel ve refresh çerezi kontrollerini içerir. Node: viewer-math.test.mjs, 2 test başarılı.

Gerçek Chrome'da yerel web bileşeni: tekerlek, çift tık, sürükleme, iki PointerEvent ile pinch, fit, %100 sıfırlama, ESC/close, seçili cevap korunması, yükleme hatası ve retry başarılı. 390×844 dar ekranda da test edilir. Fiziksel iOS/Android cihazıyla iki parmak testi yapılmadı; dokunma hareketi PointerEvents ile doğrulandı. Beş bölüm ve fullscreen QA görüntüleri qa/ altında.

## Canlı doğrulama — 13 Ekim 2026

Render 4f1a791 yayını 2m22s sonunda Live. Kalıcı yol ID: 30; 75 soru, 75 PNG, sıfır ses; web_published=true, native published=false. Production dry-run 0 ekleme gösterdi; tüm 75 manifest/PNG kontrolü geçti. Root HTML web adaptörünü içeriyor; canlı JS baytları yerel sürümle aynı; healthz 200; yetkisiz web API/görsel isteği 401.

Mevcut yollar 26 ve 28: 100'er soru. İçerik SHA256 yayın öncesi/sonrası aynı: 755f65c1cf1ba7e5b97f63f37bf756e3fb89f88b7eb1ffe534347b039ad18e76. Cevap 100→100, ilerleme 11→11, XP transaction 96→96. Flutter dosya özeti 199 dosyada aynı.

Gerçek Chrome yerel fixture: 75/75 ekranın tamamı, 7 soru türünün kontrolleri ve orijinal PNG boyutları başarılı. Web fetch adaptörü mevcut oturum yanıtını 45ms içinde döndürüp doğrudan soru ekranını açtı. 390×844 viewport testleri başarılı. Canlı uygulamada kullanıcı oturumu açılmadığı için girişli UI üzerinde son görsel tur yapılmadı; production kontrolü yetkili Render shell içinden salt okunur içerik doğrulaması ve public web dosya/sağlık kontrolleriyle yapıldı.
