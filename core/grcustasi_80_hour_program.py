"""GRC Ustası 80 saatlik, 6 aylık öğrenme programı tanımı."""


PROGRAM_SLUG = "grc-ustasi-80-saat-6-ay"
PROGRAM_NAME = "GRC Ustası — 80 Saatlik Mesleğe Hazırlık Programı"


LESSONS = [
    ("GRC, Risk ve Kontrol Dili", "Yönetişim, risk, uyum ve kontrol kavramlarını ortak bir iş dili içinde öğren; teknik olayları iş riski olarak değerlendirmeye başla."),
    ("Risk Değerlendirmesi ve Üç Savunma Hattı", "Doğal risk, artık risk, etki, olasılık, risk iştahı ve üç savunma hattının sorumluluklarını öğren."),
    ("Uygulama: Fintek Şirketi Varlık Envanteri", "Kurgusal bir fintek şirketinin sistem, veri, hizmet ve kritik süreçlerinden denetlenebilir bir varlık envanteri oluştur."),
    ("Uygulama: Risk Matrisi ve Puanlama", "Varlık, tehdit, zafiyet, etki ve olasılık değerlerinden risk puanı ve öncelik sırası oluştur."),
    ("Uygulama: Kontrol Türleri ve Kontrol Tasarımı", "Önleyici, tespit edici, düzeltici, manuel ve otomatik kontrolleri sınıflandırarak ölçülebilir bir kontrol tasarla."),
    ("Uygulama: Risk Kayıt Defteri ve Risk Yanıtı", "Risk sahibi, kontrol sahibi, aksiyon, hedef tarih ve artık risk bilgilerini içeren risk kayıt defteri hazırla."),
    ("Vaka: Teknik Bulguyu İş Riskine Dönüştürme", "Teknik bir güvenlik problemini finansal, operasyonel, hukuki ve itibari etkileriyle yönetim seviyesinde bir risk ifadesine dönüştür."),
    ("Vaka: Risk Sahibiyle Görüş Ayrılığı", "Yüksek riski kabul etmeyen bir yönetici karşısında kanıtlarını ve savunulabilir risk değerlendirmesini hazırla."),
    ("Ağ Yapısını Denetçi Gözüyle Okumak", "TCP/IP, LAN, WAN, DNS, DHCP, NAT, port, protokol, güvenlik duvarı, VPN, VLAN ve DMZ yapılarını denetim açısından öğren."),
    ("Windows, Linux ve Dizin Servisleri", "Windows Server, Linux, kullanıcılar, gruplar, yetkiler, servisler, Active Directory ve yama yönetiminin kontrol noktalarını öğren."),
    ("Uygulama: Ağ Şeması Hazırlama", "Bir şirketin internet, kullanıcı, sunucu, veri tabanı ve bulut bağlantılarını gösteren ağ şeması hazırlayıp güven sınırlarını işaretle."),
    ("Uygulama: Port, Güvenlik Duvarı ve Bölümlendirme", "Güvenlik duvarı kuralları, açık portlar ve ağ bölümleri üzerinden gereksiz erişimleri ve zayıf kontrol tasarımlarını belirle."),
    ("Uygulama: Windows ve Active Directory Kanıtları", "Kullanıcı listeleri, ayrıcalıklı gruplar, parola politikaları ve grup politikası çıktıları üzerinden kontrol testi gerçekleştir."),
    ("Uygulama: Linux Kullanıcı, Servis ve Yetki İncelemesi", "Linux kullanıcılarını, gruplarını, servislerini, dosya izinlerini ve kritik yapılandırmaları inceleyerek denetim kanıtı hazırla."),
    ("Vaka: Açık Güvenlik Duvarı Kuralı", "İş gerekçesi bulunmayan geniş kapsamlı erişim kuralının riskini, kanıtını, kök nedenini ve önerisini oluştur."),
    ("Vaka: Geciken Yamalar ve Ağ Bölümlendirme", "Kritik sistemlerde geciken yamalar ile zayıf ağ bölümlendirmesinin birlikte oluşturduğu riski değerlendir."),
    ("Bulut Bilişim ve Ortak Sorumluluk Modeli", "IaaS, PaaS, SaaS, temel AWS servisleri, bulut kanıtları ve müşteriyle hizmet sağlayıcının kontrol sorumluluklarını öğren."),
    ("Kimlik, Erişim ve Görevler Ayrılığı", "Kullanıcı yaşam döngüsü, en az yetki, MFA, ayrıcalıklı erişim, RBAC, ABAC ve erişim gözden geçirmelerini öğren."),
    ("Uygulama: AWS Varlık ve Mimari İncelemesi", "EC2, S3, RDS ve VPC bileşenlerinden oluşan ortamın varlıklarını, veri akışını ve sorumluluk sınırlarını çıkar."),
    ("Uygulama: IAM Kullanıcı, Grup, Rol ve Politika", "AWS IAM kullanıcı, grup, rol ve politikalarını inceleyerek aşırı yetkilendirme risklerini belirle."),
    ("Uygulama: Kök Kullanıcı, MFA ve Ayrıcalıklı Erişim", "Kök hesap kullanımı, MFA durumu ve yönetici erişimleri için kontrol testi ve kanıt listesi hazırla."),
    ("Uygulama: CloudTrail ve CloudWatch Kanıtları", "Bulut faaliyet kayıtlarının bütünlüğünü, kapsamını, saklama süresini ve izleme kontrollerini değerlendir."),
    ("Uygulama: İşe Giriş, Görev Değişikliği ve İşten Çıkış", "Bir kullanıcı popülasyonunda erişim verme, değiştirme, kaldırma ve dönemsel gözden geçirme kontrollerini test et."),
    ("Vaka: İşten Ayrılan Çalışanın Aktif Hesabı", "Kapatılmayan çalışan hesabını kök neden, etki, kanıt ve kontrol eksikliği açısından incele."),
    ("Vaka: Herkese Açık Bulut Depolama Alanı", "Herkese açık bir S3 alanını veri sınıflandırması, şifreleme, erişim yönetimi ve iş etkisi açısından değerlendir."),
    ("Risk Temelli BT Denetimi Planlama", "Denetim evreni, yıllık plan, kapsam, amaç, kaynak, zamanlama ve risk temelli önceliklendirme süreçlerini öğren."),
    ("Denetim Kanıtı ve Kontrol Testi", "Kanıt güvenilirliği, popülasyon, örnekleme, kontrol tasarımı, çalışma etkinliği ve yeniden uygulama yöntemlerini öğren."),
    ("Uygulama: Denetim Evreni ve Yıllık Plan", "Kurgusal bir kurumun teknoloji süreçlerinden denetim evreni çıkarıp risk temelli yıllık denetim planı hazırla."),
    ("Uygulama: Süreç Yürüyüşü ve Görüşme Hazırlığı", "Süreç sahibi görüşmesinin sorularını oluştur ve süreci baştan sona takip eden bir yürüyüş çalışması gerçekleştir."),
    ("Uygulama: Popülasyon, Örnekleme ve Kanıt Güvenilirliği", "Eksik veya şüpheli bir veri kümesini değerlendirerek örneklem yöntemini ve gerekli ek kanıtları belirle."),
    ("Uygulama: Kontrol Tasarımı ve Çalışma Etkinliği", "Bir kontrolün doğru tasarlanıp tasarlanmadığını ve dönem boyunca çalışıp çalışmadığını test et."),
    ("Uygulama: Çalışma Kâğıdı ve Bulgu Yazımı", "Amaç, kapsam, prosedür, kanıt, sonuç, istisna ve referanslardan oluşan denetim çalışma kâğıdı hazırla."),
    ("Vaka: Yönetimin Bulguya İtirazı", "Bulguyu kabul etmeyen süreç sahibi karşısında kanıtlarını, risk gerekçeni ve kapanış yaklaşımını savun."),
    ("Vaka: Güvenilir Olmayan Kanıt ve Eksik Popülasyon", "Elle hazırlanmış bir raporun güvenilirliğini değerlendirerek alternatif test yaklaşımı geliştir."),
    ("Vaka: Kontrol Var Ama Çalışmıyor", "Prosedürde tanımlı olmasına rağmen uygulanmayan kontrolün tasarım ve çalışma etkinliği sonuçlarını ayrı raporla."),
    ("ISO 27001 Yönetim Sistemi Yaklaşımı", "BGYS kapsamı, kurum bağlamı, ilgili taraflar, liderlik, risk değerlendirmesi, risk işleme ve Uygulanabilirlik Bildirgesini öğren."),
    ("CISA Alanları ve Denetçi Düşünce Yapısı", "CISA sınav alanlarını, mesleki muhakemeyi, en doğru cevap yaklaşımını ve sınavla sertifika koşulları arasındaki farkı öğren."),
    ("Uygulama: BGYS Kapsamı ve Kurum Bağlamı", "Kurgusal bir şirket için BGYS kapsamı, iç ve dış konular, ilgili taraflar ve bilgi güvenliği beklentilerini hazırla."),
    ("Uygulama: Risk İşleme Planı ve Uygulanabilirlik Bildirgesi", "Riskleri ISO 27001 kontrol alanlarıyla eşleştirerek risk işleme planı ve örnek Uygulanabilirlik Bildirgesi oluştur."),
    ("Uygulama: İç Denetim ve Uygunsuzluk", "İç denetim programı, kontrol soruları, kanıtlar ve uygunsuzluk sınıflandırmasını içeren çalışma gerçekleştir."),
    ("Uygulama: Yönetimin Gözden Geçirmesi ve Düzeltici Faaliyet", "Yönetimin gözden geçirmesi girdilerini ve çıktılarını hazırlayıp kök neden ve düzeltici faaliyet planı oluştur."),
    ("Vaka: Önce Risk mi, Önce Kontrol mü?", "Kontrol listesinden başlayan yaklaşım ile riskten başlayan yaklaşımı karşılaştırarak doğru denetim sırasını savun."),
    ("Vaka: Büyük veya Küçük Uygunsuzluk", "Bir ISO 27001 senaryosunu kanıt, yaygınlık ve yönetim sistemi etkisi üzerinden sınıflandır."),
    ("NIST, CIS ve COBIT ile Yönetişim", "NIST CSF, CIS Controls ve COBIT çerçevelerinin amaçlarını, ortak noktalarını ve kullanım alanlarını öğren."),
    ("Güvenlik Operasyonları, Dayanıklılık ve Üçüncü Taraf", "Zafiyet yönetimi, olay müdahalesi, SOC, SIEM, kayıt yönetimi, yedekleme ve üçüncü taraf risklerini öğren."),
    ("Uygulama: Çerçeve Eşleştirme", "Bir şirketin kontrol ortamını ISO 27001, NIST, CIS ve COBIT beklentileriyle eşleştir."),
    ("Uygulama: Fidye Yazılımı ve Olay Kanıtları", "Bir fidye yazılımı olayında kayıtları, alarm zincirini, olay müdahalesini ve yönetim bildirimlerini incele."),
    ("Uygulama: Yedekleme, Felaket Kurtarma ve İş Sürekliliği", "RTO, RPO, yedekleme kapsamı, geri dönüş testi ve iş sürekliliği planlarını kanıtlar üzerinden değerlendir."),
    ("Uygulama: Üçüncü Taraf Durum Tespiti", "Tedarikçi anketi, sözleşme, SOC raporu, sızma testi raporu ve hizmet seviyesi taahhütlerini incele."),
    ("Vaka: Yedek Var, Geri Dönüş Testi Yok", "Yedekler başarılı görünürken geri dönüş testi yapılmamasının iş sürekliliği riskini değerlendir."),
    ("Vaka: Tedarikçi Kaynaklı Veri İhlali", "Bir hizmet sağlayıcının veri ihlalini sözleşme, şifreleme, erişim, bildirim ve üçüncü taraf gözetimi açısından incele."),
    ("Vaka: Yönetim Kuruluna Risk Raporlama", "Teknik güvenlik verilerini KPI, KRI, risk eğilimi ve iş etkisi kullanarak yönetim sunumuna dönüştür."),
    ("Uygulama: NovaBank Kullanıcı Popülasyonu", "NovaBank senaryosunda kullanıcı, yönetici hesapları ve insan kaynakları kayıtlarını karşılaştırarak erişim testi yap."),
    ("Vaka: NovaBank Eski Çalışan Hesabı", "İşten ayrılan çalışanın açık kalan hesabını kanıt, kök neden, risk ve öneri formatında raporla."),
    ("Uygulama: ExertaBank Üçüncü Taraf Veri Akışı", "ExertaBank'ın dış hizmet sağlayıcısına veri aktarımındaki sistemleri, sahipleri ve kontrol noktalarını haritala."),
    ("Vaka: ExertaBank Sınır Ötesi Veri Aktarımı", "Farklı bir ülkeye aktarılan verileri yönetişim, sözleşme, erişim ve güvenlik kontrolleri açısından değerlendir."),
    ("Uygulama: Zeugma Sigorta Taşıma Envanteri", "Zeugma Sigorta'nın sistem taşıma projesinde uygulama, veri, altyapı, bağımlılık ve kontrol envanteri oluştur."),
    ("Vaka: Zeugma Sigorta Göç Yönetimi", "Taşıma sürecindeki değişiklik, test, onay, yedekleme ve geri dönüş planı eksikliklerini denetle."),
    ("Uygulama: S3 Dışa Açıklık Testi", "Depolama alanı politikalarını, erişim izinlerini ve dışa açıklık durumunu kanıtlarla test et."),
    ("Vaka: Hassas Verinin İnternete Açılması", "Herkese açık depolama alanının iş etkisini belirleyip acil aksiyon, kalıcı çözüm ve bulgu metni hazırla."),
    ("Uygulama: CloudTrail Kayıt İncelemesi", "Yönetim faaliyetleri, oturumlar ve kritik değişiklikler için kayıt kapsamını ve saklama ayarlarını kontrol et."),
    ("Vaka: Kayıtların Kapatıldığı Güvenlik Olayı", "Kritik kayıtların olay öncesinde kapatıldığı senaryoda kanıt boşluğunu ve izlenebilirlik riskini değerlendir."),
    ("Uygulama: MFA ve Ayrıcalıklı Hesap Testi", "Yönetici hesaplarını, MFA uygulamasını, istisnaları ve ayrıcalıklı erişim onaylarını incele."),
    ("Vaka: Aşırı Yönetici Yetkisi", "İş ihtiyacından fazla yönetici yetkisine sahip kullanıcının riskini ve iyileştirme planını hazırla."),
    ("Uygulama: Güvenlik Grubu ve İnternet Erişimi", "Bulut güvenlik gruplarını inceleyerek internete gereksiz biçimde açık servisleri belirle."),
    ("Vaka: İnternete Açık Kritik Servis", "İnternete açık yönetim servisinin tehdit, zafiyet, iş etkisi ve telafi edici kontrollerini değerlendir."),
    ("Uygulama: Şifreleme, Anahtar ve Sır Yönetimi", "Şifreleme ayarlarını, anahtar sahipliğini, anahtar değişimini ve uygulama sırlarının korunmasını test et."),
    ("Vaka: Şifrelenmemiş Hassas Veri", "Şifrelenmeden saklanan müşteri verisini sınıflandırma, anahtar yönetimi, erişim ve mevzuat etkisi açısından incele."),
    ("Uygulama: Yedekleme Yapılandırması ve Geri Dönüş Kanıtı", "Yedekleme ayarlarını, başarı kayıtlarını, saklama süresini ve geri dönüş testi kanıtlarını karşılaştır."),
    ("Vaka: Başarısız Kurtarma Testi", "Hedeflenen RTO ve RPO değerlerine ulaşılamayan kurtarma testinin nedenlerini ve iş etkisini raporla."),
    ("Uygulama: Tam Denetim Çalışma Kâğıdı", "Önceki laboratuvarlardan birini seçerek amaçtan sonuca kadar eksiksiz ve referanslı çalışma kâğıdı hazırla."),
    ("Vaka: Yönetim Cevabı ve Bulgu Kapatma", "Yönetim aksiyonunun yeterliliğini değerlendirerek yeniden test ve bulgu kapatma kararını oluştur."),
    ("Denetimde Teknik İngilizce", "Kanıt talebi, risk açıklaması, bulgu görüşmesi ve toplantılarda kullanılan temel teknik İngilizceyi öğren."),
    ("Kariyer Konumlandırması ve Sertifika Yolu", "Özgeçmiş, LinkedIn, STAR yöntemi, mülakat anlatısı ve CISA ile ISO 27001 gelişim yolunu planla."),
    ("Uygulama: İngilizce Kanıt Talebi", "Kapsamı, dönemi, popülasyonu ve teslim beklentisini belirten profesyonel İngilizce kanıt talebi yaz."),
    ("Uygulama: İngilizce Bulgu ve Yönetici Özeti", "Teknik bir problemi kısa, ölçülebilir ve yönetim seviyesine uygun İngilizce bulgu metnine dönüştür."),
    ("Uygulama: Özgeçmiş ve LinkedIn Hikâyeleri", "Tamamlanan laboratuvar ve vakaları doğru biçimde özgeçmiş ve LinkedIn profiline yerleştir."),
    ("Uygulama: Mülakat ve Sertifika Çalışma Planı", "Teknik ve davranışsal mülakat soruları, CISA soru setleri ve ISO 27001 hedefleri için kişisel plan oluştur."),
    ("Vaka: Zor Paydaş ve Kapanış Toplantısı", "Bulguyu kabul etmeyen yöneticiyle kapanış toplantısı gerçekleştirerek kanıt ve risk gerekçeni savun."),
    ("Vaka: Final Denetim Hikâyesi ve Mülakat Provası", "Bir vakayı kapsam, risk, kontrol, test, kanıt, bulgu, öneri ve sonuç sırasıyla mülakat formatında sun."),
]


def lesson_day_offsets():
    """26 haftaya 3 ders; 13. ve 26. haftalara birer ek ders dağıtır."""
    offsets = []
    for week in range(1, 27):
        week_start = (week - 1) * 7
        offsets.extend((week_start, week_start + 2, week_start + 5))
        if week in (13, 26):
            offsets.append(week_start + 6)
    return offsets


assert len(LESSONS) == 80
assert len(lesson_day_offsets()) == 80
assert lesson_day_offsets()[0] == 0
assert lesson_day_offsets()[-1] == 181
