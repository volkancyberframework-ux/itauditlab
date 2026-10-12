# İşe Alındın! İlk 30 Günün — merkezi senaryo

Bütün şirket, kişi ve kanıtlar kurgusaldır. NEXORA: 2.400 çalışan, 1,8 milyon müşteri. Oyuncu Junior GRC Specialist; iç denetçi değildir. GRC rehberlik/gözetim rolü ile iç denetimin bağımsız güvence rolü ayrıdır.

| Kişi | Sabit görev |
|---|---|
| Selin | GRC yöneticisi; oyuncunun yöneticisi |
| Murat | IT operasyon müdürü |
| Deniz | CISO |
| Ece | Risk müdürü |
| Arda | SOC lideri |
| Ayşe | CEO |

NEX-PAY ödeme hizmeti, NEX-LEDGER mutabakat sistemi. svc-pay-prod ödeme hesabıdır; hesap türü ve uygun güçlü doğrulama yöntemi araştırılır. Servis hesaplarının her zaman kullanıcı MFA'sıyla korunacağı iddia edilmez.

## Süreklilik

- Bölüm 1: Giriş kartı, gizlilik, görev bazlı erişim; bölüm 2: beklenti ve görev rolleri.
- Bölüm 3: 25 dakikalık ilk kesinti. İş hedefleri RTO 60 dakika, RPO 5 dakika.
- Bölüm 4: 20 yönetici hesabından 3 MFA istisnası, kapsam %85; kritik istisna limiti 0. Bu gösterge sonraki incelemelerde aynı kalır; doğrulama bitmeden başarı iddiası kurulmaz.
- Bölüm 5: İnceleme dönemi, kanıt tamlığı ve bağımsız denetimin sınırları.
- Bölüm 6: svc-pay-prod hesabında ihtiyaç dışı kullanıcı oluşturma yetkisi. İhtiyaç ve kullanım doğrulanır. Önceki kesintiyle nedensellik kanıtlanmamıştır.
- Bölüm 7: Ece'nin bulgu itirazı, yetkili risk kabulü ve baskının kayıtlı eskalasyonu.
- Bölüm 8: Ayrı gece olayı 02.10 başlangıç, 02.12 alarm, 03.25 hizmet dönüşü. 75 dakika kesinti, RTO 15 dakika aşılmıştır. RPO sonucu veri kontrolü tamamlanmadan açıklanmaz. MFA ile olay arasındaki nedensellik açık kalır.
- Bölüm 9: A yatırımında ilk yıl kurulum+bakım 40.000 avro. B kurulum 25.000 avro, bakım belirsiz. Risk azaltma değerleri tahmindir, garanti değildir.
- Bölüm 10: A-01 kritik yetki aksiyonu açık/gecikmiş, A-02 MFA testi sürüyor. Paneldeki sıfır açık kritik aksiyon değeri hatalı ya da kapsamı açıklanmamıştır; uzlaştırılır. Önceki kayıtlardaki açık işler kapanmış gibi gösterilmez.

9 PNG görselin kanıt numarası soru numarasıyla eşleşir. Görsellerde gerçek müşteri bilgisi veya mevzuat atfı bulunmaz. 10 ses metni intro'dur; soru okuması değildir. Gerçek kayıt yoksa intro alanı NULL; soru bağlamı metin olarak çalışır.
