from django.db import migrations

def publish(apps,schema_editor):
    from mobile_api.ad_auditor import seed
    seed(dry_run=False)

def hide(apps,schema_editor):
    Path=apps.get_model('mobile_api','LearningPath')
    for path in Path.objects.filter(preferences__ad_auditor_v1__slug='ad-auditor-v1'):
        prefs=path.preferences;prefs['web_published']=False;path.preferences=prefs;path.save(update_fields=['preferences'])
class Migration(migrations.Migration):
    dependencies=[('mobile_api','0033_cisa_auditor_simulator')]
    operations=[migrations.RunPython(publish,hide)]
