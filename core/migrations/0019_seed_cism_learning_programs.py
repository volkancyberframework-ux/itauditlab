from datetime import timedelta

from django.core.management.color import no_style
from django.db import migrations, models


THREE_MONTH_STEPS = (
    (0, "CISM Bootcamp – Başlangıç & CISM Manager Mindset"),
    (3, "Domain 1A – Information Security Governance: Kurumsal Yönetişim"),
    (6, "Domain 1B – Security Strategy: Strateji, Bütçe ve Yönetim Desteği"),
    (9, "Vaka 1 – Yeni CISO Olarak İlk 90 Gün"),
    (12, "Uygulama 1 – Board için Security Strategy & Roadmap Hazırlama"),
    (15, "Domain 2A – Information Security Risk Management: Risk Assessment"),
    (18, "Domain 2B – Risk Response: Risk Treatment, Appetite ve Ownership"),
    (21, "Vaka 2 – Kritik Bir Riski Yönetim Kabul Etmeli mi?"),
    (24, "Uygulama 2 – Risk Register & Risk Treatment Plan"),
    (27, "Yönetici Atölyesi – Risk Yönetim Kuruluna Nasıl Anlatılır?"),
    (30, "Domain 3A – Information Security Program Development"),
    (33, "Domain 3B – Security Program Management & Metrics"),
    (36, "Vaka 3 – Sıfırdan Bilgi Güvenliği Programı Kurmak"),
    (39, "Uygulama 3 – Security Program Roadmap"),
    (42, "Lab 1 – Security Budget & Business Case"),
    (45, "Lab 2 – KPI / KRI / Security Dashboard"),
    (48, "Domain 4A – Incident Management Readiness"),
    (51, "Domain 4B – Incident Response, Recovery & Lessons Learned"),
    (54, "Vaka 4 – Ransomware Krizinde CISO Kararları"),
    (57, "Tabletop Exercise – Büyük Siber Olay Yönetimi"),
    (60, "Lab 3 – Incident Response Plan"),
    (63, "Lab 4 – BIA, BCP & DRP Yönetim Senaryosu"),
    (66, "Vaka 5 – Third Party Breach & Yönetim Krizi"),
    (69, "Uygulama 4 – Executive Incident Communication"),
    (72, "CISM Manager Mindset Soru Kampı"),
    (75, "Domain 1–2 Yoğun Soru Çözümü"),
    (78, "Domain 3–4 Yoğun Soru Çözümü"),
    (81, "Mock Exam & Yanlış Analizi"),
    (84, "CISO Simülasyonu – Yönetim Kurulu Sunumu"),
    (87, "Final Workshop – CISM Sınav Stratejisi"),
)


SIX_MONTH_STEPS = (
    (0, "CISM Bootcamp – Başlangıç & Manager Mindset"),
    (6, "Domain 1A – Information Security Governance"),
    (12, "Domain 1B – Security Strategy & Strategic Planning"),
    (18, "Vaka 1 – Yeni CISO'nun İlk 90 Günü"),
    (24, "Uygulama – Security Strategy & 3 Yıllık Roadmap"),
    (30, "Lab – Security Budget & Business Case"),
    (36, "Domain 2A – Information Security Risk Assessment"),
    (42, "Domain 2B – Risk Response, Appetite & Ownership"),
    (48, "Vaka 2 – Yönetim Kurulu Risk Kabulü"),
    (54, "Uygulama – Enterprise Risk Register"),
    (60, "Lab – Risk Treatment Plan"),
    (66, "Yönetici Atölyesi – Board Risk Reporting"),
    (72, "Domain 3A – Information Security Program Development"),
    (78, "Domain 3B – Information Security Program Management"),
    (84, "Vaka 3 – Sıfırdan Security Program Kurulması"),
    (90, "Uygulama – Security Program Roadmap"),
    (96, "Lab – KPI, KRI & Management Dashboard"),
    (102, "Vaka 4 – Third-Party / Supply Chain Risk"),
    (108, "Lab – Vendor Security Governance"),
    (114, "Domain 4A – Incident Management Readiness"),
    (120, "Domain 4B – Incident Operations & Recovery"),
    (126, "Vaka 5 – Ransomware Krizi"),
    (132, "Tabletop Exercise – Executive Incident Response"),
    (138, "Lab – Incident Response Plan"),
    (144, "Lab – BIA / BCP / DRP"),
    (150, "Vaka 6 – Veri İhlali, Regülatör ve Medya Krizi"),
    (156, "Uygulama – CEO / Board Incident Briefing"),
    (162, "CISM Bombardıman Soru Kampı"),
    (168, "CISM Manager Mindset – Zor Sorular"),
    (174, "Mock Exam & Final CISO Workshop"),
    (180, "Final – CISM Sınavı + Kariyerde Yönetici Bakışı"),
)


PROGRAMS = (
    ("cism-bootcamp-3-ay", "CISM Bootcamp — 3 Ay", THREE_MONTH_STEPS),
    ("cism-bootcamp-6-ay", "CISM Bootcamp — 6 Ay", SIX_MONTH_STEPS),
)


def ensure_course_access_schema(apps, schema_editor):
    """Repair columns skipped by 0013's state-only migration on fresh databases."""
    Course = apps.get_model("core", "Course")
    CustomUser = apps.get_model("core", "CustomUser")
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        course_columns = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, Course._meta.db_table
            )
        }
    if "course_type" not in course_columns:
        schema_editor.add_field(Course, Course._meta.get_field("course_type"))
    if "intro_video_url" not in course_columns:
        intro_video_field = models.URLField(blank=True, null=True)
        intro_video_field.contribute_to_class(Course, "intro_video_url")
        schema_editor.add_field(Course, intro_video_field)

    through_model = CustomUser._meta.get_field("allowed_tests").remote_field.through
    if through_model._meta.db_table not in connection.introspection.table_names():
        schema_editor.create_model(through_model)


def seed_cism_programs(apps, schema_editor):
    Course = apps.get_model("core", "Course")
    LearningProgram = apps.get_model("core", "LearningProgram")
    LearningProgramStep = apps.get_model("core", "LearningProgramStep")
    cover_name = "__static__/img/course-covers/cism-bootcamp.png"

    # Production historically received several Course rows with explicit IDs.
    # PostgreSQL's sequence can therefore lag behind MAX(id), making the next
    # normal insert reuse an existing primary key. Align every sequence used by
    # this seed before creating catalog records.
    sequence_sql = schema_editor.connection.ops.sequence_reset_sql(
        no_style(), [Course, LearningProgram, LearningProgramStep]
    )
    with schema_editor.connection.cursor() as cursor:
        for statement in sequence_sql:
            cursor.execute(statement)

    for slug, program_name, steps in PROGRAMS:
        program, _ = LearningProgram.objects.update_or_create(
            slug=slug,
            defaults={"name": program_name, "is_active": True},
        )
        for order, (day_offset, title) in enumerate(steps, start=1):
            course_type = "test" if "soru" in title.casefold() or "mock exam" in title.casefold() else "video"
            description = (
                f"{program_name} · Gün {day_offset} içeriği. "
                "İçerik ve materyaller daha sonra eklenecektir."
            )
            course, _ = Course.objects.get_or_create(
                turkish_name=title,
                description=description,
                defaults={
                    "english_name": "",
                    "duration": timedelta(hours=1),
                    "difficulty": "Advanced",
                    "score": 0,
                    "preparer": None,
                    "dashboard_activated": False,
                    "main_page_activated": False,
                    "is_english": False,
                    "is_turkish": True,
                    "course_type": course_type,
                    "image": cover_name,
                },
            )
            if course.image.name != cover_name:
                course.image = cover_name
                course.save(update_fields=("image",))
            LearningProgramStep.objects.update_or_create(
                program=program,
                course=course,
                defaults={
                    "day_offset": day_offset,
                    "email_title": title,
                    "order": order,
                },
            )

    cisa_cover_name = "__static__/img/course-covers/cisa-bootcamp.png"
    cisa_course_ids = LearningProgramStep.objects.filter(
        program__slug__in=("normal", "normallong")
    ).values_list("course_id", flat=True)
    Course.objects.filter(pk__in=cisa_course_ids).update(image=cisa_cover_name)


class Migration(migrations.Migration):
    dependencies = [("core", "0018_studentmeetingbooking")]

    operations = [
        migrations.RunPython(ensure_course_access_schema, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name="course",
                    name="intro_video_url",
                    field=models.URLField(
                        blank=True,
                        null=True,
                        help_text="TEST kursları için sağ üst kapakta açılacak tanıtım videosu",
                    ),
                )
            ],
        ),
        migrations.RunPython(seed_cism_programs, migrations.RunPython.noop),
    ]
