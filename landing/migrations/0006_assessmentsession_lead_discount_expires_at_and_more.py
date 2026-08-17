from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('landing', '0005_lead_career_clarity_lead_effort_awareness_and_more')]
    operations = [
        migrations.CreateModel(
            name='AssessmentSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='E-posta')),
                ('profile_type', models.CharField(choices=[('student', 'Üniversite öğrencisi'), ('graduate', 'Yeni mezun'), ('working', 'Çalışıyor')], max_length=20, verbose_name='Profil')),
                ('answers', models.JSONField(blank=True, default=dict, verbose_name='Anket cevapları')),
                ('discount_percent', models.PositiveSmallIntegerField(default=15, verbose_name='İndirim oranı')),
                ('discount_expires_at', models.DateTimeField(verbose_name='İndirim son tarihi')),
                ('completed', models.BooleanField(default=False, verbose_name='Tamamlandı')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Başlangıç')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Son hareket')),
            ],
            options={'verbose_name': 'Kariyer pusulası kaydı', 'verbose_name_plural': 'Kariyer pusulası kayıtları', 'ordering': ['-updated_at']},
        ),
        migrations.AddField(model_name='lead', name='discount_expires_at', field=models.DateTimeField(blank=True, null=True, verbose_name='İndirim son tarihi')),
        migrations.AddField(model_name='lead', name='discount_percent', field=models.PositiveSmallIntegerField(default=15, verbose_name='İndirim oranı')),
    ]
