from django.db import migrations


def restore_accounts(apps, schema_editor):
    User = apps.get_model('core', 'CustomUser')
    users = User.objects.using(schema_editor.connection.alias)
    count = users.filter(is_active=False, inactivity_disabled_at__isnull=False).update(
        is_active=True, inactivity_disabled_at=None)
    users.filter(inactivity_disabled_at__isnull=False).update(inactivity_disabled_at=None)
    print(f'Cancelled inactivity policy: {count} accounts restored. Other disabled accounts unchanged.')


class Migration(migrations.Migration):
    dependencies=[('core','0036_inactivity_telegram_report')]
    operations=[migrations.RunPython(restore_accounts,migrations.RunPython.noop)]
