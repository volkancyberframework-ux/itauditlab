# Sabah açılan derslerde ek dosya alanı kontrolü

Mevcut 05.00 Türkiye saati `run_daily_programs` akışında, o gün erişime açılan derslerin `Course.attachment` alanı kontrol edilir. Aynı ders birden fazla öğrenciye açılırsa tek kez raporlanır; aynı gün tekrar çalıştırmada alan yeniden değerlendirilir. Önceki günün e-posta tekrarları yeni ders sayılmaz.

- Alan boşsa: `🚨 Course ID: … — Ders adı — Bu dersin ek dosya alanı boş. Derse ek dosya yüklenmemiş.`
- Alan doluysa yeterlidir. PDF, Word, Excel, ZIP, görsel, video veya uzantısız dosyalar kabul edilir.
- Dosya indirilmez; uzantısı, içeriği, storage varlığı veya HTTP erişimi kontrol edilmez. Dolu bir alan, uzak dosya erişimi sorununda da eksik eki tetiklemez.

Uyarı mevcut Telegram günlük raporunun ve e-posta özetinin ek kontrolü bölümündedir. Öğrenci bazlı detaylar Telegram'a geri eklenmez; diğer raporların kapsamı ve ders açma/e-posta akışları değişmez.

Geriye dönük iç çağrı uyumu için `course_pdf_checks` modül/fonksiyon isimleri ve `pdf_checked`, `pdf_missing`, `pdf_unverified` istatistik anahtarları korunur. Bunlar artık yalnızca alan doluluğunu ifade eder; `pdf_unverified` boş döner. Kullanıcıya gösterilen metinde PDF zorunluluğu veya HTTP doğrulama uyarısı bulunmaz.
