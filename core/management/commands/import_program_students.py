import csv
from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from core.models import LearningProgram, ProgramEnrollment


class Command(BaseCommand):
    help = "name,email,start_date,program kolonlu CSV'den program katılımcılarını aktarır."

    def add_arguments(self, parser):
        parser.add_argument("csv_file")

    def handle(self, *args, **options):
        User = get_user_model()
        imported = 0
        with open(options["csv_file"], newline="", encoding="utf-8-sig") as stream:
            for row_number, row in enumerate(csv.DictReader(stream), start=2):
                email = row.get("email", "").strip().lower()
                try:
                    user = User.objects.get(email__iexact=email)
                    program = LearningProgram.objects.get(slug=row.get("program", "normal").strip().lower())
                    start_date = datetime.strptime(row["start_date"].strip(), "%Y-%m-%d").date()
                except (User.DoesNotExist, LearningProgram.DoesNotExist, KeyError, ValueError) as exc:
                    raise CommandError(f"CSV satır {row_number}: {exc}") from exc
                ProgramEnrollment.objects.update_or_create(
                    user=user, program=program,
                    defaults={"start_date": start_date, "is_active": True},
                )
                imported += 1
        self.stdout.write(self.style.SUCCESS(f"{imported} öğrenci aktarıldı."))
