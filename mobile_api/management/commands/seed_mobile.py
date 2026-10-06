from django.core.management.base import BaseCommand
from mobile_api.models import LearningPath, Question


class Command(BaseCommand):
    help = "Creates starter paths and one reviewed demo challenge; never overwrites existing content."

    def handle(self, *args, **kwargs):
        for order, title in enumerate(
            [
                "GRC Uzmanlığı",
                "CISA",
                "Pentest",
                "DevSecOps",
                "İş Senaryoları",
                "Ortaya Karışık",
            ]
        ):
            p, created = LearningPath.objects.get_or_create(
                title=title,
                owner=None,
                defaults={
                    "order": order,
                    "published": True,
                    "description": "Kısa görevlerle bilgini güçlendir.",
                    "premium": order > 0,
                },
            )
            if created and order == 0:
                q = Question.objects.create(
                    kind="choice",
                    prompt="{first_name}, eski çalışan hesaplarının aktif kalması hangi riski artırır?",
                    options=[
                        {"id": "a", "text": "Erişilebilirlik kaybı"},
                        {"id": "b", "text": "Yetkisiz erişim"},
                        {"id": "c", "text": "Performans düşüşü"},
                        {"id": "d", "text": "Yedekleme hatası"},
                    ],
                    answer=["b"],
                    explanation="Ayrılan çalışanların erişimleri kaldırılmalı. Aktif hesaplar yetkisiz erişime kapı açar.",
                    hint="Kimlik ve erişim yaşam döngüsünü düşün.",
                    published=True,
                    base_xp=20,
                )
                q.paths.add(p)
        self.stdout.write(self.style.SUCCESS("Başlangıç içeriği hazır."))
