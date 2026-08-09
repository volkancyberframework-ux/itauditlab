from django.core.management.base import BaseCommand

from core.models import Course, LearningProgram, LearningProgramStep
from core.program_schedules import PROGRAM_SCHEDULES


class Command(BaseCommand):
    help = "Varsayılan CISA ve lab program akışlarını oluşturur/günceller."

    def handle(self, *args, **options):
        missing = []
        count = 0
        for slug, definition in PROGRAM_SCHEDULES.items():
            program, _ = LearningProgram.objects.get_or_create(
                slug=slug, defaults={"name": definition["name"], "is_active": True}
            )
            for order, (day_offset, course_id) in enumerate(definition["steps"]):
                try:
                    course = Course.objects.get(pk=course_id)
                except Course.DoesNotExist:
                    missing.append(course_id)
                    continue
                LearningProgramStep.objects.get_or_create(
                    program=program,
                    course=course,
                    defaults={"day_offset": day_offset, "order": order},
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f"{count} program adımı hazırlandı."))
        if missing:
            self.stdout.write(self.style.WARNING(f"Bulunamayan course ID'leri: {sorted(set(missing))}"))
