# Telegram özeti ve geçici 7 günlük grafik

Mevcut 05:00 İstanbul günlük komutu ve alıcıları korunur. `format_daily_program_summary` varsayılan olarak eskisi gibi öğrenci/ders detaylarını içerir; e-posta ve komut çıktısı aynı tam raporu kullanır. Yalnız Telegram çağrısına `include_student_details=False` ile oluşturulan özet verilir. PDF alarmları ve mobil KPI özeti (en aktif 5 dahil) korunur. Trafik, görüşme, haftalık not ve öğrenci izleme raporları değiştirilmez.

Mobil KPI özeti hazırsa Telegram metninin ardından dört panelli PNG fotoğraf gönderilir: aktif öğrenci, soru yanıtı, otomatik değerlendirmede doğruluk, tamamlanan çalışma oturumu. Grafik rapor sabahından önceki son yedi tamamlanan günü gösterir; kısmi gün yoktur. Son gün vurgulanır; başlık ve fotoğraf açıklaması o günün değerini bir önceki günle karşılaştırır.

Yedi günün günlük snapshot'ları kullanılır; henüz snapshot yoksa aynı KPI kurallarıyla mevcut etkinlik kayıtları okunur. Grafik sorgusu yedi günlük pencereyle sınırlıdır. Eski etkinlik/snapshot kayıtları veya diğer rapor geçmişi silinmez; yalnız grafik için daha eski günler kullanılmaz.

PNG `BytesIO` ile yalnız bellekte üretilir. Dosya sistemine, media klasörüne, veritabanına veya başka depoya grafik yazılmaz. `with` bloğu Telegram sendPhoto başarılı olsa da HTTP/ağ/API hatası olsa da görüntü buffer'ını kapatır. Renderer hatasında da buffer kapatılır ve figure temizlenir. Telegram'a gönderilen mesaj kullanıcının görüntülemesi için kalır; sunucuda grafik arşivi oluşmaz. Yeni bir sonraki grafikte önceki PNG tutulmaz.

Grafik üretimi/gönderimi hatası e-posta veya diğer raporları engellemez. E-posta raporuna yeni ek eklenmez; mevcut detaylı metin korunur. Bot ayarları yoksa grafik üretilmez.

Doğrulama: 42 test (mobil KPI, 7 günlük veri penceresi, gerçek PNG üretimi, boş doğruluk, buffer temizliği, kanal ayrımı, grafik hatasında diğer raporların devamı, PDF ve haftalık rapor regresyonu). Görsel QA sentetik verilerle yapıldı; QA PNG'si inceleme sonrası silindi. Gerçek Telegram alıcısına test grafiği gönderilmedi.
