import csv
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yourproject.settings")
django.setup()

from core.models import Course, TestQuestion, TestOption

COURSE_ID = 206

course = Course.objects.get(id=COURSE_ID)

questions = {}

# Önce soruları oluştur
with open("cisa_course_206_questions.csv", newline='', encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:
        q = TestQuestion.objects.create(
            course=course,
            text=row["question_text"][:500],
            explanation=row.get("explanation", ""),
            question_type="single",
            is_active=True
        )

        questions[row["question_no"]] = q

print("Questions imported")

# Sonra şıkları oluştur
with open("cisa_course_206_options_long.csv", newline='', encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:
        q = questions.get(row["question_no"])

        if not q:
            continue

        TestOption.objects.create(
            question=q,
            text=row["option_text"][:300],
            is_correct=row["is_correct"].lower() == "true"
        )

print("Options imported")
