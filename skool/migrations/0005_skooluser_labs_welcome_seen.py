from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("skool", "0004_skoollab")]

    operations = [
        migrations.AddField(
            model_name="skooluser",
            name="labs_welcome_seen",
            field=models.BooleanField(default=False),
        ),
    ]
