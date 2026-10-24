import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0031_seed_business_network')]

    operations = [
        migrations.CreateModel(
            name='WeeklyTelegramSchedule',
            fields=[
                ('id', models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                *[(name, models.TextField(blank=True, validators=[django.core.validators.MaxLengthValidator(3500)], verbose_name=label))
                  for name, label in [('monday', 'Pazartesi'), ('tuesday', 'Salı'), ('wednesday', 'Çarşamba'),
                                      ('thursday', 'Perşembe'), ('friday', 'Cuma'), ('saturday', 'Cumartesi'), ('sunday', 'Pazar')]],
            ],
            options={'verbose_name': 'Haftalık Telegram bildirimi', 'verbose_name_plural': 'Haftalık Telegram bildirimleri'},
        ),
        migrations.AddConstraint(
            model_name='weeklytelegramschedule',
            constraint=models.CheckConstraint(check=models.Q(id=1), name='weekly_telegram_singleton'),
        ),
    ]
