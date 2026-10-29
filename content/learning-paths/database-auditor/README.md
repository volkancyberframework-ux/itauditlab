# Veritabanı Denetimi

55 özgün, görselli ve uygulamalı Türkçe denetim kararı; beş bölümde 11 soru. PostgreSQL 16: 14; MySQL 8.0: 13; SQL Server 2022: 14; Oracle Database 19c: 14. 22 başlangıç, 22 orta, 11 ileri soru. Her soru için farklı SQL/config/log/kanıt içeriği ve ayrı 2560×1440 PNG vardır. Görseller cevap ekran görüntüsü değildir; kullanıcının yorumlaması gereken teknik kanıtlardır. Gerçek kişi, müşteri verisi veya üretimden alınmış ekran kullanılmaz.

Linux modülünün aynı renk, çerçeve, tipografi, görsel önizleme, tam ekran, zoom/pan ve soru-cevap bileşenleri kullanılır. 11 soruluk bölüm oturumları kaldığı yerden devam eder. Mobil mevcut yol yüzdesini gösterir; webde yeni yola özel genel yüzde, mevcut bölüm ilerleme çubuğuyla birlikte görünür. Mevcut Linux davranışına uygun olarak doğru cevaplanan sorular kalıcı ilerlemeye işlenir; yanlışlar açıklamadan öğrenilip sonraki oturumda tekrar çalışılır. Yanlış/doğru cevaptan sonra doğru yanıt, teknik gerekçe, risk, iş etkisi ve önerilen kontrol gösterilir.

## İçerik

1. Kapsam ve erişim yönetimi: ortam kimliği, user@host, login/user ayrımı, hesap kilidi, NOLOGIN, parola bitiş kapsamı, roller ve evren tamlığı.
2. Ayrıcalıklar ve güvenlik yapılandırması: superuser/sysadmin/DBA/SYSDBA, grant option, HBA trust sırası, parola kontrolleri, FILE, sahiplik ve xp_cmdshell.
3. Şifreleme ve veri bütünlüğü: TLS ile TDE ayrımı, tablespace kapsamı, anahtar kurtarma, RLS bypass, maskeleme, foreign key ve yetim kayıtlar.
4. Loglama ve izleme: DDL/binlog/audit ayrımı, kapalı audit, etkin politika, başarısız girişler, teslim edilmeyen alarm, UTC korelasyonu, hedef yazım hatası, saklama ve transaction izleme.
5. Yedekleme ve sonuç: WAL/binlog/log backup zincirleri, RMAN ve VERIFYONLY sınırları, yama kanıtı, replika/yedek ayrımı, silme yetkileri, güncel kapanış kanıtı ve risk önceliği.

SQL sonuçları kontrollü eğitim simülasyonudur; yan satırlardaki politika/HR/ticket bilgileri bağlam kanıtıdır. Çıktı biçimi okunabilirlik için sadeleştirilmiştir. Örnek sorguların gerçek ortamlarda çalıştırıldığı veya dört farklı DB motorunda otomatik yürütüldüğü iddia edilmez. Gerekli sorgu yetkisi, ürün/edisyon lisansı, sürüm ve container/oturum kapsamı gerçek denetimde ayrıca doğrulanmalıdır. Yama sorularında güncel gerçek CVE/build iddiası yoktur; sentetik patch numaraları açıkça belirtilir.

## Yayın ve doğrulama

```sh
python content/learning-paths/database-auditor/build_content.py
python content/learning-paths/database-auditor/render_evidence.py
python manage.py seed_database_auditor_path         # dry-run
python manage.py seed_database_auditor_path --apply
python manage.py test mobile_api.test_database_auditor mobile_api.test_linux_auditor mobile_web.test_ad_web
```

0037 migration aynı importer ile yolu premium/native/web olarak yayınlar ve mevcut aktif ücretli hesaplara ilerleme kaydı açar. Gelecekte ücretli olan hesaplar ortak yayın sayesinde otomatik erişir. Diğer yolların soruları, görselleri, cevapları, ilerlemesi ve XP kayıtları güncellenmez. Tekrar çalıştırma digest/registry ile doğrulanır; yönetici değişikliğinde üzerine yazmadan durur. Ters migration yalnız yeni yolun yayınını kapatır; kullanıcı verisi silmez. Görseller PrivateVoiceStorage üzerinden mevcut yetkili API ile sunulur.

Yerel browser QA fixture: `python content/learning-paths/database-auditor/qa/serve_browser_qa.py`, ardından localhost:8766. Mock API kullanır; üretim kullanıcılarına veya ilerlemesine yazmaz.

## Teknik kaynaklar (29 Ekim 2026)

- PostgreSQL 16 HBA: https://www.postgresql.org/docs/16/auth-pg-hba-conf.html
- PostgreSQL roller: https://www.postgresql.org/docs/16/role-attributes.html
- PostgreSQL parola bitişi: https://www.postgresql.org/docs/16/sql-createrole.html
- MySQL roller: https://dev.mysql.com/doc/refman/8.0/en/roles.html
- MySQL tablespace encryption alanı: https://dev.mysql.com/doc/refman/8.0/en/information-schema-innodb-tablespaces-table.html
- SQL Server TDE kapsamı: https://learn.microsoft.com/en-us/sql/relational-databases/security/encryption/transparent-data-encryption?view=sql-server-ver16
- SQL Server audit runtime durumu: https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-objects/sys-dm-server-audit-status-transact-sql
- SQL Server VERIFYONLY: https://learn.microsoft.com/en-us/sql/t-sql/statements/restore-statements-verifyonly-transact-sql?view=sql-server-ver16
- Oracle unified audit policy: https://docs.oracle.com/en/database/oracle/oracle-database/19/dbseg/configuring-audit-policies.html
- Oracle etkin audit görünümü: https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/AUDIT_UNIFIED_ENABLED_POLICIES.html
- Oracle SQL patch sonucu: https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/DBA_REGISTRY_SQLPATCH.html
