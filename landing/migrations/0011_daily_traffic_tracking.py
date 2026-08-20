from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('landing', '0010_newslettersubscriber')]

    operations = [
        migrations.CreateModel(
            name='DailyTrafficMetric',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True, verbose_name='Gün')),
                ('page_views', models.PositiveIntegerField(default=0, verbose_name='Sayfa görüntüleme')),
                ('filtered_bot_requests', models.PositiveIntegerField(default=0, verbose_name='Filtrelenen bot isteği')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Günlük trafik özeti', 'verbose_name_plural': 'Günlük trafik özetleri', 'ordering': ('-date',)},
        ),
        migrations.CreateModel(
            name='DailyTrafficReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_date', models.DateField(unique=True, verbose_name='Rapor günü')),
                ('sent_at', models.DateTimeField(auto_now_add=True, verbose_name='Gönderilme zamanı')),
            ],
            options={'verbose_name': 'Telegram trafik raporu', 'verbose_name_plural': 'Telegram trafik raporları', 'ordering': ('-report_date',)},
        ),
        migrations.CreateModel(
            name='LandingVisit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('visitor_hash', models.CharField(db_index=True, max_length=64, verbose_name='Anonim ziyaretçi özeti')),
                ('visit_date', models.DateField(db_index=True, verbose_name='Ziyaret günü')),
                ('first_path', models.CharField(default='/', max_length=255, verbose_name='İlk sayfa')),
                ('page_views', models.PositiveIntegerField(default=1, verbose_name='Sayfa görüntüleme')),
                ('is_returning', models.BooleanField(default=False, verbose_name='Geri dönen ziyaretçi')),
                ('first_seen', models.DateTimeField(auto_now_add=True, verbose_name='İlk görülme')),
                ('last_seen', models.DateTimeField(auto_now=True, verbose_name='Son görülme')),
            ],
            options={'verbose_name': 'Günlük tekil ziyaretçi', 'verbose_name_plural': 'Günlük tekil ziyaretçiler', 'ordering': ('-visit_date', '-last_seen')},
        ),
        migrations.AddConstraint(
            model_name='landingvisit',
            constraint=models.UniqueConstraint(fields=('visitor_hash', 'visit_date'), name='unique_landing_visitor_per_day'),
        ),
    ]
