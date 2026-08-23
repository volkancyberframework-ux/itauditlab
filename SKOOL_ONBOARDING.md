# GRC Ustası Skool onboarding sistemi

## Akış

Sistem `/skooltoplulugu` adresinde çalışır. Davet bağlantısı olmadan isim doğrulaması yapılamaz.
Davet tokenının yalnızca SHA-256 özeti veritabanında tutulur. Başarılı doğrulamadan sonra uzun ömürlü,
HTTP-only Django oturumu kullanılır ve süreç şu sırayla ilerler:

`Davet → İsim doğrulama → 24 soruluk test → Ses kaydı → 90 dakika görüşme`

## Telegram daveti

Bot yalnızca `TELEGRAM_ADMIN_CHAT_ID` tarafından gönderilen komutları kabul eder:

- `/create Ad Soyad` veya `create Ad Soyad`
- `/status Ad Soyad`
- `/revoke Ad Soyad`

Webhook kurulumu:

```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=https://grcustasi.com/api/skool/telegram/" \
  -d "secret_token=${TELEGRAM_WEBHOOK_SECRET}"
```

`TELEGRAM_WEBHOOK_SECRET` rastgele ve en az 32 karakter olmalıdır. Ham davet tokenları loglanmaz.

## Ses kaydı

Yönetim panelindeki **Skool ayarı** kaydına doğrudan MP3/M4A adresi girin. Doğrudan oynatılabilen
MP4 adresi `video_url` alanında ses kaynağı olarak kullanılabilir ve görüntü gösterilmez. YouTube gibi
platformlardan ses indirme veya ayırma yapılmaz. Kullanıcı doğrulanan sürenin en az yüzde 80'ini
dinlemeden üçüncü aşamaya geçemez.

## Uygunluk ve zaman dilimleri

Yönetim panelinde **Seyahat ve uygunluk** kaydı oluşturun. Zaman dilimini UTC offset yerine IANA adıyla
girin (`Asia/Ho_Chi_Minh`, `Europe/Brussels`). Saatler bulunduğunuz yerin yerel saatidir. Sistem slotları
yerel zamanda üretir, UTC olarak saklar ve kullanıcıya daima `Europe/Istanbul` saatinde gösterir.

Her gün için üç adet, 90 dakikalık ve çakışmayan slot ilk erişimde rastgele üretilir ve veritabanında
kalıcı tutulur. Sayfa yenilemek slotları değiştirmez. Slotları önceden üretmek için:

```bash
python manage.py generate_skool_slots
```

Bir tarihi veya aralığı **Uygunluk istisnası** ile kapatabilirsiniz. Var olan rezervasyonlar silinmez;
yönetim panelindeki aktif görüşmeler kontrol edilmelidir.

## Rezervasyon ve yeniden planlama

Bugün için rezervasyon yapılamaz. Kullanıcı yalnızca bir aktif görüşme alabilir. Slot alma ve yeniden
planlama işlemleri transaction ve satır kilitleriyle korunur. Görüşmeye 24 saat veya daha az kaldığında
sistem üzerinden değişiklik engellenir. Meet bağlantısının tek kaynağı Skool ayarı veya ilk kurulumda
`SKOOL_GOOGLE_MEET_URL` değişkenidir.

## Günlük Telegram özeti

Render'daki `skool-meeting-digest` görevi 15 dakikada bir komutu çalıştırır. Komut, aktif seyahat
konumunda yerel saat 09:00 olduğunda o günün görüşmelerini tek mesajda gönderir. `NotificationLog`
anahtarı aynı günün mesajının ikinci kez gönderilmesini önler.

## Yönetim

- Özel panel: `/admin/skool/`
- Kullanıcı görüşme hazırlığı: `/admin/skool/users/<id>/`
- Ayrıntılı model yönetimi: `/bulamazsinki/`

Bu ekranların tamamı Django staff authentication gerektirir. Kariyer cevapları public değildir.

## Gerekli ortam değişkenleri

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_CHAT_ID=
TELEGRAM_WEBHOOK_SECRET=
# Aynı bot başka bir uygulamada webhook kullanıyorsa BotFather üzerinden GRC
# Ustası için ayrı bot açın. Bir Telegram botu yalnızca tek webhook kullanabilir.
GRCUSTASI_TELEGRAM_BOT_TOKEN=
GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID=
GRCUSTASI_TELEGRAM_WEBHOOK_SECRET=
PUBLIC_BASE_URL=https://grcustasi.com
SKOOL_GOOGLE_MEET_URL=https://meet.google.com/jbv-csdm-eyy
SKOOL_AUDIO_URL=
SKOOL_MEETING_DURATION_MINUTES=90
SKOOL_DAILY_SLOT_COUNT=3
SKOOL_MINIMUM_GAP_MINUTES=15
SKOOL_DISPLAY_TIMEZONE=Europe/Istanbul
```

`DATABASE_URL` ve `SECRET_KEY` mevcut servisle aynıdır.

Render web servisine bu değerleri ekledikten sonra webhook'u kurup doğrulayın:

```bash
python manage.py configure_skool_telegram_webhook
```

## Deployment

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check --deploy
python manage.py test skool landing core
```

Migrationlar yalnızca yeni tablolar ve alanlar ekler; mevcut öğrenci, eğitim ve enrollment tablolarına
destructive değişiklik yapmaz. Production'da örnek veri otomatik oluşturulmaz.
