"""Scoped importer and feedback for an original, non-audio CISA simulation."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from django.core.exceptions import ValidationError
from django.db import transaction

ROOT = Path(__file__).resolve().parent.parent / 'content/learning-paths/cisa-auditor-simulator'
KEY = 'cisa_auditor_v1'
FIELDS = ('kind','prompt','context','options','answer','explanation','hint','difficulty','goals','base_xp','premium','published','order','card_pages')


def is_cisa(path):
    return (path.preferences or {}).get(KEY, {}).get('enabled') is True


def load_package():
    from .models import Question
    data = json.loads((ROOT / 'package.json').read_text())
    rows = data['questions']
    if len(rows) != 100 or len({q['external_id'] for q in rows}) != 100:
        raise ValidationError('100 benzersiz soru gerekli.')
    if [q['number'] for q in rows] != list(range(1, 101)):
        raise ValidationError('Soru sırası hatalı.')
    if [q['domain'] for q in rows] != [d for d in range(1, 6) for _ in range(20)]:
        raise ValidationError('Domain sırası veya sayısı hatalı.')
    allowed = {'choice','multi_select','sentence_order','drag_select','fill_blank','scenario'}
    for q in rows:
        if q['kind'] not in allowed or q['kind'] not in dict(Question.TYPES):
            raise ValidationError('Desteklenmeyen soru türü.')
        if not all(q[k] for k in ('prompt','context','explanation','answer','goals')):
            raise ValidationError('İçerik eksik: ' + q['external_id'])
        if any(t in q['explanation'].lower() for t in ('referans:', 'kaynak:', 'http', 'sayfa ')):
            raise ValidationError('Yanıt ekranına referans eklenemez.')
        keys = [o['id'] for o in q['options']]
        if len(keys) != len(set(keys)):
            raise ValidationError('Şık kimlikleri tekrarlanıyor.')
        if q['kind'] == 'fill_blank':
            if q['options'] or any(not isinstance(a,str) or not a.strip() for a in q['answer']):
                raise ValidationError('Metin yanıtı hatalı.')
        elif not set(q['answer']) <= set(keys) or not all(o.get('feedback') for o in q['options']):
            raise ValidationError('Seçenek yanıtı veya gerekçesi eksik.')
        if q['kind'] == 'sentence_order' and set(q['answer']) != set(keys):
            raise ValidationError('Sıralama eksik.')
        if q['kind'] in ('choice','scenario','drag_select') and len(q['answer']) != 1:
            raise ValidationError('Tek seçimde bir doğru yanıt gerekli.')
    return data


@transaction.atomic
def seed(*, dry_run=True):
    from .models import LearningPath, Module, Question
    data = load_package()
    digest = hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    # Serialize creation even when no target row exists; no existing content is changed.
    from django.db import connection
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [130013001])
    matches = list(LearningPath.objects.select_for_update().filter(preferences__cisa_auditor_v1__slug=data['slug']))
    if len(matches) > 1:
        raise ValidationError('Birden fazla kayıtlı hedef var; işlem durdu.')
    path = matches[0] if matches else None
    if not path and LearningPath.objects.filter(title=data['title']).exists():
        raise ValidationError('Aynı başlıklı kayıtsız yol var; üzerine yazılmadı.')
    if path:
        reg = path.preferences[KEY]
        if path.owner_id or path.title != data['title'] or reg['digest'] != digest:
            raise ValidationError('Kayıt kimliği veya paket değişmiş; overwrite engellendi.')
        if path.modules.count() != 5:
            raise ValidationError('Bölüm kayıtları değiştirilmiş.')
        ids = set(reg['questions'].values())
        if set(path.questions.values_list('pk',flat=True)) != ids or len(ids) != 100:
            raise ValidationError('Registry ile kayıtlar uyumsuz; çoğaltma engellendi.')
        for row in data['questions']:
            q = path.questions.get(pk=reg['questions'][row['external_id']])
            if q.audio_id or q.intro_id or not q.module_id or q.module.path_id != path.pk or q.module.order != row['domain']:
                raise ValidationError('Soru bölüm/medya ilişkisi değiştirilmiş.')
            if q.answer_options.exists():
                raise ValidationError('Yanıt kaynakları farklılaşmış; otomatik overwrite engellendi.')
            if set(q.paths.values_list('pk',flat=True)) != {path.pk} or any(getattr(q,k) != row[k] for k in FIELDS):
                raise ValidationError('Mevcut içerik değiştirilmiş; otomatik overwrite yapılmadı.')
    report = dict(title=data['title'],path_id=path.pk if path else None,create=0 if path else 100,
                  domains={str(d):20 for d in range(1,6)},types=dict(Counter(q['kind'] for q in data['questions'])),
                  audio=0,dry_run=dry_run,progress_preserved=True,other_paths_untouched=True)
    if dry_run:
        return report
    if path:
        if not path.published:
            path.published = True
            path.save(update_fields=["published"])
        return dict(report,published=True)
    path = LearningPath.objects.create(title=data['title'],description=data['description'],icon='school',color='#166B5B',difficulty='intermediate',minutes=240,premium=False,published=True,order=40)
    modules = {d:Module.objects.create(path=path,title=data['modules'][d-1],order=d) for d in range(1,6)}
    registry = {}
    for row in data['questions']:
        q = Question.objects.create(module=modules[row['domain']], **{k:row[k] for k in FIELDS})
        q.paths.add(path)
        registry[row['external_id']] = q.pk
    path.preferences = {KEY:dict(enabled=True,slug=data['slug'],digest=digest,questions=registry), 'direct_start':True}
    path.save(update_fields=['preferences'])
    return dict(report,path_id=path.pk,created=100,published=True)


def answer_key(q):
    """Use exactly the same source as Answer evaluation, including ordered IDs."""
    from .views import options
    opts, answers = options(q)
    if q.kind == 'sentence_order':
        answers = q.answer
    if q.kind in ('fill_blank','text'):
        return ['Beklenen cevap: '+str(q.answer[0])] + (['Kabul edilen alternatifler: '+', '.join(q.answer[1:])] if len(q.answer)>1 else [])
    texts = {o['id']:o['text'] for o in opts}
    return [(f'{i+1}. ' if q.kind == 'sentence_order' else '• ')+texts[a] for i,a in enumerate(answers)]


def explanation(q, submitted, correct):
    key = '✅ Doğru cevap:\n'+'\n'.join(answer_key(q))
    reason, work = q.explanation.split('\n\n💼 Gerçek iş hayatında\n',1)
    extra = ''
    if not correct:
        opts = {o['id']:o for o in q.options}
        if q.kind == 'sentence_order':
            values = submitted if isinstance(submitted,list) else []
            mismatch = next((i for i,a in enumerate(q.answer) if i>=len(values) or values[i]!=a),0)
            extra = f'{mismatch+1}. adımda “{opts[q.answer[mismatch]]["text"]}” gelmeli. '+reason.removeprefix('🧠 Neden doğru?\n')
        elif q.kind == 'fill_blank':
            extra = 'Yazdığın yanıt bu vaka için beklenen kavramla eşleşmedi. '+reason.removeprefix('🧠 Neden doğru?\n')
        else:
            chosen = submitted if isinstance(submitted,list) else []
            invalid = [a for a in chosen if a not in q.answer and a in opts]
            missing = [a for a in q.answer if a not in chosen]
            extra = '\n'.join('“'+opts[a]['text']+'”: '+opts[a]['feedback'] for a in invalid)
            if missing:
                extra += ('\n' if extra else '')+'Eksik doğru seçenekler:\n'+'\n'.join('“'+opts[a]['text']+'”: '+opts[a]['feedback'] for a in missing)
    return key+'\n\n'+reason+ ('\n\n❌ Senin cevabın neden uygun değil?\n'+extra if extra else '')+'\n\n💼 Gerçek iş hayatında\n'+work


def evaluation(session):
    """Latest attempt per question; no diagnosis or career suitability verdict."""
    from .models import QuestionAttempt
    from .models import Question
    attempts = QuestionAttempt.objects.filter(session__path=session.path,session__user=session.user,session__is_archived=False).select_related('question__module').order_by('created_at','pk')
    latest = {a.question_id:a for a in attempts}
    summaries = []
    for module in session.path.modules.order_by('order'):
        rows = [a for a in latest.values() if a.question.module_id == module.pk]
        if len(rows) != 20:
            continue
        correct = sum(a.is_correct for a in rows)
        strengths = [a.question.goals[0] for a in rows if a.is_correct]
        gaps = [a.question.goals[0] for a in rows if not a.is_correct]
        summaries.append(dict(domain=module.order,title=module.title,correct=correct,total=20,rate=correct*5,
                              strengths=strengths,development=gaps,
                              feedback='Kanıta dayalı kararlarını koru. Yanlış yaptığın vakalarda iş etkisini ve kontrol amacını yeniden karşılaştır.'))
    complete = len(latest) == 100
    text = []
    for item in summaries:
        text += [f'{item["title"]}\n{item["correct"]}/20 doğru · %{item["rate"]}',
                 'Güçlü konular: '+(', '.join(item['strengths']) or 'Henüz belirgin değil'),
                 'Gelişim konuları: '+(', '.join(item['development']) or 'Bu bölümde yanlış yanıt yok'), item['feedback']]
    if complete:
        # The five completed Domains correspond to concrete facets of auditing.
        facets=['Analitik düşünme ve kanıt','Risk ve iş süreçleri','Kontrol tasarımı','Operasyon ve dayanıklılık','Güvenlik kararları']
        text += ['Genel değerlendirme']+[f'{facets[i]}: {s["correct"]}/20' for i,s in enumerate(summaries)]
        text += ['Bu sonuç mesleğe uygunluk hakkında kesin hüküm vermez. Hangi görevlerden keyif aldığını düşün; gelişim konularını yeniden çalışarak ilerlemeni gözlemle.']
    return dict(domains=summaries,complete=complete,text='\n\n'.join(text))
