from django.db import migrations


CISM_PROGRAM_SLUGS = ("cism-bootcamp-3-ay", "cism-bootcamp-6-ay")


def activate_cism_courses_as_tests(apps, schema_editor):
    Course = apps.get_model("core", "Course")
    LearningProgramStep = apps.get_model("core", "LearningProgramStep")
    course_ids = LearningProgramStep.objects.filter(
        program__slug__in=CISM_PROGRAM_SLUGS
    ).values_list("course_id", flat=True)
    Course.objects.filter(pk__in=course_ids).update(
        course_type="test",
        dashboard_activated=True,
    )


class Migration(migrations.Migration):
    dependencies = [("core", "0019_seed_cism_learning_programs")]

    operations = [
        migrations.RunPython(
            activate_cism_courses_as_tests,
            migrations.RunPython.noop,
        )
    ]
