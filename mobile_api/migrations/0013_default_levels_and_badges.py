from django.db import migrations


def defaults(apps, schema_editor):
    Settings = apps.get_model('mobile_api', 'LevelSettings')
    Reward = apps.get_model('mobile_api', 'LevelReward')
    Settings.objects.get_or_create(pk=1, defaults={'xp_per_level': 100})
    for level, title in [(1, 'Usta adayı rozeti'), (3, 'Risk avcısı rozeti'), (5, 'Kontrol ustası rozeti')]:
        Reward.objects.get_or_create(level=level, defaults={
            'title': title, 'description': 'Bu seviyeye ulaştığında dijital rozetin profilinde görünür.',
            'kind': 'badge', 'published': True,
        })


class Migration(migrations.Migration):
    dependencies = [('mobile_api', '0012_userlevelreward_and_more')]
    operations = [migrations.RunPython(defaults, migrations.RunPython.noop)]
