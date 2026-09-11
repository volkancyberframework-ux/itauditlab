from django.db import migrations


CISM_PROGRAM_SLUGS = ("cism-bootcamp-3-ay", "cism-bootcamp-6-ay")
CISM_COURSE_DESCRIPTION = (
    "CISM Bootcamp kapsamında bilgi güvenliği yönetişimi, risk yönetimi, "
    "güvenlik programı yönetimi ve olay yönetimi alanlarında ilerleyin. "
    "Sorularınız için bana volkan@grcustasi.com adresinden ulaşabilirsiniz."
)


def set_cism_course_descriptions(apps, schema_editor):
    Course = apps.get_model("core", "Course")
    LearningProgramStep = apps.get_model("core", "LearningProgramStep")
    course_ids = LearningProgramStep.objects.filter(
        program__slug__in=CISM_PROGRAM_SLUGS
    ).values_list("course_id", flat=True)
    Course.objects.filter(pk__in=course_ids).update(
        description=CISM_COURSE_DESCRIPTION
    )


class Migration(migrations.Migration):
    dependencies = [("core", "0020_activate_cism_courses_as_tests")]

    operations = [
        migrations.RunPython(
            set_cism_course_descriptions,
            migrations.RunPython.noop,
        )
    ]
