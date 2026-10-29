# Teknik inceleme ve doğrulama sınırları

55 senaryonun her birinde ayrı teknik çıktı ve ayrı PNG vardır. Komut/çıktı satırlarının yatay/dikey sınırları renderer assertion'larıyla kontrol edilir. Yanıt anahtarı görsele yazılmaz. Kanıtların altında kurgusal eğitim etiketi yer alır.

İncelemede korunan ayrımlar:

- VLAN/access/trunk üyeliği L3 erişim izolasyonu sayılmaz. Native VLAN, allowed VLAN ve DTP ayrı alanlardır. ACL adı ile uygulandığı arayüz/yön farklıdır.
- Genel firewall örnekleri ilk eşleşme veya stateful mevcut oturum davranışını kanıtta açıkça belirtir; üreticiye özgü bütün varsayılanlara genellenmez. NAT adres çevirisi izin kararı değildir. Transit politika cihazın yerel yönetim politikasının yerine geçirilmez.
- VPN şifrelemesi MFA veya hedef yetkisi yerine sayılmaz. Sunucu sertifikasının CA güveni, beklenen CN ve kullanım amacı ayrı kontrollerdir. Sertifika iptalinin uygulanması ayrıca doğrulanır. Split tunnel kendi başına ihlal ilan edilmez; onaylı tasarım ve diğer kontrollerle değerlendirilir. Kripto sapması kurum kriteri üzerinden verilir; gerçek bir oturumun çözüldüğü iddia edilmez.
- AWS security group izin birleşimi ve stateful davranışı NACL ilk eşleşme/stateless davranışıyla karıştırılmaz. Public IP/route ve diğer katmanlar olmadan yalnız izin kaydından kesin internet maruziyeti çıkarılmaz.
- ALLOW/ACCEPT uygulama giriş veya veri okuma başarısı sayılmaz. Başarısız tarama ihlal başarısı diye sunulmaz. SKIPDATA ile NODATA farklıdır. NAT kaynak portu, zaman ve kimlik atfı birlikte incelenir. Saat dilimi ile gerçek saat senkronizasyonu ayrılır.
- Ticket ve yapılandırma niyeti çalışma zamanı kanıtı sayılmaz. Negatif ICMP testi bütün TCP servislerinin kapalı olduğunu kanıtlamaz. Düzeltmeler denetçinin izinsiz üretim değişikliği yapmasına dayanmaz.

Kaynaklar README.md'de bağlantılıdır. Fortinet sayfalarına erişim sağlanamadığından bu sayfalardan doğrulanmış üretici varsayılanı iddia edilmez; genel firewall örnekleri simülatör olarak açıkça etiketlenir. Fiziksel ağ cihazı, gerçek üretim taraması veya fiziksel iOS/Android testi yapılmaz. API grading/progress, yetkili görsel erişimi ve kullanıcı ataması Django testleriyle; görsel etkileşimler yerel mock API browser fixture'ıyla test edilir.
