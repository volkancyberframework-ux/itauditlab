from django.db import migrations, models


def update_contact_email(apps, schema_editor):
    SiteSetting = apps.get_model('landing', 'SiteSetting')
    SiteSetting.objects.filter(
        contact_email__in=['info@grcmastery.com', 'merhaba@grcustasi.com']
    ).update(contact_email='destek@grcustasi.co')


class Migration(migrations.Migration):
    dependencies = [('landing', '0007_seed_job_market_counts')]

    operations = [
        migrations.AlterField(
            model_name='sitesetting',
            name='contact_email',
            field=models.EmailField(default='destek@grcustasi.co', max_length=254, verbose_name='İletişim e-postası'),
        ),
        migrations.RunPython(update_contact_email, migrations.RunPython.noop),
    ]
