from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('landing', '0011_daily_traffic_tracking')]
    operations = [
        migrations.CreateModel(
            name='CorporateInquiry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='Ad soyad')),
                ('email', models.EmailField(max_length=254, verbose_name='Kurumsal e-posta')),
                ('phone', models.CharField(max_length=40, verbose_name='Telefon')),
                ('company', models.CharField(max_length=160, verbose_name='Şirket')),
                ('employee_count', models.CharField(choices=[('1-10', '1–10'), ('11-50', '11–50'), ('51-250', '51–250'), ('251-1000', '251–1.000'), ('1000+', '1.000+')], max_length=20, verbose_name='Çalışan sayısı')),
                ('service', models.CharField(choices=[('it_audit', 'BT Denetim'), ('iso_readiness', 'ISO 27001 Uyum Hazırlığı'), ('technical_assessment', 'Teknik Siber Güvenlik Değerlendirmesi'), ('continuous_control', 'Sürekli Kontrol'), ('grc_control', 'GRC / Risk / Kontrol'), ('other', 'Diğer')], max_length=40, verbose_name='İlgilenilen hizmet')),
                ('message', models.TextField(verbose_name='İhtiyaç')),
                ('consent', models.BooleanField(default=False, verbose_name='İletişim izni')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Oluşturulma')),
            ], options={'verbose_name': 'Kurumsal görüşme talebi', 'verbose_name_plural': 'Kurumsal görüşme talepleri', 'ordering': ('-created_at',)}),
        migrations.CreateModel(
            name='PartnerApplication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120, verbose_name='Ad soyad')),
                ('email', models.EmailField(max_length=254, verbose_name='E-posta')),
                ('phone', models.CharField(max_length=40, verbose_name='Telefon')),
                ('linkedin', models.URLField(blank=True, verbose_name='LinkedIn')),
                ('company_role', models.CharField(max_length=180, verbose_name='Şirket / Pozisyon')),
                ('partnership_type', models.CharField(choices=[('sales', 'Satış / Referral Partner'), ('professional', 'GRC / Audit Professional'), ('both', 'Her İkisi')], max_length=20, verbose_name='Partnerlik tipi')),
                ('message', models.TextField(verbose_name='Birlikte çalışma fikri')),
                ('consent', models.BooleanField(default=False, verbose_name='İletişim izni')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Oluşturulma')),
            ], options={'verbose_name': 'Partnerlik başvurusu', 'verbose_name_plural': 'Partnerlik başvuruları', 'ordering': ('-created_at',)}),
    ]
