from django.db import migrations

def update(apps,schema_editor):
    Path=apps.get_model('mobile_api','LearningPath')
    path=Path.objects.filter(pk=26).first()
    if not path or not (path.preferences or {}).get('first30_v1'):return
    from mobile_api.first30_revision import apply_revision
    apply_revision(dry_run=False)

def restore(apps,schema_editor):
    from mobile_api.first30_revision import rollback_revision
    rollback_revision()

class Migration(migrations.Migration):
    dependencies=[('mobile_api','0030_first30_program')]
    operations=[migrations.RunPython(update,restore)]
