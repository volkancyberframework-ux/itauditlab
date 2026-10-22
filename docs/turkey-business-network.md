# Türkiye canlı iş ağı

Ana sayfada kariyer pusulasının altında yer alır. 81 il, `BusinessNetworkCity` tablosunda plaka koduyla tutulur. İlk kurulumda İzmir, İstanbul, Ankara, Çorum, Sinop, Samsun, Hatay, Adana, Manisa, Aydın ve Kütahya aktiftir. Tekrar çalışan veri migrasyonu yönetici seçimlerini değiştirmez.

Yönetim: `/admin/core/businessnetworkcity/` (CORE → Türkiye İş Ağı Yönetimi). Model değiştirme yetkisi olan personel, haritadan veya liste düğmelerinden durum değiştirir. CSRF korumalı PATCH işlemi atomiktir; editör, zaman ve Django yönetim işlem kaydı tutulur. Şehir ekleme/silme kapalıdır.

Genel API: `/api/business-network/cities/`, `/api/business-network/stats/`. GET işlemleri veri değiştirmez, editör bilgisi yayımlanmaz, yanıtlar önbelleğe alınmaz. Sayaç veritabanından hesaplanır. Açık sayfa görünürken 60 saniyede yenilenir. Eksik veri veya veritabanı hatasında uydurma sayı gösterilmez.

8 dil yerel JSON içerir; mevcut dil değiştiricisi ve Arapça RTL ile çalışır. Harita coğrafi yönünü korur. Tüm 81 ilde hover, dokunma ve Enter/Space ile iletişim açılır. Enter e-posta bağlantısına odaklanır, Escape kapatır. E-posta göndermek otomatik değildir; mailto bağlantısı kullanılır. Hareket azaltma tercihi desteklenir.

## Sınır verisi

Kaynak: https://github.com/theaiagent/turkiye_iller_geojson — `turkiye_iller.geojson`, 22 Ekim 2026 tarihinde alındı. Kaynak README'sine göre cihadturhan/tr-geojson ve OpenStreetMap türevi, ODbL 1.0. Dosya geometri sadeleştirmeden, Polygon/MultiPolygon ve tüm halkaları korunarak sunulur. SVG Web Mercator projeksiyonu kullanır. Atıf, indirilebilir GeoJSON ve lisans haritada yer alır. Genel görselleştirme amaçlıdır.

## Doğrulama

170 Django testi başarılı: ağ verisi, izinler, CSRF, idempotent kurulum ve durum değişimi, hata davranışı; mevcut dil, fiyat, mevzuat, hukuk, takvim ve misafir akışı regresyonları dahil. Migrasyon sapması yok; JavaScript sözdizimi ve static toplama başarılı.

Tarayıcı: 8 dil × 2 tema × 3 genişlik (320, 768, 1440) = 48 kombinasyon; 81 sınır, 11 aktif il, doğru pasif durum ve mailto, sıfır yatay taşma. Ayrıca 81 ilin tamamında iletişim kutusu ve klavyeyle e-posta odağı doğrulandı; mobil e-posta dokunma alanı en az 44 px.

Dağıtım normal migrate ve collectstatic akışıyla yapılır. Geri dönüşte tabloyu/veriyi silmeden önceki uygulama sürümüne dönülebilir; 0031 ters işlemi mevcut il durumlarını silmez.
