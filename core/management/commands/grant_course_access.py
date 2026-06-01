import os
import django
import argparse

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "itaudit.settings")
django.setup()

from django.contrib.auth import get_user_model
from core.models import Course, Enrollment


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--email", required=True)
    parser.add_argument("--course-id", required=True, type=int)

    args = parser.parse_args()

    User = get_user_model()

    try:
        user = User.objects.get(email__iexact=args.email)
    except User.DoesNotExist:
        print(f"User not found: {args.email}")
        return

    try:
        course = Course.objects.get(id=args.course_id)
    except Course.DoesNotExist:
        print(f"Course not found: {args.course_id}")
        return

    enrollment, created = Enrollment.objects.get_or_create(
        user=user,
        course=course,
        defaults={"is_active": True}
    )

    if not created:
        enrollment.is_active = True
        enrollment.save()

    print(
        f"SUCCESS: {user.email} granted access to "
        f"{course.name if hasattr(course,'name') else course.title}"
    )


if __name__ == "__main__":
    main()
