from django.db import migrations

# Frozen, original starting controls; not official standard text or exhaustive sector coverage.
COMMON = [('ISO',
  'Bilgi güvenliği politikası',
  'Yönetişim',
  'medium',
  'Bilgi güvenliği politikasının güncel sürümü yönetim tarafından onaylanmış ve çalışanlarla paylaşılmış mı?',
  'Onay tarihi, politika sürümü ve duyuru kaydı.'),
 ('ISO',
  'Varlık envanterinin güncelliği',
  'Varlık yönetimi',
  'medium',
  'Sunucu, uç nokta, yazılım ve kritik veri varlıkları için sorumlusu belli bir envanter tutuluyor mu?',
  'Varlık listesi ve son gözden geçirme kaydı.'),
 ('ISO',
  'Ayrıcalıklı hesapların kontrolü',
  'Erişim yönetimi',
  'high',
  'Yönetici hesapları kişiye özel mi ve ihtiyaç doğrultusunda düzenli gözden geçiriliyor mu?',
  'Yetkili hesap listesi ve erişim gözden geçirme kaydı.'),
 ('ISO',
  'Çok faktörlü kimlik doğrulama',
  'Kimlik doğrulama',
  'high',
  'Uzaktan erişim ve kritik yönetim arayüzlerinde çok faktörlü doğrulama uygulanıyor mu?',
  'Kimlik doğrulama ilkesi ve kişisel veri içermeyen yapılandırma özeti.'),
 ('ISO',
  'İşten ayrılanların erişimlerinin kapatılması',
  'İnsan kaynakları güvenliği',
  'high',
  'İşten ayrılma bildirimi sonrası sistem erişimleri tanımlı süre içinde kapatılıyor mu?',
  'Anonimleştirilmiş örnek kapatma talebi ve işlem zamanları.'),
 ('ISO',
  'Yedeklerin geri yükleme testi',
  'Yedekleme',
  'high',
  'Kritik sistem yedekleri düzenli alınıyor ve geri yüklenebilirliği test ediliyor mu?',
  'Son geri yükleme test raporu ve yedekleme planı.'),
 ('ISO',
  'Güvenlik güncellemelerinin takibi',
  'Zafiyet yönetimi',
  'high',
  'Kritik güvenlik güncellemeleri için önceliklendirme ve süre takibi yapılıyor mu?',
  'Yama uyum raporu ve istisna onayları.'),
 ('ISO',
  'Güvenlik olaylarının kaydı',
  'Olay yönetimi',
  'medium',
  'Güvenlik olayları kaydediliyor, sorumlulara atanıyor ve kapanışta değerlendiriliyor mu?',
  'Olay kayıt şablonu ve anonimleştirilmiş olay örneği.'),
 ('ISO',
  'Tedarikçi güvenlik değerlendirmesi',
  'Tedarikçi yönetimi',
  'medium',
  'Kritik tedarikçilerin bilgi güvenliği riskleri sözleşme öncesinde değerlendiriliyor mu?',
  'Tedarikçi değerlendirmesi ve güvenlik şartları.'),
 ('ISO',
  'Logların merkezi izlenmesi',
  'İzleme',
  'high',
  'Kritik sistem kayıtları merkezi olarak toplanıyor ve belirlenmiş kurallarla inceleniyor mu?',
  'Log kaynak listesi ve örnek alarm inceleme kaydı.'),
 ('ISO',
  'Bilgi güvenliği farkındalığı',
  'Farkındalık',
  'low',
  'Çalışanlara görevlerine uygun güvenlik eğitimi veriliyor ve katılım takip ediliyor mu?',
  'Eğitim planı ve anonimleştirilmiş katılım özeti.'),
 ('ISO',
  'Fiziksel erişimin kontrolü',
  'Fiziksel güvenlik',
  'medium',
  'Sunucu odası gibi kritik alanlara erişim yetkilendirilip kaydediliyor mu?',
  'Yetki listesi, ziyaretçi süreci ve erişim kayıt örneği.'),
 ('NIST',
  'Siber risk sorumlulukları',
  'Govern',
  'medium',
  'Siber risk kararları için yönetim sorumlulukları ve raporlama düzeni belirlenmiş mi?',
  'Sorumluluk matrisi ve yönetim toplantı gündemi.'),
 ('NIST',
  'Kritik hizmetlerin belirlenmesi',
  'Identify',
  'medium',
  'Kurumun kritik hizmetleri ve bu hizmetlerin teknoloji bağımlılıkları listelenmiş mi?',
  'Kritik hizmet envanteri ve bağımlılık listesi.'),
 ('NIST',
  'Verilerin korunması',
  'Protect',
  'high',
  'Hassas veriler için erişim ve güvenli aktarım kuralları uygulanıyor mu?',
  'Veri sınıflandırma yaklaşımı ve güvenli aktarım yapılandırması.'),
 ('NIST',
  'Şüpheli etkinliklerin tespiti',
  'Detect',
  'high',
  'Şüpheli erişim veya olağan dışı etkinlikler için alarm üretilip değerlendirme yapılıyor mu?',
  'Alarm kuralları ve örnek inceleme kaydı.'),
 ('NIST',
  'Olay müdahale tatbikatı',
  'Respond',
  'medium',
  'Siber olay müdahale planı ekipler tarafından düzenli olarak deneniyor mu?',
  'Masa başı tatbikat tutanağı ve iyileştirme listesi.'),
 ('NIST',
  'Hizmetlerin geri kazanılması',
  'Recover',
  'high',
  'Kesinti sonrasında kritik hizmetleri geri getirmek için test edilmiş bir plan var mı?',
  'Geri dönüş planı ve son test çıktısı.')]
SECTORS = {'Belediye Denetimi': [('BEL-001',
                        'Vatandaş hizmetlerinde erişim sınırları',
                        'Belediye hizmetleri',
                        'high',
                        'Vatandaş başvuru ve tahsilat sistemlerinde erişimler görev ve birim bazında sınırlandırılıyor '
                        'mu?',
                        'Yetki matrisini alın; farklı birimlerden örnek kullanıcıların sadece görev kapsamındaki '
                        'kayıtlara erişebildiğini test edin.'),
                       ('BEL-002',
                        'Tahsilat ve işlem izlenebilirliği',
                        'Mali hizmetler',
                        'high',
                        'Tahsilat, iptal ve iade işlemleri yetkilendirilip izlenebilir biçimde kaydediliyor mu?',
                        'İşlem ve onay kayıtlarından örneklem seçin; işlemi başlatan ve onaylayan yetkileri '
                        'karşılaştırın.'),
                       ('BEL-003',
                        'Belediye hizmetlerinin sürekliliği',
                        'İş sürekliliği',
                        'high',
                        'Başvuru, ruhsat ve tahsilat hizmetleri için kesinti ve geri dönüş süreçleri test ediliyor mu?',
                        'Kritik hizmet listesini ve son kesinti tatbikatını inceleyin; geri dönüş sürelerini '
                        'hedeflerle karşılaştırın.')],
 'Hastane Denetimi': [('HAS-001',
                       'Hasta kayıtlarına görev bazlı erişim',
                       'Hasta verileri',
                       'high',
                       'Hasta kayıtlarına erişim görev ve bakım ilişkisiyle sınırlandırılıyor mu?',
                       'Anonimleştirilmiş örnek hesaplarla yetki sınırlarını, acil erişim istisnalarını ve erişim '
                       'loglarını doğrulayın; gerçek hasta verilerini dışarı aktarmayın.'),
                      ('HAS-002',
                       'Tıbbi cihaz ağlarının ayrılması',
                       'Tıbbi cihaz güvenliği',
                       'high',
                       'Tıbbi cihazlar envantere alınmış ve diğer ağlardan uygun biçimde ayrılmış mı?',
                       'Cihaz envanteri, ağ şeması ve güvenlik duvarı kurallarını inceleyin; klinik işleyişi '
                       'etkilemeyen onaylı testlerle erişim sınırlarını doğrulayın.'),
                      ('HAS-003',
                       'Klinik sistemlerin kesinti planı',
                       'Klinik süreklilik',
                       'high',
                       'Hasta kabul, laboratuvar ve görüntüleme sistemleri için kesinti ve geri dönüş planları '
                       'deneniyor mu?',
                       'İş sürekliliği planını, son tatbikat raporunu ve geri yükleme sonuçlarını inceleyin; klinik '
                       'birim sorumlularıyla alternatif çalışma adımlarını doğrulayın.'),
                      ('HAS-004',
                       'Sağlık verisi aktarım güvenliği',
                       'Veri paylaşımı',
                       'high',
                       'Entegrasyonlarda hasta verisi aktarımı yetkili alıcılarla ve güvenli kanallarla '
                       'sınırlandırılıyor mu?',
                       'Entegrasyon envanterini, alıcı yetkilerini ve şifreli aktarım ayarlarını inceleyin; örnek '
                       'testleri kişisel veri içermeyen kayıtlarla yapın.')]}


def seed(apps, schema_editor):
    Definition = apps.get_model('workspace', 'ControlDefinition')
    Template = apps.get_model('workspace', 'AuditTemplate')
    db = schema_editor.connection.alias
    common = []
    for index, (kind, title, theme, risk, description, evidence) in enumerate(COMMON, 1):
        item, _ = Definition.objects.using(db).get_or_create(code=f'ORT-{index:03d}', defaults={
            'title': title, 'theme': theme, 'risk': risk, 'description': description,
            'evidence_guidance': evidence, 'framework': 'ISO/IEC 27001:2022' if kind == 'ISO' else 'NIST CSF 2.0',
            'intern_visible': index in [1, 2, 8, 9, 11, 12, 13, 14],
        })
        common.append(item)
    for name, rows in SECTORS.items():
        template, _ = Template.objects.using(db).get_or_create(name=name, defaults={
            'description': 'Genel bilgi güvenliği ve sektöre özel başlangıç kontrolleri. Kurumun kapsamına göre uyarlayın; resmî standart metni veya eksiksiz mevzuat kontrol listesi değildir.',
        })
        template.controls.add(*common)
        for code, title, theme, risk, description, evidence in rows:
            item, _ = Definition.objects.using(db).get_or_create(code=code, defaults={
                'title': title, 'theme': theme, 'risk': risk, 'description': description,
                'evidence_guidance': evidence, 'framework': 'Sektörel kontrol',
            })
            template.controls.add(item)


class Migration(migrations.Migration):
    dependencies = [('workspace', '0006_audittemplate_controldefinition_and_more')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
