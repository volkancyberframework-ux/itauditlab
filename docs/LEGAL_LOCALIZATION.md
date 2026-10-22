# GRC Ustası — ülke bazlı mevzuat yerelleştirmesi

Doğrulama tarihi: **22 Ekim 2026**. Mevzuat özetleri seçicidir; resmî metin ve somut kapsam değerlendirmesinin yerine geçmez.

## Kapsam ve korunan alanlar

- Sekiz dil, 14 hukuk alanı: TR; US/GB/EU; FR/BE; ES/CL/MX/AR; JP; CN; VN; SA.
- Ana sayfa ve kurumsal sayfanın mevzuat bölümleri aynı merkezi kayıtları kullanır. Ayrıntılar `/mevzuat/` adresindedir.
- Kullanıcının son talebine göre iş fırsatları bölümü, iş ilanı rakamları, 490.000+ alanı, Ortak Yön kutusu ve pentest açıklaması korunmuştur.
- Ticari fiyatlar, ödeme hesabı, kullanıcılar, misafir hesapları, ders ve randevu akışları değişmez. Para birimi önceki talepteki gibi dile bağlıdır; mevzuat ülkesi fiyatı değiştirmez.
- Hizmet sağlayıcının KVKK/gizlilik/sözleşme belgeleri ülke seçilince başka ülkenin belgesiyle değiştirilmez. Yeni tercih çerezleri mevcut çerez politikasına açıklanmıştır.

## İçerik envanteri ve sınıflandırma

| Alan | Karar |
|---|---|
| Ana sayfa eski 7545/DORA/AI Act/NIS2/SEC kartları | Ülke bazlı merkezi kayıtlar; kapsam ve durum ayrı |
| Kurumsal sayfa sabit 7545 bölümü ve menü etiketi | Aynı kayıt yapısı; menüde Mevzuat |
| ISO/NIST/COBIT/SOC 2/IEC 62443 ve teknik müfredat | Uluslararası standart/çerçeve veya evrensel teknik içerik; ulusal kanun gibi gösterilmez |
| Eğitim fiyatları, programlar, eğitmen, harita ve kariyer alanları | Ticari/mesleki içerik; ülkeye göre yeniden yazılmaz |
| Form aydınlatmaları ve sağlayıcının yasal metinleri | İşletmenin gerçek veri işleme bildirimi; ülke seçimiyle hukuk değiştirilmez |
| Diğer uygulamaların öğrenci/rezervasyon/admin/API sayfaları | Yerelleştirme enjeksiyonunun kapsamı dışında |

## Veri ve yayın yönetimi

`landing.models.LegalRegulation` ülke, resmî ad, otorite, kategori, tarihler, durum, resmî HTTPS kaynak, son doğrulama ve dil bazlı açıklama/iş etkisi/kapsam/kontrol alanlarını tutar. `LegalRevision` yayın düzenlemelerinin geçmişini saklar.

Admin: `/bulamazsinki/landing/legalregulation/`. İnceleme bekleyen, yayımlanmayan, yürürlükten kalkmış veya ilgili dilde metni olmayan kayıt ön yüzde gösterilmez. Başka ülkeye/dile geri dönüş yoktur. Veritabanındaki yayın kaldırma kararları paket içindeki tohum dosyasıyla geçersiz kılınmaz.

`0016` ek tabloları oluşturur; `0017` yalnızca eksik tohum kayıtlarını ekler ve ilk revizyonlarını kaydeder. Mevcut iş verilerini veya daha önce düzenlenmiş mevzuat kayıtlarını değiştirmez.

## Dil, kalıcılık ve SEO

- `?lang=es&country=CL` gibi mevcut URL üzerine sorgu parametreleri kullanılır; eski yollar korunur.
- Her dilin son ülkesi ayrı saklanır. Dil değişimi kendi son ülkesini geri getirir; ülke değişimi dili korur.
- Yerel kataloglarla sunucuda HTML çevirisi yapılır; tarayıcı içindeki geçişler aynı orijinal metinleri kullanır. Çalışan sayfada üçüncü taraf çeviri çağrısı yapılmaz.
- Canonical, 14 karşılıklı hreflang, x-default, Open Graph, dil/yön ve mevzuat ItemList verisi üretilir. `/sitemap.xml` 56 yerelleştirilmiş adres; `/robots.txt` sitemap bağlantısı sunar.

## Kaynak ve tazelik kontrolü

```sh
python manage.py check_legal_sources
python manage.py check_legal_sources --country VN
```

Bu bağımsız yönetim komutu resmî kaynakların erişimini, içerik parmak izini ve doğrulama yaşını raporlar. İlk parmak izi karşılaştırma bazıdır. HTML değişmesi yalnızca olası değişiklik anlamına gelir. Kayıt içeriğini, hukuki durumu, doğrulama tarihini veya yayın onayını otomatik değiştirmez. Admin üzerinden editör incelemesi gerekir. Baz sıfırlama eylemi de yayın onayı vermez.

Kontrol aracı resmî alan adı listesi, HTTPS, kamuya açık adres ve boyut/zaman sınırları kullanır. 403/503/zaman aşımı gibi erişim sınırlamaları raporlanır; bunlar tek başına bir kanunun değiştiği veya kaynak URL’sinin geçersiz olduğu anlamına gelmez. Periyodik çalıştırma için komut mevcut operasyon zamanlayıcısına bağlanabilir; bu sürüm yeni ücretli servis ya da bildirim aboneliği oluşturmaz.

## Düzeltilen hukuki ayrımlar

- CIRCIA uygulama kuralı: düzenleyici inceleme süreci, genel yürürlükte raporlama yükümlülüğü olarak gösterilmez.
- Fransa NIS2 aktarımı ile Belçika’nın ulusal NIS2 kanunu ayrı durumlarda gösterilir.
- İspanya NIS2 ulusal metin doğrulaması tamamlanmadığından ilgili kayıt inceleme bekler ve yayımlanmaz.
- Şili 21.719, 1 Aralık 2026 için yaklaşan düzenlemedir; 19.628 mevcut rejim olarak ayrılır.
- Meksika 2025 tarihli yeni LFPDPPP ve kamu sektörü LGPDPPSO ayrıdır; eski INAI gözetimi güncel otorite gibi sunulmaz.
- Vietnam 116/2025/QH15, 91/2025/QH15 ve 356/2025/NĐ-CP; 116’nın 143/2025/QH15 değişiklik geçmişi açıklanır.
- Çin’in 2025 değişikliği ve 2026 uygulaması; MLPS teknik standardı ile kanun yükümlülüğü ayrılır.
- Büyük ceza tutarları bütün kurumlar için genellenmez. Standartlar ve rehberler ulusal kanun gibi etiketlenmez.

## Kayıtlar ve resmî kaynaklar

| Hukuk alanı | Kayıt | Durum / yayın | Resmî kaynak |
|---|---|---|---|
| TR | 7545 • Siber Güvenlik Kanunu | active; law | [Kaynak](https://siberguvenlik.gov.tr/sss) |
| TR | 6698 • KVKK | active; law | [Kaynak](https://www.kvkk.gov.tr/Icerik/7834/6698-Sayili-Kisisel-Verilerin-Korunmasi-Kanununda-Yapilan-Degisiklikler-Hakkinda-Kamuoyu-Duyurusu) |
| TR | BİG • Genelge ve Rehber | active; law | [Kaynak](https://siberguvenlik.gov.tr/sss) |
| US | SEC • Cybersecurity disclosures | active; law | [Kaynak](https://www.sec.gov/files/rules/final/2023/33-11216.pdf) |
| US | CIRCIA • Reporting rulemaking | draft; law | [Kaynak](https://www.reginfo.gov/public/do/eoDetails?rrid=1550967) |
| US | NIST CSF 2.0 | active; guidance | [Kaynak](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=957258) |
| GB | UK GDPR • DPA 2018 | active; law | [Kaynak](https://www.gov.uk/guidance/data-use-and-access-act-2025-data-protection-and-privacy-changes) |
| GB | NIS Regulations 2018 | active; law | [Kaynak](https://www.legislation.gov.uk/uksi/2018/506/contents) |
| EU | GDPR | active; law | [Kaynak](https://eur-lex.europa.eu/eli/reg/2016/679/oj) |
| EU | NIS2 Directive | active; law | [Kaynak](https://digital-strategy.ec.europa.eu/en/policies/nis2-directive) |
| EU | DORA | active; law | [Kaynak](https://finance.ec.europa.eu/regulation-and-supervision/financial-services-legislation/implementing-and-delegated-acts/digital-operational-resilience-regulation_en) |
| EU | EU AI Act | active; law | [Kaynak](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) |
| FR | RGPD • Informatique et Libertés | active; law | [Kaynak](https://www.cnil.fr/fr/le-cadre-national/la-loi-informatique-et-libertes) |
| FR | NIS 2 • Transposition en cours | draft; law | [Kaynak](https://messervices.cyber.gouv.fr/nis2) |
| FR | LPM • OIV | active; law | [Kaynak](https://cyber.gouv.fr/reglementation/cybersecurite-systemes-dinformation/directives-nis-nis2-et-dispositif-saiv/) |
| BE | RGPD | active; law | [Kaynak](https://eur-lex.europa.eu/eli/reg/2016/679/oj) |
| BE | Loi NIS2 belge | active; law | [Kaynak](https://atwork.safeonweb.be/fr/nis2) |
| ES | RGPD • LOPDGDD | active; law | [Kaynak](https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673) |
| ES | ENS • Real Decreto 311/2022 | active; law | [Kaynak](https://www.boe.es/buscar/act.php?id=BOE-A-2022-7191) |
| ES | NIS2 • Seguimiento de transposición | needs_review — yayımlanmaz; law | [Kaynak](https://digital-strategy.ec.europa.eu/en/policies/nis2-directive-spain) |
| CL | Ley 21.663 • Ciberseguridad | active; law | [Kaynak](https://www.bcn.cl/leychile/navegar?idNorma=1202434) |
| CL | Ley 19.628 • Régimen vigente | active; law | [Kaynak](https://www.bcn.cl/leychile/Navegar?idNorma=141599&idVersion=2023-05-09) |
| CL | Ley 21.719 • Nueva protección de datos | upcoming; law | [Kaynak](https://www.bcn.cl/leychile/navegar?idNorma=1209272) |
| MX | LFPDPPP • Texto vigente | active; law | [Kaynak](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFPDPPP.pdf) |
| MX | LGPDPPSO • Sector público | active; law | [Kaynak](https://datos-personales.scjn.gob.mx/sites/default/files/normativa-materia/LGPDPPSO-DOF-20Mar2025.pdf) |
| AR | Ley 25.326 • Datos personales | active; law | [Kaynak](https://www.argentina.gob.ar/normativa/nacional/ley-25326-64790/texto) |
| JP | サイバーセキュリティ基本法 | active; law | [Kaynak](https://laws.e-gov.go.jp/law/426AC1000000104) |
| JP | 個人情報保護法 • APPI | active; law | [Kaynak](https://www.ppc.go.jp/en/legal/) |
| JP | METI • 経営ガイドライン | active; guidance | [Kaynak](https://www.meti.go.jp/policy/netsecurity/mng_guide.html) |
| CN | 网络安全法 • 2025年修正 | active; law | [Kaynak](https://www.gjbmj.gov.cn/n1/2026/0421/c409088-40705863.html) |
| CN | 数据安全法 | active; law | [Kaynak](https://www.miit.gov.cn/zwgk/zcwj/flfg/art/2022/art_284b390b84484f10b0e43eeafaad0f6d.html) |
| CN | 个人信息保护法 • PIPL | active; law | [Kaynak](https://fgk.chinatax.gov.cn/zcfgk/c100009/c5211776/content.html) |
| CN | 网络数据安全管理条例 | active; law | [Kaynak](https://app.www.gov.cn/govdata/gov/202409/30/520076/article.html) |
| VN | Luật 116/2025/QH15 • An ninh mạng | active; law | [Kaynak](https://chinhphu.vn/?classid=1&docid=216499&orggroupid=1&pageid=27160) |
| VN | Luật 91/2025/QH15 • Dữ liệu cá nhân | active; law | [Kaynak](https://sav.gov.vn/vi/bai-viet/tai-lieu-gioi-thieu-luat-bao-ve-du-lieu-ca-nhan) |
| VN | Nghị định 356/2025/NĐ-CP | active; law | [Kaynak](https://congbao.cdnchinhphu.vn/180507251028987904/2026/1/17/356signed-1768638052103952849513.pdf) |
| SA | NCA • الضوابط الأساسية | active; law | [Kaynak](https://istitlaa.ncc.gov.sa/en/security/nca/ecc22024/Documents/ECC%202-2024%20EN%2019092024.pdf) |
| SA | نظام حماية البيانات الشخصية • PDPL | active; law | [Kaynak](https://misa.gov.sa/app/uploads/2025/08/PersonalDataProtectionLaw.pdf) |
| SA | NCA • ضوابط الحوسبة السحابية | active; law | [Kaynak](https://nca.gov.sa/en/regulatory-documents/controls-list/ccc/) |
| CN | MLPS 2.0 • 等级保护技术基线 | active; guidance | [Kaynak](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=BAFB47E8874764186BDB7865E8344DAF) |
| AR | AAIP 47/2018 • Medidas recomendadas | active; guidance | [Kaynak](https://www.argentina.gob.ar/normativa/nacional/resoluci%C3%B3n-47-2018-312662/texto) |

## Kontrol ve geri alma

Django kontrolleri, migration tutarlılığı, JavaScript sözdizimi, mevcut ödeme/hesap/randevu regresyonları ve yeni ülke/yayın/SEO/sunucu çevirisi testleri çalıştırılır. Tarayıcıda sekiz dil/14 hukuk alanı, RTL, tercihler, üç ekran genişliği ve iki tema kontrol edilir. Sonuçlar `output/legal-localization-20261022/` altında tutulur.

Geri alma: uygulama commit’ini revert ederek önceki sürümü yayımlayın. Ek mevzuat tablolarını ve revizyonları koruyun; kullanıcı/ödeme/randevu tablolarında geri alma işlemi gerekmez. Veri silen ters migration uygulamayın.

## Editör incelemesinde kalacak konular

- İspanya NIS2 ulusal aktarımının yayımlanmış ve konsolide metni.
- Fransa NIS2 ve ABD CIRCIA süreçlerinin yeni aşamaları.
- Şili’nin Aralık geçişi; Vietnam ikincil mevzuatı ve değişikliklerinin somut uygulaması.
- Kuruma özgü sektör/eşik/rol değerlendirmesi, yaptırım hesapları ve olay bildirim süreleri. Özetler bunları bütün şirketlere genellemez.
- Erişimi otomasyon tarafından engellenen resmî sitelerin manuel kontrolü.
