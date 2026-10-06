"""Prepare repeatable content only in the isolated device-demo database."""
import secrets
from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from mobile_api.models import LearningPath, Question, Subscription

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if settings.ROOT_URLCONF != 'mobile_api.dev_urls':
            raise CommandError('Only run with --settings=mobile_api.dev_settings')
        user, _ = get_user_model().objects.get_or_create(username='device_demo', defaults={'email': 'demo@grcustasi.test', 'first_name': 'Volkan', 'is_mobile': True})
        credential_file = Path(settings.DATABASES['default']['NAME']).parent / 'demo_password.txt'
        if not credential_file.exists():
            password = 'Grc-' + secrets.token_urlsafe(9)
            credential_file.write_text(password)
            credential_file.chmod(0o600)
            user.set_password(password)
            user.save()
        p, _ = LearningPath.objects.get_or_create(owner=user, title='GRC • iPhone Deneme', defaults={'published': True, 'description': '8 kısa görevle uygulamanın öğrenme akışını dene.', 'minutes': 6})
        content = [
            ('choice', 'Eski çalışan hesaplarının açık kalması hangi riski artırır?', ['Yetkisiz erişim', 'Yedekleme kapasitesi', 'Ekran çözünürlüğü'], ['0'], 'İşten ayrılan çalışanların erişimleri zamanında kaldırılmalıdır.'),
            ('multi_select', 'Güçlü erişim kontrolüne hangi uygulamalar katkıda bulunur?', ['Çok faktörlü kimlik doğrulama', 'Ortak yönetici hesabı', 'Periyodik erişim gözden geçirmesi'], ['0', '2'], 'MFA ve erişim gözden geçirmeleri hesap güvenliğini artırır. Ortak hesaplar izlenebilirliği azaltır.'),
            ('fill_blank', 'Sadece görev için gerekli yetkileri verme prensibi: ______', [], ['least privilege', 'en az yetki', 'asgari yetki'], 'En az yetki (Least Privilege), ihtiyaç duyulan erişimle sınırlı yetki verilmesidir.'),
            ('scenario', '{first_name}, Domain Admin grubunda 14 kullanıcı buldun. İlk adımın ne olmalı?', ['Hesapları hemen silmek', 'Yetkilerin gerekçesini ve onaylarını incelemek', 'Bulgunun üstünü kapatmak'], ['1'], 'Önce iş gereksinimi, yetki onayları ve hesapların kullanımını incele; değişiklikleri yetkili süreçle uygula.'),
            ('choice', 'Risk değerlendirmesinde hangi iki unsur birlikte ele alınır?', ['Olasılık ve etki', 'Dosya adı ve boyutu', 'Ekran rengi ve parlaklığı'], ['0'], 'Risk, olayın olasılığı ve gerçekleştiğinde yaratacağı etkiyle değerlendirilir.'),
            ('text', 'Çok faktörlü kimlik doğrulamanın yaygın kısaltmasını yaz.', [], ['mfa'], 'MFA, Multi-Factor Authentication anlamına gelir.'),
            ('choice', 'Bir güvenlik bulgusu için hangi kanıt daha güçlüdür?', ['Tarihli ve doğrulanabilir sistem kaydı', 'Kulaktan duyma bilgi', 'Kaynağı belirsiz yorum'], ['0'], 'Kanıtın doğrulanabilir, ilgili ve zaman açısından anlamlı olması gerekir.'),
            ('scenario', 'Yedekleme başarılı görünüyor. Kurtarmaya hazır olduğunu nasıl doğrularsın?', ['Sadece yeşil göstergeye bakarak', 'Kontrollü geri yükleme testi yaparak', 'Dosya adını değiştirerek'], ['1'], 'Geri yükleme testi, yedeğin gerçek bir kurtarma ihtiyacında kullanılabilir olduğunu doğrular.'),
        ]
        for order, (kind, prompt, labels, answer, explanation) in enumerate(content):
            existing = p.questions.filter(order=order).first()
            if existing:
                continue
            q = Question.objects.create(kind=kind, prompt=prompt, options=[{'id': str(i), 'text': label} for i, label in enumerate(labels)], answer=answer, explanation=explanation, hint='Kontrolün amacını ve kanıtı düşün.', published=True, base_xp=20, order=order)
            q.paths.add(p)
        Subscription.objects.update_or_create(transaction_id='isolated-device-demo', defaults={'user': user, 'provider': 'device-demo', 'status': 'active', 'expires_at': timezone.now() + timedelta(days=7), 'verified_at': timezone.now()})
        self.stdout.write('Demo hazır. E-posta: demo@grcustasi.test')
        self.stdout.write('Parola: ' + credential_file.read_text())
