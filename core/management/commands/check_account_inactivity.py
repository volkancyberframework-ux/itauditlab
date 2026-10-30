from django.core.management.base import BaseCommand
from core.account_inactivity import run_due_check


class Command(BaseCommand):
    help = 'Türkiye saatiyle 09:00 sonrası günlük 20 gün hareketsizlik kontrolünü çalıştırır; aynı gün tekrar etmez.'

    def handle(self, *args, **options):
        run = run_due_check()
        if run is None:
            self.stdout.write('09:00 Türkiye saati bekleniyor; hesap değiştirilmedi.')
        else:
            self.stdout.write(f'{run.reporting_date}: {run.checked_count} hesap kontrol edildi; {len(run.disabled_user_ids)} hesap pasife alındı.')
