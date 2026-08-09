from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0014_digitalproduct_purchaseintent"),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningProgram",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=200)),
                ("is_active", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="LearningProgramStep",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("day_offset", models.PositiveIntegerField(help_text="Başlangıçtan kaç gün sonra açılacak")),
                ("email_title", models.CharField(blank=True, max_length=255)),
                ("order", models.PositiveIntegerField(default=0)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="core.course")),
                ("program", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="steps", to="core.learningprogram")),
            ],
            options={"ordering": ("day_offset", "order", "id")},
        ),
        migrations.CreateModel(
            name="ProgramEnrollment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_date", models.DateField()),
                ("is_active", models.BooleanField(default=True)),
                ("welcome_sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("program", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="enrollments", to="core.learningprogram")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="learning_programs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-is_active", "start_date", "user__email")},
        ),
        migrations.CreateModel(
            name="ProgramRelease",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Mail bekliyor"), ("sent", "Gönderildi"), ("failed", "Mail hatası")], default="pending", max_length=12)),
                ("access_granted_at", models.DateTimeField(blank=True, null=True)),
                ("email_sent_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("enrollment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="releases", to="core.programenrollment")),
                ("step", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="core.learningprogramstep")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddConstraint(
            model_name="learningprogramstep",
            constraint=models.UniqueConstraint(fields=("program", "course"), name="unique_program_course_step"),
        ),
        migrations.AddConstraint(
            model_name="programenrollment",
            constraint=models.UniqueConstraint(fields=("user", "program"), name="unique_user_learning_program"),
        ),
        migrations.AddConstraint(
            model_name="programrelease",
            constraint=models.UniqueConstraint(fields=("enrollment", "step"), name="unique_program_step_release"),
        ),
    ]
