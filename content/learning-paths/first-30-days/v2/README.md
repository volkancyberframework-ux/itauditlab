# İkinci sürüm: roller, döngü, öğretici kartlar ve ses

Kullanıcının yeni isteği önceki şartnamenin gerçek ses üretmeme kuralını değiştirir. Bu sürüm 10 gerçek, Türkçe yapay ses kaydı içerir. Kayıtlar installed Yelda ve Cem sesleriyle oluşturulmuş, iki konuşmacı sesi kullanılmıştır. Her biri yaklaşık 2,5–3 dakika; süreler audio_report.json'da bulunur. İnsan kaydı oldukları iddia edilmez. Metinler transcript_01.txt … transcript_10.txt.

100 kayıt ve 10 bölüm korunur. Her bölümün sırası: audio, multi_select, sentence_order, drag_select, fill_blank, image, scenario, choice, scenario, info. İlk oturumda ilk 8 farklı görev biçimi görünür. Sesli cevap kaydı ve anlamsal serbest yazı değerlendirmesi eklenmez; dinleme görevi gerçek ses + karar seçimi kullanır.

Karakterler: Selin (Yöneticin), Murat (IT Operasyon Müdürü), Deniz (Bilgi Güvenliği Yöneticisi), Ece (Risk Müdürü), Arda (SOC Ekip Lideri), Ayşe (CEO / Genel Müdür). Rol etiketleri bağlam, soru, şık, açıklama ve ders metinlerinde gösterilir. İlk günün geçişleri ve bölüm kartlarının sonraki bölüme bağlantıları güçlendirildi.

10 bilgi kartında 4'er sayfa: kavram, NEXORA örneği, uygulama yaklaşımı, işte dikkat edilecek hata ve sonraki adım. 40 sayfa toplam. 10. bölüm, planlandı/uygulandı/doğrulandı ayrımıyla önceki aksiyonların durumunu açıklar.

Sabit soru kimlikleri, yanıt anahtarları ve bölüm kimlikleri aynı kalır. 0031 migration'ı yalnız yol 26'daki doğrulanmış paketi değiştirir. Yanıt, XP veya tamamlanmış soru kaydı silmez. Aktif oturumlarda yalnız cevaplanmamış pozisyonlar yeni sıraya göre düzenlenir. Önceki alanlar preferences.first30_v2.backup içinde saklanır. Kullanıcı tarafından elle değiştirilen kayıt bulunduğunda otomatik overwrite yapılmaz.

    python manage.py revise_first30
    python manage.py revise_first30 --apply
    python manage.py revise_first30 --rollback --apply

İlk komut dry-run'dır. Geri alma, eski içeriği geri koyar; kullanıcı verisini veya ses dosyalarını silmez. Yeniden uygulama kayıt çoğaltmaz. Sesler ve ilk gün erişim tablosu immutable bundled PrivateVoiceStorage üzerinden yetkili API ile sunulur. Render pre-deploy sırasında özel diske erişim gerekmez.

Testler: 10 Django testi (ilk sürüm + revizyon) başarılı; 10 Flutter testi revizyonun ilk 10 görevini telefon genişliğinde doğruladı. İlk ses görevinin dinleme düğmesi, seçim/sıralama/sürükleme/yazma arayüzleri ve 4 sayfalık kart render edildi. Ses indirme, MP3 başlığı, MIME, Range isteği ve anonim erişim reddi Django API testinde doğrulandı. 100 kayıt gerçek API'den döngü sırasında tamamlandı. Geri alma, tekrar uygulama ve öğrenci ilerlemesini koruma doğrulandı.
