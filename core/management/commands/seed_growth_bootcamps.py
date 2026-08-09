from django.core.management.base import BaseCommand

from core.models import Bootcamp


BOOTCAMPS = [
    {
        "title": "AI Çağında Girişimcilik: Fikirden İlk Satışa",
        "slug": "ai-caginda-girisimcilik-fikirden-ilk-satisa",
        "description": "Yapay zekâ araçlarını kullanarak fikrini doğrular, hedef müşterini netleştirir, güçlü bir teklif oluşturur ve ilk satış görüşmelerine hazırlanırsın. 8 saat boyunca birebir çalışır; fikir, ürün, fiyatlandırma, satış ve pazarlama planını birlikte çıkarırız.",
    },
    {
        "title": "YouTube 0’dan 10.000 Aboneye: Kanal ve Gelir Modeli",
        "slug": "youtube-0-dan-10000-aboneye",
        "description": "Kanal konumlandırması, içerik serileri, başlık ve kapak sistemi, izlenme analizi, yayın takvimi ve sürdürülebilir gelir modelleri üzerine birebir çalışırız. Hedefin için ölçülebilir bir büyüme yol haritası oluşturursun; sonuçlar uygulama ve pazar koşullarına bağlıdır.",
    },
    {
        "title": "Instagram 0’dan 10.000 Organik Takipçiye",
        "slug": "instagram-0-dan-10000-organik-takipciye",
        "description": "Niş seçimi, profil konumlandırması, Reels formatları, içerik sütunları, topluluk yönetimi ve satışa yönlendiren içerik planını birlikte kurarız. Takipçi hedefini gerçekçi metrikler ve haftalık üretim sistemiyle yönetirsin.",
    },
    {
        "title": "AI ile Kişisel Marka ve 90 Günlük İçerik Sistemi",
        "slug": "ai-ile-kisisel-marka-icerik-sistemi",
        "description": "Uzmanlığını görünür bir kişisel markaya dönüştürür; LinkedIn, Instagram ve YouTube için tekrar kullanılabilir içerik sistemi kurarsın. AI destekli araştırma, fikir üretme, yazım, görsel ve yayın planlama süreçlerini birebir tasarlarız.",
    },
    {
        "title": "Dijital Ürününü 30 Günde Satışa Çıkar",
        "slug": "dijital-urununu-30-gunde-satisa-cikar",
        "description": "E-kitap, eğitim, şablon veya üyelik fikrini doğrular; minimum uygulanabilir ürünü, satış sayfasını, fiyatı ve lansman planını hazırlarsın. Program sonunda uygulayabileceğin net bir 30 günlük aksiyon planın olur.",
    },
    {
        "title": "B2B Satış ve LinkedIn’den Müşteri Kazanımı",
        "slug": "b2b-satis-linkedin-musteri-kazanimi",
        "description": "İdeal müşteri profilini çıkarır, karar vericilere ulaşma sistemini kurar, mesajlarını ve görüşme akışını hazırlarız. LinkedIn içerikleri, doğrudan erişim, ihtiyaç analizi ve teklif kapatma pratiğini birebir çalışırsın.",
    },
    {
        "title": "AI Destekli Satış Hunisi ve Pazarlama Otomasyonu",
        "slug": "ai-destekli-satis-hunisi-otomasyonu",
        "description": "Potansiyel müşterinin ilk temastan satın almaya kadar geçtiği yolu tasarlar; lead magnet, e-posta akışı, CRM takibi ve içerik otomasyonunu kurarsın. Kullanacağın araçları bütçene ve iş modeline göre birlikte seçeriz.",
    },
    {
        "title": "Danışmanlık İşini Kur ve İlk Müşterini Bul",
        "slug": "danismanlik-isini-kur-ilk-musterini-bul",
        "description": "Bilgini paketlenebilir bir danışmanlık hizmetine dönüştürür; kapsam, fiyatlandırma, teklif dosyası, müşteri görüşmesi ve teslimat sürecini oluşturursun. İlk müşteri arayışın için kişisel satış planı hazırlarsın.",
    },
    {
        "title": "E-Ticarette Kazandıran Ürün, Teklif ve Dönüşüm",
        "slug": "e-ticaret-urun-teklif-donusum",
        "description": "Ürün araştırması, müşteri problemi, rakip analizi, teklif tasarımı, ürün sayfası ve reklam öncesi dönüşüm hazırlığını birlikte yaparız. Amaç yalnızca mağaza açmak değil, ölçülebilir bir satış sistemi kurmaktır.",
    },
    {
        "title": "No-Code ve AI ile Mikro SaaS Fikrini Doğrula",
        "slug": "no-code-ai-mikro-saas-dogrulama",
        "description": "Mikro SaaS fikrini müşteri görüşmeleriyle test eder, değer önerisini netleştirir, no-code araçlarla prototip planını ve ilk kullanıcı kazanım stratejisini çıkarırsın. Teknik ekip kurmadan önce talebi ölçmeyi öğrenirsin.",
    },
]


class Command(BaseCommand):
    help = "AI, girişimcilik, satış ve pazarlama bootcamplerini eksikse oluşturur."

    def handle(self, *args, **options):
        created = 0
        for order, definition in enumerate(BOOTCAMPS, start=100):
            _, was_created = Bootcamp.objects.get_or_create(
                slug=definition["slug"],
                defaults={
                    "title": definition["title"],
                    "description": definition["description"],
                    "duration": "8 Saat · Birebir",
                    "level": "Tüm Seviyeler",
                    "price": 10000,
                    "currency": "TRY",
                    "is_active": True,
                    "order": order,
                },
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"{created} yeni bootcamp oluşturuldu."))
