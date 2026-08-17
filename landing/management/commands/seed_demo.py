from django.core.management.base import BaseCommand
from landing.models import JobMarketCount, SiteSetting

class Command(BaseCommand):
    help = 'Açıkça demo olarak etiketlenen başlangıç verilerini oluşturur.'
    def handle(self, *args, **options):
        SiteSetting.load()
        rows = [
            ('Türkiye','🇹🇷',99,'https://www.linkedin.com/jobs/search/?keywords=GRC&location=Turkey'),
            ('Almanya','🇩🇪',998,'https://www.linkedin.com/jobs/search/?keywords=GRC&location=Germany'),
            ('Japonya','🇯🇵',287,'https://www.linkedin.com/jobs/search/?keywords=GRC&location=Japan'),
            ('ABD','🇺🇸',17348,'https://www.linkedin.com/jobs/search/?keywords=GRC&location=United%20States'),
        ]
        for country, flag, grc, search_url in rows:
            JobMarketCount.objects.update_or_create(country=country, defaults={'flag':flag,'grc':grc,'search_url':search_url,'source_label':'Piyasa göstergesi','is_demo':True})
        self.stdout.write(self.style.SUCCESS('Demo verileri hazır.'))
