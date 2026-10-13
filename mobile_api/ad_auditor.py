"""Web-only AD course; immutable evidence and scoped deterministic import."""
import hashlib,json
from pathlib import Path
from collections import Counter
from functools import lru_cache
from django.core.exceptions import ValidationError
from django.db import transaction,connection
ROOT=Path(__file__).resolve().parent.parent/'content/learning-paths/ad-auditor'
ASSETS=Path(__file__).resolve().parent/'demo_assets/ad_auditor'
KEY='ad_auditor_v1'
FIELDS=('kind','prompt','context','options','answer','explanation','hint','difficulty','goals','base_xp','published','premium','order','card_pages','image')

def is_ad(path):return (path.preferences or {}).get(KEY,{}).get('enabled') is True

@lru_cache(maxsize=1)
def package():
    from PIL import Image
    from .models import Question
    p=json.loads((ROOT/'package.json').read_text());manifest=json.loads((ROOT/'images.json').read_text())
    qs=p['questions']
    if len(qs)!=75 or len({q['external_id'] for q in qs})!=75 or [q['number'] for q in qs]!=list(range(1,76)):
        raise ValidationError('75 benzersiz soru gerekli.')
    if [q['chapter'] for q in qs]!=[c for c in range(1,6) for _ in range(15)]:raise ValidationError('Bölüm sırası hatalı.')
    if Counter(q['difficulty'] for q in qs)!=Counter(beginner=30,intermediate=35,advanced=10):raise ValidationError('Zorluk dağılımı hatalı.')
    if len(manifest)!=75 or len({a['sha256'] for a in manifest})!=75:raise ValidationError('75 benzersiz görsel gerekli.')
    for q,m in zip(qs,manifest):
        if q['kind'] not in dict(Question.TYPES) or q['kind'] in ('audio','voice','info') or not q['answer'] or not q['explanation'] or not q['hint']:raise ValidationError('İçerik eksik.')
        keys={o['id'] for o in q['options']}
        if q['kind']!='fill_blank' and not set(q['answer'])<=keys:raise ValidationError('Cevap eşleşmesi hatalı.')
        if q['kind']=='sentence_order' and set(q['answer'])!=keys:raise ValidationError('Sıralama eksik.')
        if q['kind']=='multi_select' and len(q['answer'])<2:raise ValidationError('Çoklu seçim eksik.')
        if m['number']!=q['number'] or m['file']!=q['image']:raise ValidationError('Görsel/soru eşleşmesi hatalı.')
        f=ASSETS/Path(q['image']).name
        if hashlib.sha256(f.read_bytes()).hexdigest()!=m['sha256']:raise ValidationError('Görsel bütünlüğü hatalı.')
        with Image.open(f) as im:
            if im.size!=(2560,1440):raise ValidationError('Görsel çözünürlüğü hatalı.')
            im.verify()
    return p,manifest

@transaction.atomic
def seed(*,dry_run=True):
    from .models import LearningPath,Module,Question
    p,manifest=package();digest=hashlib.sha256(json.dumps([p,manifest],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    if connection.vendor=='postgresql':
        with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_xact_lock(%s)',[130075013])
    matches=list(LearningPath.objects.select_for_update().filter(preferences__ad_auditor_v1__slug=p['slug']))
    if len(matches)>1:raise ValidationError('Tekrarlayan hedef; işlem durdu.')
    path=matches[0] if matches else None
    if not path and LearningPath.objects.filter(title=p['title']).exists():raise ValidationError('Kayıtsız aynı başlık; overwrite engellendi.')
    if path:
        reg=path.preferences[KEY]
        if path.owner_id or path.title!=p['title'] or reg['digest']!=digest or path.modules.count()!=5:raise ValidationError('Hedef kimliği/içeriği değişmiş.')
        if set(path.questions.values_list('pk',flat=True))!=set(reg['questions'].values()) or path.questions.count()!=75:raise ValidationError('Registry uyumsuz.')
        for row in p['questions']:
            q=path.questions.get(pk=reg['questions'][row['external_id']])
            if q.audio_id or q.intro_id or not q.module_id or q.module.path_id!=path.pk or q.module.order!=row['chapter'] or q.answer_options.exists():raise ValidationError('Soru ilişkisi veya yanıt kaynağı değişmiş.')
            if set(q.paths.values_list('id',flat=True))!={path.pk}:raise ValidationError('Soru başka yolla paylaşılmış.')
            if any((q.image.name if k=='image' else getattr(q,k))!=row[k] for k in FIELDS):raise ValidationError('Soru değiştirilmiş; overwrite engellendi.')
    report=dict(title=p['title'],path_id=path.pk if path else None,create=0 if path else 75,chapters={str(c):15 for c in range(1,6)},types=dict(Counter(q['kind'] for q in p['questions'])),images=75,audio=0,web_only=True,dry_run=dry_run)
    if dry_run:return report
    if path:
        prefs=path.preferences
        if not prefs.get('web_published'):
            prefs['web_published']=True;path.preferences=prefs;path.save(update_fields=['preferences'])
        return dict(report,web_published=True)
    path=LearningPath.objects.create(title=p['title'],description=p['description'],icon='search',color='#166B5B',difficulty='beginner',minutes=180,order=41,published=False)
    modules={c:Module.objects.create(path=path,title=p['modules'][c-1],order=c) for c in range(1,6)}
    ids={}
    for row in p['questions']:
        q=Question.objects.create(module=modules[row['chapter']],**{k:row[k] for k in FIELDS});q.paths.add(path);ids[row['external_id']]=q.pk
    path.preferences={KEY:dict(enabled=True,slug=p['slug'],digest=digest,questions=ids),'web_only':True,'web_published':True}
    path.save(update_fields=['preferences'])
    return dict(report,path_id=path.pk,created=75,web_published=True)

def feedback(q,submitted,correct):
    from .cisa_simulator import answer_key
    row=package()[0]['questions'][q.order-1]
    result='✅ Doğru cevap\n'+'\n'.join(answer_key(q))+'\n\n'+q.explanation
    if not correct:
        opts={o['id']:o['text'] for o in q.options}
        if q.kind=='sentence_order':
            mismatch=next((i for i,a in enumerate(q.answer) if i>=len(submitted) or submitted[i]!=a),0)
            reason=f'{mismatch+1}. adımda “{opts[q.answer[mismatch]]}” gelmeli. '+row['hint']
        elif q.kind=='fill_blank':reason='Yazdığın yanıt ekrandaki alan için beklenen kavram veya değerle eşleşmedi. '+row['hint']
        else:
            reason='\n'.join('“'+opts[a]+'”: '+row['feedback'][a] for a in submitted if a in opts and a not in q.answer)
            missing=[a for a in q.answer if a not in submitted]
            if missing:reason+='\nEksik doğru seçenekler: '+'; '.join(opts[a] for a in missing)
        result+='\n\n❌ Bu cevap neden uygun değil?\n'+reason
    return result
