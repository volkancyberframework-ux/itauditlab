import secrets
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from workspace.models import Organization, Audit, Membership, Control, ResponseRevision, Evaluation, Finding

# Original demonstration questions, thematically inspired by ISO/IEC 27001 and NIST CSF.
# These are not licensed standard text, an exhaustive framework, or formal clause mappings.
CONTROLS=[
('ISO','Bilgi güvenliği politikası','Yönetişim','medium','Bilgi güvenliği politikasının güncel sürümü yönetim tarafından onaylanmış ve çalışanlarla paylaşılmış mı?','Onay tarihi, politika sürümü ve duyuru kaydı.'),
('ISO','Varlık envanterinin güncelliği','Varlık yönetimi','medium','Sunucu, uç nokta, yazılım ve kritik veri varlıkları için sorumlusu belli bir envanter tutuluyor mu?','Varlık listesi ve son gözden geçirme kaydı.'),
('ISO','Ayrıcalıklı hesapların kontrolü','Erişim yönetimi','high','Yönetici hesapları kişiye özel mi ve ihtiyaç doğrultusunda düzenli gözden geçiriliyor mu?','Yetkili hesap listesi ve erişim gözden geçirme kaydı.'),
('ISO','Çok faktörlü kimlik doğrulama','Kimlik doğrulama','high','Uzaktan erişim ve kritik yönetim arayüzlerinde çok faktörlü doğrulama uygulanıyor mu?','Kimlik doğrulama ilkesi ve kişisel veri içermeyen yapılandırma özeti.'),
('ISO','İşten ayrılanların erişimlerinin kapatılması','İnsan kaynakları güvenliği','high','İşten ayrılma bildirimi sonrası sistem erişimleri tanımlı süre içinde kapatılıyor mu?','Anonimleştirilmiş örnek kapatma talebi ve işlem zamanları.'),
('ISO','Yedeklerin geri yükleme testi','Yedekleme','high','Kritik sistem yedekleri düzenli alınıyor ve geri yüklenebilirliği test ediliyor mu?','Son geri yükleme test raporu ve yedekleme planı.'),
('ISO','Güvenlik güncellemelerinin takibi','Zafiyet yönetimi','high','Kritik güvenlik güncellemeleri için önceliklendirme ve süre takibi yapılıyor mu?','Yama uyum raporu ve istisna onayları.'),
('ISO','Güvenlik olaylarının kaydı','Olay yönetimi','medium','Güvenlik olayları kaydediliyor, sorumlulara atanıyor ve kapanışta değerlendiriliyor mu?','Olay kayıt şablonu ve anonimleştirilmiş olay örneği.'),
('ISO','Tedarikçi güvenlik değerlendirmesi','Tedarikçi yönetimi','medium','Kritik tedarikçilerin bilgi güvenliği riskleri sözleşme öncesinde değerlendiriliyor mu?','Tedarikçi değerlendirmesi ve güvenlik şartları.'),
('ISO','Logların merkezi izlenmesi','İzleme','high','Kritik sistem kayıtları merkezi olarak toplanıyor ve belirlenmiş kurallarla inceleniyor mu?','Log kaynak listesi ve örnek alarm inceleme kaydı.'),
('ISO','Bilgi güvenliği farkındalığı','Farkındalık','low','Çalışanlara görevlerine uygun güvenlik eğitimi veriliyor ve katılım takip ediliyor mu?','Eğitim planı ve anonimleştirilmiş katılım özeti.'),
('ISO','Fiziksel erişimin kontrolü','Fiziksel güvenlik','medium','Sunucu odası gibi kritik alanlara erişim yetkilendirilip kaydediliyor mu?','Yetki listesi, ziyaretçi süreci ve erişim kayıt örneği.'),
('NIST','Siber risk sorumlulukları','Govern','medium','Siber risk kararları için yönetim sorumlulukları ve raporlama düzeni belirlenmiş mi?','Sorumluluk matrisi ve yönetim toplantı gündemi.'),
('NIST','Kritik hizmetlerin belirlenmesi','Identify','medium','Kurumun kritik hizmetleri ve bu hizmetlerin teknoloji bağımlılıkları listelenmiş mi?','Kritik hizmet envanteri ve bağımlılık listesi.'),
('NIST','Verilerin korunması','Protect','high','Hassas veriler için erişim ve güvenli aktarım kuralları uygulanıyor mu?','Veri sınıflandırma yaklaşımı ve güvenli aktarım yapılandırması.'),
('NIST','Şüpheli etkinliklerin tespiti','Detect','high','Şüpheli erişim veya olağan dışı etkinlikler için alarm üretilip değerlendirme yapılıyor mu?','Alarm kuralları ve örnek inceleme kaydı.'),
('NIST','Olay müdahale tatbikatı','Respond','medium','Siber olay müdahale planı ekipler tarafından düzenli olarak deneniyor mu?','Masa başı tatbikat tutanağı ve iyileştirme listesi.'),
('NIST','Hizmetlerin geri kazanılması','Recover','high','Kesinti sonrasında kritik hizmetleri geri getirmek için test edilmiş bir plan var mı?','Geri dönüş planı ve son test çıktısı.'),
]

class Command(BaseCommand):
    help='Load an idempotent, fictional audit workspace. Development only.'
    def add_arguments(self,parser):parser.add_argument('--prepare-admin',action='store_true')
    @transaction.atomic
    def handle(self,*args,**options):
        if not settings.DEBUG:raise CommandError('Yalnızca yerel demo ortamında çalışır.')
        users=get_user_model()
        org,_=Organization.objects.get_or_create(slug='ornek-belediyesi',defaults={'name':'Örnek Belediyesi'})
        audit,_=Audit.objects.get_or_create(organization=org,title='2026 Bilgi Güvenliği Denetimi',defaults={'is_demo':True})
        it,created=users.objects.get_or_create(email='ayse.yilmaz@example.demo',defaults={'first_name':'Ayşe','last_name':'Yılmaz','must_change_password':False})
        if created:it.set_unusable_password();it.save()
        Membership.objects.get_or_create(user=it,audit=audit,defaults={'role':'it'})
        statuses=['implemented','implemented','partial','partial','missing','partial','missing','implemented','unanswered','partial','implemented','unanswered','implemented','unanswered','partial','unanswered','unanswered','implemented']
        for index,(kind,title,theme,risk,description,evidence) in enumerate(CONTROLS,1):
            control,created=Control.objects.get_or_create(audit=audit,code=f'SKB-{index:03d}',defaults={'title':title,'theme':theme,'risk':risk,'description':description,'evidence_guidance':evidence,'framework':'ISO/IEC 27001:2022' if kind=='ISO' else 'NIST CSF 2.0','intern_visible':index in [1,2,8,9,11,12,13,14]})
            if not created:continue
            status=statuses[index-1]
            if status!='unanswered':
                explanations={'implemented':'İlgili süreç tanımlandı ve düzenli olarak uygulanıyor. Örnek uygulama kayıtları denetim için hazırlanıyor.','partial':'Süreç bazı sistemlerde uygulanıyor. Kapsamın tamamlanması için BT ekibinin iyileştirme çalışması devam ediyor.','missing':'Henüz kurumsal ölçekte uygulanmıyor. Sorumlu ekip ve uygulama takvimi belirlenmesi gerekiyor.'}
                ResponseRevision.objects.create(control=control,actor=it,status=status,explanation=explanations[status])
                if index==3:ResponseRevision.objects.create(control=control,actor=it,status='partial',explanation='Yönetici hesaplarının listesi güncellendi. İki eski servis hesabının sahipliği henüz doğrulanmadı.')
                assessment={'implemented':'compliant','partial':'partial','missing':'noncompliant'}[status]
                Evaluation.objects.create(control=control,assessment=assessment,rationale={'compliant':'Demo incelemede süreç tanımı ve örnek kayıtlar tutarlı bulundu.','partial':'Kapsam ve periyodik kontrol kayıtları tamamlanmalıdır.','noncompliant':'Uygulamanın başlatılması ve kanıtlarla doğrulanması gerekir.'}[assessment],private_note='Denetçi iç notu: Örneklem kapsamını saha görüşmesinde doğrula.',customer_visible=index!=7)
        for title,recommendation,severity,visible in [
            ('Kritik erişimlerde MFA kapsamı eksik','Uzaktan erişim ve yönetici hesapları için MFA kapsamını tamamlayın.','high',True),
            ('Yedek geri dönüş testleri tüm sistemleri kapsamıyor','Kritik hizmetler için test takvimi oluşturun ve sonuçları kaydedin.','high',True),
            ('Farkındalık eğitim kayıtları dağınık','Eğitim katılımını merkezi olarak takip edin.','medium',True),
            ('Denetçi iç değerlendirmesi: örneklem genişletilecek','Ek teknik örneklem belirlenmeden BT sorumlusu paylaşımı yapılmayacak.','medium',False)]:
            Finding.objects.get_or_create(audit=audit,title=title,defaults={'recommendation':recommendation,'severity':severity,'customer_visible':visible})
        if options['prepare_admin']:
            admin,_=users.objects.get_or_create(email='demo@grcustasi.local')
            password=secrets.token_urlsafe(14)
            admin.is_staff=True;admin.is_superuser=True;admin.is_active=True;admin.must_change_password=False;admin.first_name='Demo';admin.last_name='Yönetici';admin.set_password(password);admin.save()
            self.stdout.write(f'Demo admin: {admin.email}\nParola: {password}')
        self.stdout.write(f'{audit.controls.count()} kontrol hazır. Mevcut yanıtlar korunmuştur.')
