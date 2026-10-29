from django.db import migrations

def publish(apps,schema_editor):
    from mobile_api.database_auditor import seed,assign_paid
    from mobile_api.models import LearningPath
    result=seed(dry_run=False)
    result['assigned']=assign_paid(LearningPath.objects.get(pk=result['path_id']))
    print('Database audit publication:', result)

def hide(apps,schema_editor):
    Path=apps.get_model('mobile_api','LearningPath')
    Path.objects.filter(preferences__database_auditor_v1__slug='database-auditor-v1').update(published=False)
class Migration(migrations.Migration):
    dependencies=[('mobile_api','0036_linux_auditor')]
    operations=[migrations.RunPython(publish,hide)]
