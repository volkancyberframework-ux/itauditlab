# kurumsal.grcustasi.com yönlendirmesi

Kurumsal landing page aynı Django/Render servisi içinde çalışır. Uygulama `Host` başlığı
`kurumsal.grcustasi.com` olduğunda kurumsal template'i gösterir; `/kurumsal/` adresi de
önizleme ve test rotası olarak kullanılabilir.

## Render

1. Render Dashboard → `core` web service → **Settings → Custom Domains** bölümüne gidin.
2. `kurumsal.grcustasi.com` alan adını ekleyin.
3. Render'ın gösterdiği CNAME hedefini kopyalayın.

## DNS

Alan adı sağlayıcınızda `kurumsal` adıyla bir **CNAME** kaydı oluşturun ve hedef olarak
Render'ın verdiği adresi kullanın. Aynı ad için eski A/AAAA/CNAME kaydı varsa çakışmayı
giderin. DNS yayıldığında Render TLS sertifikasını otomatik üretir.

Uygulamada `ALLOWED_HOSTS` ve `CSRF_TRUSTED_ORIGINS` ayarları hazırdır. Formların çalışması
için yeni bir environment variable gerekmez; kayıtlar PostgreSQL veritabanına yazılır ve
mevcut `TELEGRAM_BOT_TOKEN` ile `TELEGRAM_CHAT_ID` tanımlıysa Telegram bildirimi gönderilir.
