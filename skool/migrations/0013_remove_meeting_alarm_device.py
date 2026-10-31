from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('skool', '0012_meetingalarmdevice')]
    operations = [migrations.DeleteModel(name='MeetingAlarmDevice')]
