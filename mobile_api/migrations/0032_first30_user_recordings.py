from django.db import migrations

def publish(apps,schema_editor):
    Path=apps.get_model('mobile_api','LearningPath')
    path=Path.objects.filter(pk=26).first()
    if not path or not (path.preferences or {}).get('first30_v2',{}).get('enabled'):return
    from mobile_api.first30_recordings import replace_recordings
    replace_recordings(dry_run=False)

def restore(apps,schema_editor):
    from mobile_api.first30_recordings import restore_generated_recordings
    restore_generated_recordings()

class Migration(migrations.Migration):
    dependencies=[('mobile_api','0031_first30_variety_audio')]
    operations=[migrations.RunPython(publish,restore)]
