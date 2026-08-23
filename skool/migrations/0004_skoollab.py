from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("skool", "0003_booking_completed_status")]

    operations = [
        migrations.CreateModel(
            name="SkoolLab",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=180, verbose_name="Çalışma adı")),
                ("description", models.TextField(blank=True, verbose_name="Açıklama")),
                ("pdf", models.FileField(upload_to="skool_labs/", verbose_name="Laboratuvar PDF'i")),
                ("order", models.PositiveSmallIntegerField(default=0, verbose_name="Sıra")),
                ("is_active", models.BooleanField(default=True, verbose_name="Yayında")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ("order", "title"), "verbose_name": "Skool laboratuvarı", "verbose_name_plural": "Skool laboratuvarları"},
        ),
    ]
