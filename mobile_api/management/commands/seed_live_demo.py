from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from mobile_api.models import LearningPath, Question


class Command(BaseCommand):
    help = "Create an ordinary demo account and ten free practice questions, once."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        User = get_user_model()
        email = "mobile.demo@grcustasi.com"
        user = User.objects.filter(username="mobile_demo_oct2026").first()
        if user is None:
            if User.objects.filter(email__iexact=email).exists():
                raise CommandError("Demo email already belongs to another account.")
            user = User.objects.create(
                username="mobile_demo_oct2026", email=email, first_name="Demo",
                is_active=True, is_staff=False, is_superuser=False, is_mobile=True,
                password='pbkdf2_sha256$600000$a6a66b824d6933236b7a71d1$ZXvlgIdUS20AGfO0n+pGM9wDK/vPs70d7VdvwG+9Z+M=',
            )
        path, _ = LearningPath.objects.get_or_create(
            title="Demo • 10 GRC Sorusu", owner=None,
            defaults={"description": "Erişim, risk ve denetim üzerine 10 kısa soru. Konfeti ve XP akışını dene!", "published": True, "premium": False, "minutes": 10, "order": 0},
        )
        content = [
            ("İşten ayrılan bir çalışanın hesabı açık kalırsa hangi risk artar?", ["Yetkisiz erişim", "Ekran parlaklığı", "Disk kapasitesi", "Yazıcı hızı"], "a", "Ayrılan çalışanların erişimleri zamanında kaldırılmalıdır."),
            ("Risk değerlendirmesinde hangi iki unsur birlikte ele alınır?", ["Dosya adı ve uzantısı", "Olasılık ve etki", "Renk ve boyut", "Yaş ve unvan"], "b", "Olayın gerçekleşme olasılığı ve yaratacağı etki riski belirler."),
            ("En az yetki prensibi neyi ifade eder?", ["Herkese yönetici erişimi vermeyi", "Hiç kimseye erişim vermemeyi", "Yalnızca görev için gerekli yetkileri vermeyi", "Parolayı ekipçe paylaşmayı"], "c", "Yetkiler iş gereksinimi ile sınırlı olmalıdır."),
            ("Hangi yöntem çok faktörlü kimlik doğrulamaya örnektir?", ["Parola ve aynı parolayı tekrar yazmak", "Kullanıcı adı ve e-posta adresi", "İki farklı parola", "Parola ve doğrulama uygulamasından kod"], "d", "Parola bilgi faktörü, doğrulama uygulamasındaki kod ise sahiplik faktörüdür."),
            ("Bir yedeğin kurtarmada kullanılabildiğini nasıl doğrularsın?", ["Kontrollü geri yükleme testiyle", "Dosya adını değiştirerek", "Sadece başarılı göstergesine bakarak", "Yedeği silerek"], "a", "Geri yükleme testi, yedeğin gerçekten kullanılabildiğini doğrular."),
            ("Denetimde hangi kanıt daha güvenilirdir?", ["Kaynağı belirsiz yorum", "Tarihli ve doğrulanabilir sistem kaydı", "Kulaktan duyma bilgi", "Eski bir tahmin"], "b", "Kanıt ilgili, doğrulanabilir ve incelenen döneme uygun olmalıdır."),
            ("Bir faturayı oluşturan kişinin ödemeyi tek başına onaylamasını hangi kontrol önler?", ["Ekran kilidi", "Dosya sıkıştırma", "Görevler ayrılığı", "Parola uzunluğu"], "c", "Görevler ayrılığı, kritik işlemleri farklı kişilere dağıtarak hata ve suistimal riskini azaltır."),
            ("Şüpheli bağlantı içeren bir e-posta geldi. İlk güvenli adım nedir?", ["Bağlantıya tıklamak", "Parolanı göndermek", "Eki çalıştırmak", "Bağlantıyı açmadan güvenlik ekibine bildirmek"], "d", "Şüpheli içerikle etkileşime girmeden kurumun bildirim süreci izlenmelidir."),
            ("Bir güvenlik istisnası nasıl yönetilmelidir?", ["Risk değerlendirmesi, yetkili onay ve süre sınırıyla", "Süresiz ve kayıtsız", "Sadece sözlü anlaşmayla", "Kontrolleri tamamen kaldırarak"], "a", "İstisnalar gerekçeli, onaylı, süreli ve düzenli gözden geçirilen kayıtlar olmalıdır."),
            ("Bir yönetici hesabının yetkilerinin hâlâ gerekli olduğunu nasıl kontrol edersin?", ["Hesap adının uzunluğuna bakarak", "Periyodik erişim gözden geçirmesiyle", "Ekran rengini değiştirerek", "Logları kapatarak"], "b", "Erişim gözden geçirmesi, mevcut yetkileri görev ve iş gereksinimleriyle karşılaştırır."),
        ]
        for order, (prompt, labels, answer, explanation) in enumerate(content):
            if path.questions.filter(order=order).exists():
                continue
            q = Question.objects.create(kind="choice", prompt=prompt,
                options=[{"id": letter, "text": label} for letter, label in zip("abcd", labels)],
                answer=[answer], explanation=explanation,
                hint="Kontrolün hangi riski azaltmayı amaçladığını düşün.",
                base_xp=20, published=True, premium=False, order=order)
            q.paths.add(path)
        self.stdout.write(self.style.SUCCESS("Demo account and ten questions are ready."))
