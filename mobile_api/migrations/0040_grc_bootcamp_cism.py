from django.db import migrations


def publish(apps, schema_editor):
    from mobile_api.grc_bootcamp import seed as grc_seed, assign_paid
    from mobile_api.cism_manager import seed as cism_seed
    from mobile_api.models import LearningPath
    for seed in (grc_seed,cism_seed):
        result=seed(dry_run=False)
        result['assigned']=assign_paid(LearningPath.objects.get(pk=result['path_id']))
        print('Premium course publication:',result)


def hide(apps, schema_editor):
    Path=apps.get_model('mobile_api','LearningPath')
    Path.objects.filter(preferences__grc_bootcamp_v1__slug='grc-bootcamp-v1').update(published=False)
    Path.objects.filter(preferences__cism_manager_v1__slug='cism-manager-v1').update(published=False)


class Migration(migrations.Migration):
    dependencies=[('mobile_api','0039_daily_kpi_report')]
    operations=[migrations.RunPython(publish,hide)]
