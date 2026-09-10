from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("skool", "0008_seed_bulk_skool_invitations")]

    operations = [
        migrations.AddField(
            model_name="skooluser",
            name="withdrawal_notice_accepted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Cayma/iade bildirimi kabul zamanı"),
        ),
        migrations.AddField(
            model_name="skooluser",
            name="withdrawal_notice_version",
            field=models.CharField(blank=True, max_length=24, verbose_name="Cayma/iade bildirimi sürümü"),
        ),
    ]
