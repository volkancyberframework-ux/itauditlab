from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.grcustasi_80_hour_program import (
    LESSONS,
    PROGRAM_NAME,
    PROGRAM_SLUG,
    lesson_day_offsets,
)
from core.models import Course, LearningProgram, LearningProgramStep


class Command(BaseCommand):
    help = "GRC Ustası 80 saatlik Test derslerini ve 6 aylık programı oluşturur/günceller."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Değişiklikleri doğrular ve özeti gösterir; veritabanına kaydetmez.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        offsets = lesson_day_offsets()
        if len(LESSONS) != 80 or len(offsets) != 80:
            raise CommandError("Program tam olarak 80 ders ve 80 zaman adımı içermelidir.")
        if offsets[-1] != 181:
            raise CommandError("Programın son dersi 182. program gününde açılmalıdır.")

        program, program_created = LearningProgram.objects.update_or_create(
            slug=PROGRAM_SLUG,
            defaults={"name": PROGRAM_NAME, "is_active": True},
        )

        created_courses = 0
        updated_courses = 0
        desired_course_ids = []

        for number, ((title, description), day_offset) in enumerate(
            zip(LESSONS, offsets), start=1
        ):
            full_title = f"GRC Ustası {number:02d} — {title}"
            defaults = {
                "english_name": "",
                "duration": timedelta(hours=1),
                "difficulty": self._difficulty(number),
                "description": description,
                "dashboard_activated": False,
                "main_page_activated": False,
                "is_english": False,
                "is_turkish": True,
                "course_type": Course.CourseType.TEST,
            }

            course = Course.objects.filter(turkish_name=full_title).order_by("pk").first()
            if course is None:
                course = Course.objects.create(turkish_name=full_title, **defaults)
                created_courses += 1
            else:
                changed = False
                for field, value in defaults.items():
                    if getattr(course, field) != value:
                        setattr(course, field, value)
                        changed = True
                if changed:
                    course.save(update_fields=list(defaults))
                    updated_courses += 1

            desired_course_ids.append(course.pk)
            LearningProgramStep.objects.update_or_create(
                program=program,
                course=course,
                defaults={
                    "day_offset": day_offset,
                    "order": number,
                    "email_title": f"{number}. dersiniz açıldı: {title}",
                },
            )

        stale_steps = program.steps.exclude(course_id__in=desired_course_ids)
        stale_count = stale_steps.count()
        if stale_count:
            stale_steps.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Program: {PROGRAM_NAME} ({'oluşturuldu' if program_created else 'güncellendi'})\n"
                f"Dersler: 80 Test · yeni {created_courses} · güncellenen {updated_courses}\n"
                f"Takvim: gün 0–181 · 26 hafta · toplam 80 saat\n"
                f"Kaldırılan eski program adımı: {stale_count}"
            )
        )

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("DRY RUN: Veritabanı değişiklikleri geri alındı."))

    @staticmethod
    def _difficulty(number):
        if number <= 25:
            return "Beginner"
        if number <= 72:
            return "Intermediate"
        return "Advanced"
