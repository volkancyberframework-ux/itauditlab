from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0016_enrollment_orientation_seen"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MentorshipRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_type", models.CharField(choices=[("question", "Tek soru"), ("meeting", "Birebir görüşme")], max_length=16)),
                ("reason", models.TextField()),
                ("status", models.CharField(choices=[("pending", "Bekliyor"), ("answered", "Yanıtlandı"), ("scheduled", "Planlandı"), ("closed", "Kapandı")], db_index=True, default="pending", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mentorship_requests", to="core.course")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mentorship_requests", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Birebir destek talebi",
                "verbose_name_plural": "Birebir destek talepleri",
                "ordering": ("-created_at",),
            },
        ),
    ]
