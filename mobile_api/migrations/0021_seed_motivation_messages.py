from django.db import migrations


def seed(apps, schema_editor):
    Message = apps.get_model('mobile_api', 'MotivationMessage')
    if not Message.objects.exists():
        for index, body in enumerate([
            'Bugün bir vakayı çöz. Bir riski daha net görmek, yarının güçlü kararının ilk adımıdır.',
            'Küçük adımlar, güçlü bir uzmanlık. Bugün 5 dakikanı kendine ve bir GRC görevine ayır.',
            'Senaryoyu oku, kararını ver, nedenini düşün. Öğrendiğin bilgi uyguladıkça senin olur.',
            'Mükemmel olmak zorunda değilsin. Bir soruyu dene, geri bildirimi oku ve dünden bir adım ileri git.',
            'Gerçek hayatta iyi kararlar pratikle gelişir. Bugünkü öğrenme yolculuğuna kaldığın yerden devam et.',
        ]):
            Message.objects.create(body=body, order=index)


class Migration(migrations.Migration):
    dependencies = [('mobile_api', '0020_mobileadminalert_motivationmessage_and_more')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
