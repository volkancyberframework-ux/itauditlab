from django.db import migrations
from mobile_api.web_demo import seed_web_demo


class Migration(migrations.Migration):
    dependencies = [('mobile_api', '0028_personalappaddress')]
    operations = [migrations.RunPython(seed_web_demo, migrations.RunPython.noop)]
