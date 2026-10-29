# Günlük mobil KPI bölümü

Mevcut `run_daily_programs` sabah Telegram/e-posta sayacına eklenir; yeni zamanlayıcı, yeni alıcı veya öğrenciye yeni mesaj yoktur. PDF uyarılarından sonra, öğrenci bazlı ders açılış detaylarından önce görünür.

## Dönem ve hesap sayımı

İstanbul saatine göre sabah D raporu tamamlanmış D−1 gününü D−2 ile karşılaştırır. Gün aralığı yerel 00:00 dahil / sonraki 00:00 hariçtir; sabahın kısmi günü tam günle karşılaştırılmaz. Kayıtlı hesap/tam erişim hakkı sayımı raporun alındığı andaki durumdur ve bu saat mesajda gösterilir. Toplam öğrenci farkı önceki sabahın gerçek snapshot'ıyla karşılaştırılır; ilk ölçümde artış uydurulmaz.

Öğrenci evreni `is_mobile=True`, `is_staff=False`, `is_superuser=False` hesaplarıdır. Web tarayıcısından aynı mobil hesapla yapılan çalışma da dahildir; cihaz türüne göre native/web ayrımı yapılmaz. Kayıtlı toplam, kapalı hesapları da içerir; açık/kapalı ayrıca gösterilir. Tam erişim hakkı; geçerli süreli, manuel ömür boyu ve mevcut premium kuralındaki geçerli active/trial/grace mağaza üyeliklerini kapsar. Bu sayı tahsil edilmiş ödeme sayısı değildir. Erişim tarihi geçmiş hesaplar ayrı sayılır; doğrulama bekleyenler ayrı gösterilir. Erişim hakkı, zorunlu e-posta/ilk şifre kontrollerini kaldırmaz.

`Yeni hesap` kayıt tarihi (`date_joined`) D−1 içinde olan mobil öğrenci hesaplarıdır. Önceden var olan bir web hesabına mobil yetki verilmesinin ayrı etkinleştirme tarihi tutulmadığından bu işlem yeni kayıt sayılmaz; toplam hesap farkında görünebilir.

## Aktivite tanımları

- Aktif: AnalyticsEvent, gerçek LearningSession açılışı/tamamlanması, QuestionAttempt veya VoiceSubmission kaydı olan tekil öğrenci. Tekrarlı istemci eventleri öğrenci sayısını çoğaltmaz. Sessiz/gönderilmeyen istemci etkinliği ölçülemez; rapor bunu kayıtlı etkinlik olarak niteler.
- Soru çözen: info dışı QuestionAttempt kaydı olan tekil öğrenci. Yanıt sayısı tekrarları içerir; bilgi kartları ayrı sayılır.
- Doğruluk: choice/multi_select/fill_blank/image/audio/scenario/sentence_order/drag_select türlerinde doğru/otomatik değerlendirilen yanıt. Info, sesli ve serbest metin oranı bozmaz. Değerlendirme yoksa oran sıfır değil `—` olur. Fark yüzde puan olarak gösterilir.
- Süre: istemcinin yanıtla bildirdiği süre, her yanıt için en fazla 600 saniye; tahmini süre olarak etiketlenir. Arka planda uygulama açık kaldığı süre ölçülmez.
- Tamamlanan oturum: completed_at rapor günündedir. Arşivlenmiş/yeniden başlatılmış eski oturumlar geçmişte gerçekleşen çalışma olduğu için hariç bırakılmaz.
- Net XP: günün attempt.xp_change toplamı; negatif pratik puanları dahil.
- Son 7 gün aktif: rapor günü dahil yedi kapalı günde tekil kayıtlı aktivite. Etkinliksiz eski hesap: açık, hesabı yedi günden eski, bu dönemde kaydı bulunmayan hesap.
- Yeni aktif/etkinliği kesilen: önceki gün ile rapor gününün tekil aktivite kümeleri farkı. Yeni aktif, ilk kez kullanan anlamına gelmez; önceki gün kaydı yokken rapor gününde kaydı olan kişidir.
- Geri dönüş: önceki kapalı gün aktif olanlardan rapor gününde de aktif olanlar / önceki gün aktifleri.
- İlk 5: gün içinde yanıtlanan farklı question ID sayısı azalan; eşitlikte yanıt sayısı, sonra user ID. Tek soruyu tekrar tekrar çözmek farklı soru sıralamasını şişirmez. Satırda farklı soru/yanıt, doğruluk, süre, çalışılan oturum ve XP bulunur.
- Popüler ilk 3 yol: soru çözen tekil öğrenci, sonra yanıt sayısı. Bilgi kartı veya sırf yol atama sayısı değildir.

UserPathProgress.last_activity, toplu atama ve ders yayınlama işlemleri gerçek kullanım kanıtı sayılmaz. Kullanıcının ders erişimi/ilerlemesi/XP'si rapor tarafından değiştirilmez.

## Snapshot ve hata davranışı

`MobileDailyKPI` rapor tarihi tekil JSON snapshot'ı tutar. Aynı sabah tekrar çalıştırma ikinci ölçüm üretmez; önceki günün KPI referansı sonradan değişmez. Öğrenci adları/e-postaları snapshot içine yazılmaz; top user ID'leri ve metrikler tutulur, görüntülemede mevcut ad okunur. Ad yoksa/eposta biçimindeyse yalnız Öğrenci + ID gösterilir. Yönetim paneli salt okunur raporları gösterir.

KPI üretimi başarısız olursa aynı sayaca uyarı eklenir; mevcut ders, PDF, e-posta, trafik ve görüşme akışları devam eder. Rapor, öğrenciler için otomatik yaptırım veya mesaj üretmez.

Kontroller: 31 test; kapalı gün/saat dilimi, personel dışlama, event tekilleştirme, arşivli geçmiş, sesli/serbest metin doğruluğu, süre sınırı, üyelik kapsamı, ilk ölçüm, snapshot tekrar güvenliği, sıralama, mevcut sayaç entegrasyonu ve hata izolasyonu. Komut: `python manage.py test mobile_api.test_daily_kpis core.test_course_pdf_checks core.tests.DailyProgramAutomationTests core.test_weekly_notifications`.
