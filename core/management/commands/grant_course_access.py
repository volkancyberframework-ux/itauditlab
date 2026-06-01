from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Course


class Command(BaseCommand):
    help = "Kullanıcıya test course access verir."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--course-id", type=int, required=True)

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        course_id = options["course_id"]

        User = get_user_model()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Kullanıcı bulunamadı: {email}"))
            return

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Course bulunamadı: {course_id}"))
            return

        user.allowed_tests.add(course)

        self.stdout.write(
            self.style.SUCCESS(
                f"Access verildi: {email} -> {course.turkish_name} (ID: {course.id})"
            )
        )
