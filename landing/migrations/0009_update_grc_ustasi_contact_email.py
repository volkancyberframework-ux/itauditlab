from django.db import migrations, models


def update_contact_email(apps, schema_editor):
    SiteSetting = apps.get_model('landing', 'SiteSetting')
    SiteSetting.objects.filter(contact_email='destek@grcustasi.co').update(
        contact_email='volkan@grcustasi.com'
    )


class Migration(migrations.Migration):
    dependencies = [('landing', '0008_update_contact_email')]

    operations = [
        migrations.RunPython(update_contact_email, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='sitesetting',
            name='contact_email',
            field=models.EmailField(
                default='volkan@grcustasi.com',
                max_length=254,
                verbose_name='İletişim e-postası',
            ),
        ),
    ]
