from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'İptal edildi: hareketsizlik nedeniyle pasifleştirme ve Telegram bildirimi çalıştırılmaz.'

    def handle(self, *args, **options):
        self.stdout.write('Hareketsizlik kontrolü iptal edildi. Hesaplar değiştirilmedi; Telegram bildirimi gönderilmedi.')
