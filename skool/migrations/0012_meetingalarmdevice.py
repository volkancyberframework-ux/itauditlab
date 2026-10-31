from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('skool','0011_guest_accounts'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name='MeetingAlarmDevice', fields=[
        ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
        ('token_hash',models.CharField(editable=False,max_length=64,unique=True)),
        ('created_at',models.DateTimeField(auto_now_add=True)),
        ('expires_at',models.DateTimeField()),
        ('revoked_at',models.DateTimeField(blank=True,null=True)),
        ('owner',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,to=settings.AUTH_USER_MODEL)),
    ])]
