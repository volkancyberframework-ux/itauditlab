from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from core.models import Course, Enrollment

User = get_user_model()


class Command(BaseCommand):
    help = "Grant course access to a user by email and course id"

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, type=str)
        parser.add_argument("--course-id", required=True, type=int)

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        course_id = options["course_id"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f"User not found: {email}")

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            raise CommandError(f"Course not found: {course_id}")

        enrollment, created = Enrollment.objects.get_or_create(
            user=user,
            course=course
        )

        if course.course_type == Course.CourseType.TEST:
            user.allowed_tests.add(course)

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Access granted: {email} -> {course.turkish_name or course.english_name}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Access already exists: {email} -> {course.turkish_name or course.english_name}"
                )
            )
