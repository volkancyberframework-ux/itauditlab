# Çok kurumlu denetim konsolu

Bağımsız Django uygulaması; ITAudit ile aynı Git deposunda, aynı Render servisi ve PostgreSQL üzerinde, ayrı kullanıcı ve oturum tablolarıyla çalışır. Kurum adı, logo ve subdomain merkezi admin panelinden yönetilir. Kurum logoları veritabanında saklanır.

Ayrıntılı [kullanım ve Render kurulum kılavuzu](KULLANIM_KILAVUZU.md).

Yerel: `pip install -r requirements.txt`, `python manage.py migrate`, `python manage.py createsuperuser`, `python manage.py runserver 127.0.0.1:8765`.

Üretim: mevcut Render servisi otomatik olarak `/denetim/` yolunu açar. Merkezi yönetim `/denetim/admin/`: mevcut aktif ITAudit süper yöneticisinin e-postası ve ilk kurulumdaki parolası geçerlidir. Yeni veritabanı veya servis oluşturmayın. Wildcard DNS yalnızca kuruma özel subdomain kullanımı için gereklidir.

Test: `python manage.py test`. E-posta ve Telegram tekrar denemeleri: `python manage.py send_notifications`.

Gerçek yayında demo seed komutlarını çalıştırmayın. Mevcut denetim geçmişi migration ile korunur. Yeni son test onayı alanı varsayılan olarak kapalıdır; mevcut değerlendirmeler denetçi onayı bekler. Önceki bulgulara migration günü +30 gün son tarih atanır; gerçek planlara göre düzenleyin.
