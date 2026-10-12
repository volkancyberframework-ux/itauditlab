# Kullanıcının kendi kayıtları — 12 Ekim 2026

Kaynak: masaüstü /sesler klasöründeki DJI_29 … DJI_38 WAV dosyaları. Dosya adlarındaki üretim zamanı sırasıyla bölüm 1 … 10'a eşlendi. Orijinaller korunarak aynı klasöre grc_day_01.mp3 … grc_day_10.mp3 üretildi.

FFmpeg atempo=1.2 ile süre %16,67 kısaldı; ses perdesi korunur. MP3, 44.100 Hz, 128 kbit/s. On dosyanın tamamı decode edildi; çıkış süreleri kaynak/1.2 değerine 0,15 saniye toleransla uydu. Kaynak/çıkış adı, süre ve SHA-256 manifest.json içinde.

0032 veri migration'ı yalnız yol 26'nın 10 audio sorusunun audio bağlantısını değiştirir. Yeni AudioAsset kimlikleri yeni URL oluşturur; cihazda eski yapay sesin önbelleği kullanılmaz. Soru kimlikleri, metinler, cevaplar, ilerleme ve puanlar değişmez. Önceki ses bağlantıları preferences.first30_recorded_20261012.previous_audio_ids içinde saklanır. İdempotent işlem tekrar kayıt üretmez; ters migration yalnız eski ses bağlantılarını geri koyar.

Özel sesler immutable bundled PrivateVoiceStorage ile yetkili API'den sunulur. Yeni dosya alanı first30-recorded-20261012; eski first30-v2 alanına veya kullanıcının sonradan yüklediği başka dosyaya yazılmaz.

Doğrulama: 2 Django testi başarılı. 10 sesin özel indirme endpointi HTTP 200/audio-mpeg ve gerçek MP3 baytlarını döndürdü. Dry-run, iki kez uygulama, geri alma, yeniden uygulama; mevcut cevap, puan ve tamamlanan soru kaydının korunması doğrulandı. Yerel gerçek migration başarılı.
