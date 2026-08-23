from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("skool", "0004_skoollab"),
        ("core", "0017_mentorshiprequest"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentMeetingBooking",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("meeting_url", models.URLField()),
                ("status", models.CharField(choices=[("active", "Aktif"), ("completed", "Tamamlandı"), ("cancelled", "İptal")], db_index=True, default="active", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("request", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="booking", to="core.mentorshiprequest")),
                ("slot", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="student_booking", to="skool.meetingslot")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="student_meeting_bookings", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Öğrenci görüşme rezervasyonu",
                "verbose_name_plural": "Öğrenci görüşme rezervasyonları",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="studentmeetingbooking",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "active")), fields=("user",), name="one_active_normal_student_booking"),
        ),
    ]
