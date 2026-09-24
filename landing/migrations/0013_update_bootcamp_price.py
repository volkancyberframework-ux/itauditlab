from django.db import migrations, models


def update_price(apps, schema_editor):
    SiteSetting = apps.get_model("landing", "SiteSetting")
    SiteSetting.objects.using(schema_editor.connection.alias).filter(
        bootcamp_price=59999
    ).update(bootcamp_price=89999)


def restore_price(apps, schema_editor):
    SiteSetting = apps.get_model("landing", "SiteSetting")
    SiteSetting.objects.using(schema_editor.connection.alias).filter(
        bootcamp_price=89999
    ).update(bootcamp_price=59999)


class Migration(migrations.Migration):
    dependencies = [("landing", "0012_corporate_leads")]
    operations = [
        migrations.AlterField(
            model_name="sitesetting",
            name="bootcamp_price",
            field=models.PositiveIntegerField(default=89999, verbose_name="Bootcamp fiyatı"),
        ),
        migrations.RunPython(update_price, restore_price),
    ]
