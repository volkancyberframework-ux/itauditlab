"""Publish only the verified first-30-days path; rollback hides, never erases history."""
from django.db import migrations

def publish(apps,schema_editor):
    # This path already exists in production. Fresh installations need an explicit
    # target selection, so this migration does not invent an ID there.
    Path=apps.get_model('mobile_api','LearningPath')
    if not Path.objects.filter(pk=26).exists():return
    from mobile_api.first30_content import import_package
    import_package(path_id=26,dry_run=False)

def hide(apps,schema_editor):
    Path=apps.get_model('mobile_api','LearningPath');Question=apps.get_model('mobile_api','Question')
    path=Path.objects.filter(pk=26).first()
    if not path or 'İşe Alındın! İlk 30 Günün' not in path.title:return
    reg=(path.preferences or {}).get('first30_v1',{})
    Question.objects.filter(pk__in=reg.get('questions',{}).values()).update(published=False)
    reg['enabled']=False
    path.preferences['first30_v1']=reg
    path.published=False;path.save(update_fields=['published','preferences'])

class Migration(migrations.Migration):
    dependencies=[('mobile_api','0029_web_all_types_demo')]
    operations=[migrations.RunPython(publish,hide)]
