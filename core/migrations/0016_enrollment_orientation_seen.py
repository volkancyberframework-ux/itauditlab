from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0015_learning_program_automation")]

    operations = [
        migrations.AddField(
            model_name="enrollment",
            name="orientation_seen",
            field=models.BooleanField(default=False),
        ),
    ]
