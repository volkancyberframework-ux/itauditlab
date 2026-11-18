from types import SimpleNamespace
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.db.models import Exists, OuterRef
from core.enrollment_history import restore_access_history
from core.models import Enrollment, LessonEvidence


class Command(BaseCommand):
    help='Show missing enrollment history; --apply restores only verified access as archived records.'

    def add_arguments(self,parser):
        parser.add_argument('--apply',action='store_true')
        parser.add_argument('--database',default='default')

    def handle(self,*args,**options):
        alias=options['database']
        existing=Enrollment.objects.using(alias).filter(user_id=OuterRef('user_id'),course_id=OuterRef('course_id'))
        missing=LessonEvidence.objects.using(alias).filter(first_accessed_at__isnull=False,user__is_staff=False,user__is_superuser=False).annotate(found=Exists(existing)).filter(found=False)
        self.stdout.write(f'Missing verified histories: {missing.count()}; students: {missing.values("user_id").distinct().count()}')
        if not options['apply']:
            self.stdout.write('Dry run. No records changed.');return
        with transaction.atomic(using=alias):
            count=restore_access_history(apps,SimpleNamespace(connection=connections[alias]))
        self.stdout.write(self.style.SUCCESS(f'Restored archived histories: {count}. No new access or Telegram messages.'))
