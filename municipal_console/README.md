# Torbalı Belediyesi denetim konsolu

Bağımsız Django 5.2 uygulaması. ITAudit ile aynı Git deposunda tutulabilir; aynı Django sürecine veya veritabanına eklenmez.

## Yerel

Python sanal ortamında `pip install -r requirements.txt`, `python manage.py migrate`, `python manage.py runserver 127.0.0.1:8765`.
Demo için yalnızca DEBUG ortamında `python manage.py seed_workflow`; gerçek yayında demo seed komutlarını çalıştırmayın.

## Üretim

Render servis root directory: `municipal_console`. Ayrı PostgreSQL, ayrı SECRET_KEY, ayrı kullanıcılar.
`config.settings`, `accounts.User` ve `municipal_sessionid`/`municipal_csrftoken` çerezleri kullanılır; host-only çerezler. ITAudit `core.CustomUser` ve veritabanı değişmez.

İlk kurulumda `python manage.py provision_torbali`, `python manage.py createsuperuser` çalıştırın.
`/admin/` → kurumlar: subdomain (yalnızca etiket, örn. torbalibld).
`/admin/` → kullanıcılar: bağımsız konsol hesapları; üyelikler: denetim ve rol ataması; kontroller: soru ve test/kanıt rehberi.
Yeni kullanıcının ilk girişte parolasını değiştirmesi gerekir.

Subdomain kaydı DNS oluşturmaz. Render özel alan adı ve DNS ayarları tamamlanmalı; wildcard kurulduğunda yeni kurum adresleri panelden yönetilebilir. Tanımsız *.grcustasi.com adresleri 404 döner.

## İşleyiş

1. BT yanıtları
2. Saha denetimi ve onaylı randevu
3. Bulguların giderilmesi
4. Sürekli kontrol: yeni yanıt sürümleri, değerlendirme, bulgu ve öneriler devam eder.

Kontroller ve bulgular PDF indirilebilir. Grafikler gerçek güncel kayıtlardan oluşturulur. Stajyer PDF'i yalnızca yetkili kontrol tanımlarını içerir; BT PDF'inde denetçi değerlendirmesi bulunmaz.

Telegram: `GRCUSTASI_TELEGRAM_BOT_TOKEN` ve `GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID` ortam değişkenlerini tanımlayın. Girişler ve uygulamadaki denetim işlemleri commit sonrası gönderilir. Başarısız bildirimler saklanır; `python manage.py send_notifications` ile tekrar denenir. Merkezi yönetimde bildirim kayıtları incelenebilir. Cron kurulmazsa otomatik periyodik tekrar gerçekleşmez. İletişim hatasında tekrar gönderim nadiren mükerrer mesaj doğurabilir.

Test: `python manage.py test`.
