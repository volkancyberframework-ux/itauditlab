# Sabah açılan derslerde PDF kontrolü

Mevcut `python manage.py run_daily_programs` akışında çalışır. Yeni bir zamanlayıcı veya alıcı yoktur. Takvim `render.yaml` içinde 02:00 UTC / 05:00 İstanbul olarak tanımlıdır; mevcut üretim zamanlaması değiştirilmez.

O çalışmada yeni erişim verilen dersler ve aynı yerel günde daha önce açılmış ProgramRelease kayıtları kontrol edilir. Böylece aynı gün yeniden çalıştırmada Telegram/erişim kontrolü yeniden yapılabilir; bir önceki günün yalnız e-posta tekrarı bugünün PDF alarmına eklenmez. Aynı course birden çok öğrenci/programda açılsa da tek kontrol ve tek uyarı satırı olur. Alarmda Course.pk ve Course gerçek adı kullanılır; e-posta başlığı takma adı kullanılmaz.

- Ek alanı boşsa: `🚨 Course ID: … — Ders adı — Bu derste PDF yok. Derse ek dosya yüklenmemiş.`
- Dosya 404/410 ise: aynı alarm; dosya bulunamadığı açıklanır.
- PDF adı taşısa da PDF başlığı yoksa: PDF formatında değil alarmı.
- Timeout, 5xx, erişim/redirect veya HTML sayfası sonucu: PDF yok denmez; `⚠️ PDF KONTROLÜ DOĞRULANAMADI` ayrı bölümünde Course ID/ad gösterilir.
- PDF dosyasının başlığı doğrulanır; tüm PDF içeriği veya tam yapısal bütünlüğü analiz edilmez.

Scheduled worker'ın web servisine ait `/data/media` diski yoktur. Bu nedenle `storage.exists()` ile yanlış eksik alarmı üretmek yerine, öğrencinin kullandığı storage URL'sinden ilk en fazla 1024 bayt kontrol edilir. Range ve streaming kullanılır; dosya bütünü indirilmez. En fazla dört paralel kontrol ve bağlantı/okuma timeout'u vardır. URL/token veya ham istisna metni rapora yazılmaz. PDF kontrolündeki erişim hataları öğrenci erişimi ve e-posta akışını durdurmaz.

Uyarı, `format_daily_program_summary` ile oluşturulan mevcut Telegram raporunun içinde, öğrenci detaylarından önce yer alır. Mevcut e-posta özetinin aynı mesajı kullanması korunur. Kullanıcıya yeni mesaj türü veya öğrencilere ayrı PDF uyarısı gönderilmez.

Doğrulama: `python manage.py test core.test_course_pdf_checks core.tests.DailyProgramAutomationTests core.test_weekly_notifications`. Testlerde Telegram, SMTP ve dosya HTTP erişimi mock edilir; gerçek alıcılara test mesajı gönderilmez.
