# Teknik ve görsel inceleme

55 ayrı teknik senaryo, 55 ayrı PNG, 55 farklı çıktı. Görseller Linux renderer'ının renk/çerçeve/font ölçüleriyle üretilir; yalnız ürün/kanıt başlığı ve SQL içeriği yeni modüle aittir. Komutlar genişliklerine göre satır kırılır; 55 görselin komut/çıktı sınırları renderer assertion'larıyla kontrol edilir. Kanıtın altında sentetik/kurgusal veri etiketi bulunur.

Teknik incelemede ayrıştırılan başlıca kavramlar:

- PostgreSQL HBA ilk eşleşen kaydı kullanır; trust ile SCRAM'ın sırası önemlidir. VALID UNTIL genel hesap bitişi değil parola süresidir. NOLOGIN ile nesne izinleri, şema sahipliği ile superuser, RLS ile BYPASSRLS ayrı tutulmuştur.
- MySQL user@host kimliği, atanmış/etkin roller, GRANT OPTION ve FILE kapsamı ayrılmıştır. secure_file_priv gereksiz FILE yetkisini iptal etmez. require_secure_transport zorunluluğu ile oturumun fiili TLS durumu karıştırılmaz. INNODB_TABLESPACES.ENCRYPTION Y/N değerleri kullanılır.
- SQL Server login/database user, sysadmin/DENY, SQL login politika bayrakları ve xp_cmdshell kapsamı ayrılmıştır. TDE TLS sağlamaz; VERIFYONLY gerçek restore değildir. Foreign key is_disabled ve is_not_trusted farklı anlamlarıyla kullanılır. Audit tanımı ile runtime hedef durumunu ayıran TARGET_CREATION_FAILED değeri üretici referansıyla doğrulanmıştır.
- Oracle DBA rolü SYSDBA ile aynı sayılmaz. Parola dosyası idari yetkileri, profil limitleri, tablespace şifreleme kapsamı ve constraint durumu ayrı kanıtlardır. Unified audit policy tanımı ile etkinliği, binary patch ile datapatch sonucu ve RMAN iş başarısı ile işlevsel geri dönüş testi ayrılmıştır.

Başarısız giriş saldırı başarısı diye sunulmaz. Şifreleme kontrolü yetkisiz kullanıcı erişimini otomatik engelliyor diye öğretilmez. Replikasyon bağımsız yedek sayılmaz. Bir ayar, tek oturum veya bir ticket bütün kurum için kesin güvence sayılmaz. Hedef RPO, politika, HR ve tarih bağlamları kanıtta belirtilir; öneriler yetkili değişiklik ve yeniden test sürecini kullanır.

Query execution sınırı: SQL örnekleri üretici şema/özellik referanslarıyla gözden geçirilmiş sentetik örneklerdir; dört veritabanı motoruna bağlanılıp yürütülmemiştir. Üretim ortamı veya gerçek kullanıcı verisi QA'ya alınmamıştır. Fiziksel iOS/Android cihaz testi yapılmamıştır; mevcut mobil renderer API sözleşmesi ve tarayıcı mobil viewport'u doğrulanır.
