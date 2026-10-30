from importlib import import_module
from django.db import migrations


def backfill(apps, schema_editor):
    # Core may migrate before mobile on a fresh installation. Complete the
    # activity bootstrap only after every historical mobile event table exists.
    import_module('core.migrations.0035_account_inactivity_policy').backfill_access(apps, schema_editor)


class Migration(migrations.Migration):
    dependencies=[('mobile_api','0040_grc_bootcamp_cism'),('core','0035_account_inactivity_policy')]
    operations=[migrations.RunPython(backfill,migrations.RunPython.noop)]
