# Çok kurumlu denetim konsolu

Bağımsız Django uygulaması; ITAudit ile aynı Git deposunda, ayrı servis/veritabanı/kullanıcılarla çalışır. Kurum adı, logo ve subdomain merkezi admin panelinden yönetilir. Kurum logoları veritabanında saklanır.

Ayrıntılı [kullanım ve Render kurulum kılavuzu](KULLANIM_KILAVUZU.md).

Yerel: `pip install -r requirements.txt`, `python manage.py migrate`, `python manage.py createsuperuser`, `python manage.py runserver 127.0.0.1:8765`.

Üretim: depo kökündeki `render-console.yaml`; mevcut ITAudit `render.yaml` dosyasından bağımsız Blueprint. Wildcard `*.grcustasi.com` DNS kurulumu gerekir; kök ve www ITAudit'te kalır. Kurum oluşturmak DNS API çağrısı yapmaz.

Test: `python manage.py test`. E-posta ve Telegram tekrar denemeleri: `python manage.py send_notifications`.

Gerçek yayında demo seed komutlarını çalıştırmayın. Mevcut denetim geçmişi migration ile korunur. Yeni son test onayı alanı varsayılan olarak kapalıdır; mevcut değerlendirmeler denetçi onayı bekler. Önceki bulgulara migration günü +30 gün son tarih atanır; gerçek planlara göre düzenleyin.
