from django.conf import settings
from django.db import migrations


def enable_demo(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    User.objects.using(schema_editor.connection.alias).filter(
        username__in=["mobile_demo_oct2026", "device_demo"]
    ).update(is_mobile=True)


class Migration(migrations.Migration):
    dependencies = [
        ("mobile_api", "0007_live_demo_content"),
        ("core", "0023_customuser_is_mobile_customuser_mobile_last_date"),
    ]
    operations = [migrations.RunPython(enable_demo, migrations.RunPython.noop)]
