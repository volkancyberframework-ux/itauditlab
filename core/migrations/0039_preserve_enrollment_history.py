from django.db import migrations, models


def keep_rolling_deploy_defaults(apps, schema_editor):
    # Old workers may still insert enrollments while the new release is starting.
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute('ALTER TABLE core_enrollment ALTER COLUMN is_archived SET DEFAULT FALSE')
        schema_editor.execute('ALTER TABLE core_enrollment ALTER COLUMN restored_from_access SET DEFAULT FALSE')


class Migration(migrations.Migration):
    dependencies=[('core','0038_first_login_service_consent')]
    operations=[
        migrations.AddField(model_name='enrollment',name='is_archived',field=models.BooleanField(default=False,verbose_name='Arşivde',help_text='Öğrencinin listesinden kaldırılmıştır; geçmiş kayıt korunur.')),
        migrations.AddField(model_name='enrollment',name='restored_from_access',field=models.BooleanField(default=False,editable=False,verbose_name='Giriş kanıtından geri getirildi',help_text='Kayıt zamanı gerçek ilk ders erişiminden alınmıştır; özgün enrollment zamanı bilinmez.')),
        migrations.RunPython(keep_rolling_deploy_defaults,migrations.RunPython.noop),
    ]
