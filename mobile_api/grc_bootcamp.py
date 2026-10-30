"""Premium native and web GRC bootcamp course; immutable evidence and scoped deterministic import."""
import hashlib,json
from pathlib import Path
from collections import Counter
from functools import lru_cache
from django.core.exceptions import ValidationError
from django.db import transaction,connection
ROOT=Path(__file__).resolve().parent.parent/'content/learning-paths/grc-bootcamp'
ASSETS=Path(__file__).resolve().parent/'demo_assets/grc_bootcamp'
KEY='grc_bootcamp_v1'
FIELDS=('kind','prompt','context','options','answer','explanation','hint','difficulty','goals','base_xp','published','premium','order','card_pages','image')

def is_grc(path):return (path.preferences or {}).get(KEY,{}).get('enabled') is True

@lru_cache(maxsize=1)
def package():
    from PIL import Image
    from .models import Question
    p=json.loads((ROOT/'package.json').read_text());manifest=json.loads((ROOT/'images.json').read_text())
    qs=p['questions']
    if len(qs)!=80 or len({q['external_id'] for q in qs})!=80 or [q['number'] for q in qs]!=list(range(1,81)):
        raise ValidationError('80 benzersiz soru gerekli.')
    if [q['chapter'] for q in qs]!=[c for c in range(1,6) for _ in range(16)]:raise ValidationError('Bölüm sırası hatalı.')
    if Counter(q['difficulty'] for q in qs)!=Counter(beginner=32,intermediate=32,advanced=16):raise ValidationError('Zorluk dağılımı hatalı.')
    if len(manifest)!=80 or len({a['sha256'] for a in manifest})!=80:raise ValidationError('80 benzersiz görsel gerekli.')
    for q,m in zip(qs,manifest):
        if q['kind'] not in dict(Question.TYPES) or q['kind'] in ('audio','voice','info') or not q['answer'] or not q['explanation'] or not q['hint']:raise ValidationError('İçerik eksik.')
        if q['kind']!='image' or any(not q.get(k) for k in ('technical','risk','impact','control')):
            raise ValidationError('Her soru görselli ve beş parçalı açıklamalı olmalı.')
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
        with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_xact_lock(%s)',[310080041])
    matches=list(LearningPath.objects.select_for_update().filter(preferences__grc_bootcamp_v1__slug=p['slug']))
    if len(matches)>1:raise ValidationError('Tekrarlayan hedef; işlem durdu.')
    path=matches[0] if matches else None
    if not path and LearningPath.objects.filter(title=p['title']).exists():raise ValidationError('Kayıtsız aynı başlık; overwrite engellendi.')
    if path:
        reg=path.preferences[KEY]
        if path.owner_id or path.title!=p['title'] or reg['digest']!=digest or path.modules.count()!=5:raise ValidationError('Hedef kimliği/içeriği değişmiş.')
        if set(path.questions.values_list('pk',flat=True))!=set(reg['questions'].values()) or path.questions.count()!=80:raise ValidationError('Registry uyumsuz.')
        for row in p['questions']:
            q=path.questions.get(pk=reg['questions'][row['external_id']])
            if q.audio_id or q.intro_id or not q.module_id or q.module.path_id!=path.pk or q.module.order!=row['chapter'] or q.answer_options.exists():raise ValidationError('Soru ilişkisi veya yanıt kaynağı değişmiş.')
            if set(q.paths.values_list('id',flat=True))!={path.pk}:raise ValidationError('Soru başka yolla paylaşılmış.')
            if any((q.image.name if k=='image' else getattr(q,k))!=row[k] for k in FIELDS):raise ValidationError('Soru değiştirilmiş; overwrite engellendi.')
    report=dict(title=p['title'],path_id=path.pk if path else None,create=0 if path else 80,chapters={str(c):16 for c in range(1,6)},types=dict(Counter(q['kind'] for q in p['questions'])),images=80,audio=0,web_only=False,dry_run=dry_run)
    if dry_run:return report
    if path:
        prefs=path.preferences
        if not path.published:
            path.published=True;path.save(update_fields=['published'])
        if not prefs.get('web_published'):
            prefs['web_published']=True;path.preferences=prefs;path.save(update_fields=['preferences'])
        return dict(report,web_published=True)
    path=LearningPath.objects.create(title=p['title'],description=p['description'],icon='search',color='#166B5B',difficulty='beginner',minutes=240,order=45,published=True,premium=True)
    modules={c:Module.objects.create(path=path,title=p['modules'][c-1],order=c) for c in range(1,6)}
    ids={}
    for row in p['questions']:
        q=Question.objects.create(module=modules[row['chapter']],**{k:row[k] for k in FIELDS});q.paths.add(path);ids[row['external_id']]=q.pk
    path.preferences={KEY:dict(enabled=True,slug=p['slug'],digest=digest,questions=ids),'web_only':False,'web_published':True,'paid_only':True,'direct_start':True}
    path.save(update_fields=['preferences'])
    return dict(report,path_id=path.pk,created=80,web_published=True)


def assign_paid(path):
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    from django.utils import timezone
    from .models import Subscription,UserPathProgress
    now=timezone.now()
    subscribed=Subscription.objects.filter(status__in=['active','trial','grace_period'],expires_at__gt=now).values('user_id')
    eligible=get_user_model().objects.filter(is_active=True,is_mobile=True).filter(Q(mobile_full_access=True)|Q(mobile_paid_until__gt=now)|Q(pk__in=subscribed))
    count=0
    for user_id in eligible.values_list('pk',flat=True).iterator():
        _,created=UserPathProgress.objects.get_or_create(user_id=user_id,path=path)
        count+=created
    return count
