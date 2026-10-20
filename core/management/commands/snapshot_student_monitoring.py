from django.core.management.base import BaseCommand, CommandError
from core.student_monitoring import capture_snapshot


class Command(BaseCommand):
    help = 'Bugünün gerçek öğrenci izleme özetini kaydeder. Yeniden çalıştırılması güvenlidir.'
    def add_arguments(self, parser):
        parser.add_argument('--correction-reason', default='', help='Mevcut bugünkü özeti denetim izli düzeltme gerekçesi.')
        parser.add_argument('--actor-id', type=int)
    def handle(self, *args, **options):
        from core.models import CustomUser
        actor = None
        reason = options['correction_reason'].strip()
        if reason:
            actor = CustomUser.objects.filter(pk=options['actor_id'], is_staff=True, is_active=True).first()
            if not actor or not actor.has_perm('core.change_monitoringsettings') or len(reason) < 5:
                raise CommandError('Düzeltme için yetkili yönetici ve en az 5 karakter gerekçe gerekli.')
        obj, changed = capture_snapshot(actor, reason)
        self.stdout.write(f'{obj.reporting_date}: ' + ('Özet kaydedildi.' if changed else 'Özet zaten kayıtlı; değiştirilmedi.'))
