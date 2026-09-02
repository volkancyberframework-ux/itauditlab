from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("skool", "0006_seed_grc_ustasi_labs")]

    operations = [
        migrations.CreateModel(
            name="SkoolLabProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("completed_at", models.DateTimeField(auto_now_add=True)),
                ("lab", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_progress", to="skool.skoollab")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lab_progress", to="skool.skooluser")),
            ],
            options={"verbose_name": "Laboratuvar ilerlemesi", "verbose_name_plural": "Laboratuvar ilerlemeleri", "ordering": ("completed_at",)},
        ),
        migrations.AddConstraint(
            model_name="skoollabprogress",
            constraint=models.UniqueConstraint(fields=("user", "lab"), name="unique_skool_lab_progress"),
        ),
    ]
