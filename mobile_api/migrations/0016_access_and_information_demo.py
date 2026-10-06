from django.db import migrations


def configure_access(apps, schema_editor):
    User = apps.get_model('core', 'CustomUser')
    Settings = apps.get_model('mobile_api', 'MobileSettings')
    Path = apps.get_model('mobile_api', 'LearningPath')
    Question = apps.get_model('mobile_api', 'Question')
    # Preserve existing mobile users' full access; public registration remains free.
    User.objects.filter(is_mobile=True).update(mobile_full_access=True)
    path = Path.objects.filter(title='Demo • Tüm Soru Tipleri', owner=None).first()
    Settings.objects.get_or_create(pk=1, defaults={'free_path': path})
    if path:
        for question in path.questions.filter(order__gte=3):
            question.order += 1
            question.save(update_fields=['order'])
        card = Question.objects.create(kind='info', prompt='Riski üç adımda anlat', order=3,
            published=True, base_xp=0, card_pages=[
                {'title': '1 • Neden', 'body': 'Risk cümlesi **kontrol eksikliği** ile başlar.\n\n*Yedekleme yapılmaması nedeniyle…*', 'reveal': 'Neden: Riski mümkün kılan durum. Bir olayın kendisi değildir.'},
                {'title': '2 • Olay', 'body': 'Sonra **ne gerçekleşebilir?** sorusunu yanıtla.\n\n*…disk arızasında müşteri verilerinin kaybolması…*', 'reveal': 'Olay: Gerçekleşmesi belirsiz olan durum. Burada veri kaybı.'},
                {'title': '3 • Etki', 'body': 'Son olarak iş sonucunu ekle: **hizmet kesintisi** veya **finansal kayıp**.\n\n*…ve hizmetlerin aksaması riski vardır.*', 'reveal': 'Neden → Olay → Etki. Açık ve somut bir risk cümlesi için bu üç parçayı birleştir.'},
            ])
        card.paths.add(path)
        path.description = '10 soru tipi ve araya yerleştirilmiş kaydırmalı bilgi kartı. Yazılı veya sesli yanıtı da dene.'
        path.save(update_fields=['description'])
    Question.objects.filter(paths=path, kind='voice', answer=[]).update(
        answer=['veri kaybı'],
        prompt='Sesli veya yazılı yanıt: Bu senaryonun riskini iki kelimeyle yaz (ilk kelime: veri) ya da kendi cümlenle sesli anlat.',
        context='Müşteri verileri yedeksiz bir bilgisayarda tutuluyor. Yazılı yanıt otomatik kontrol edilir. Sesli mesaj üzerinden geri bildirim e-posta yoluyla 24 saat içinde incelenip verilecektir.',
        explanation='Doğru kısa yanıt: veri kaybı. Yedek bulunmaması nedeniyle, disk arızasında müşteri verilerinin kaybolması ve hizmetlerin aksaması riski vardır.',
    )


class Migration(migrations.Migration):
    dependencies = [('mobile_api', '0015_question_card_pages_voicesubmission_feedback_sent_at_and_more'), ('core', '0024_customuser_mobile_full_access')]
    operations = [migrations.RunPython(configure_access, migrations.RunPython.noop)]
