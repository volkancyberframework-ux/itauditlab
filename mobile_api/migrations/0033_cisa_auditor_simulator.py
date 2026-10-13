from django.db import migrations

def publish(apps,schema_editor):
    from mobile_api.cisa_simulator import seed
    seed(dry_run=False)

def unpublish(apps,schema_editor):
    # Reversible visibility rollback, never delete attempts, scores or content.
    Path=apps.get_model('mobile_api','LearningPath')
    for path in Path.objects.filter(preferences__cisa_auditor_v1__slug='cisa-auditor-simulator-v1'):
        path.published=False
        path.save(update_fields=['published'])

class Migration(migrations.Migration):
    dependencies=[('mobile_api','0032_first30_user_recordings')]
    operations=[migrations.RunPython(publish,unpublish)]
