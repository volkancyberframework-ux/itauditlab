# Torbalı konsolu — ITAudit deposunda bağımsız yayın

## Ayrım

Mevcut `render.yaml`, `itaudit/`, `core/`, `landing/` ve `skool/` değişmedi.
Yeni uygulama `municipal_console/` altında. Ayrı servis, PostgreSQL, SECRET_KEY ve auth tabloları kullanır. ITAudit hesabı konsola giriş sağlamaz. Mevcut veritabanını yeni servis için kullanmayın.
Yeni uygulamada `/admin/` merkezi yönetimdir. ITAudit'in `/admin/` alanından bağımsızdır.

## Render

1. Bu Git deposu yayımlandıktan sonra Render'da **New → Blueprint** ile depoyu seçin. Blueprint dosya yolu `render-console.yaml` olsun. Mevcut `render.yaml` Blueprint'ini değiştirmeyin. Yeni servisler ücretli kaynak içerir; Render fiyat özetini kontrol edin.
2. Yeni `municipal-console` servisi ve yalnızca ona ait `municipal-console-db` oluşur. `municipal-notification-retry` cron'u bekleyen mesajları 5 dakikada bir dener.
3. Yeni servis için mevcut botun `GRCUSTASI_TELEGRAM_BOT_TOKEN` ve `GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID` değerlerini Render Environment'a girin. Değerleri Git'e koymayın. Bot webhook'u değiştirilmez; ITAudit bildirimleri etkilenmez.
4. Render Shell: `python manage.py provision_torbali` ardından `python manage.py createsuperuser`. Gerçek bağımsız yönetici hesabı oluşturulur; yerel demo parolası veya verileri yayına kopyalanmaz.
5. Yönetim panelinde kullanıcılar, denetim üyelikleri ve kontroller eklenir. Yeni kullanıcıların rolü Membership üzerinden belirlenir. Konsol kullanıcısı için `is_staff` gerekmez.

## torbalibld.grcustasi.com

Render subdomain destekler. **Yeni web servisinin Settings → Custom Domains → Add Custom Domain** alanına yalnızca `torbalibld.grcustasi.com` yazın; `https://` veya yol eklemeyin. Render servisinin kendi `*.onrender.com` adını değiştirmek farklı bir ayardır.

DNS yönetimi GoDaddy nameserver'larında görünüyor. grcustasi.com DNS panelinde:

| Tür | Ad / Host | Hedef |
| --- | --- | --- |
| CNAME | torbalibld | Yeni servisin Render panelindeki gerçek `….onrender.com` adresi |

Hedefi tahmin etmeyin; Render'dan kopyalayın. Aynı `torbalibld` etiketi için çakışan A/AAAA/CNAME kaydı bulunmamalı. Kök alanın ve www'nin mevcut ITAudit kayıtlarını değiştirmeyin. Render'a dönüp Verify seçin; sertifika hazırlanmasını bekleyin.

“İzin vermiyor” hatasının tam metni görülmedi. Alan başka servise atanmış olabilir, yanlış ekranda işlem yapılıyor olabilir veya DNS doğrulaması bekliyor olabilir; kesin neden henüz doğrulanmadı.

## Merkezi subdomain yönetimi

Konsol `/admin/` → Organizations → subdomain: `torbalibld` (tam URL değil). Kurum slug'ı veri kimliğidir, adres değişikliği için değiştirilmesi gerekmez. Tanımsız kurum adresleri 404 döner; kurumlar birbirinin denetimlerini göremez.

Bu alan uygulama yönlendirmesini değiştirir, DNS/Render API çağrısı yapmaz. Tekil DNS kurulumunda yeni adresi ayrıca Render ve DNS'e ekleyin. Eski adresi panelde değiştirmek onu hemen geçersiz kılar.

Çok sayıda subdomain için yeni servise `*.grcustasi.com` özel alan adı tanımlanabilir. Render'ın verdiği **tam değerlerle** şu üç CNAME gerekir: `*`, `_acme-challenge`, `_cf-custom-hostname`. Kök alanın da Render'a yönlenmesi gerekir. Mevcut kök/www ITAudit servisini taşımayın; Render panelinde kökün mevcut serviste kalması ve wildcard'ın yeni servise atanması doğrulanmalıdır. Bu doğrulanmadan wildcard DNS değişikliği yapmayın. Wildcard etkin olunca yeni kurum etiketleri yalnızca merkezi panelden atanabilir.

Resmî kaynaklar: https://render.com/docs/custom-domains ve https://render.com/docs/configure-other-dns

## Yayın sonrası kontrol

Konsol login, ilk parola değişikliği, kurum üyeliği, her rolün görünümü, PDF indirme ve Telegram teslim kaydı kontrol edilir. Sürekli kontrol fazında yanıtlar yeni sürüm olarak saklanır; denetçi uygunsuzluk kaydederse bulgu açılır/yeniden açılır. Gerçek denetimde demo seed komutları çalıştırılmaz.

## Git

Yalnızca `municipal_console/`, `render-console.yaml` ve bu belge bu entegrasyona aittir. Depoda daha önce bulunan .DS_Store değişiklikleri, rapor taslakları, output/ ve tmp/ bu değişikliğin dışındadır. Veritabanı, sanal ortam ve sırlar eklenmez. Push henüz yapılmadı.
