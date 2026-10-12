"""Scoped, idempotent importer for the first 30 days learning path."""
import base64
import hashlib
import json
from collections import Counter
from pathlib import Path
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction

ROOT=Path(__file__).resolve().parent.parent/'content'/'learning-paths'/'first-30-days'
KEY='first30_v1'
FIELDS=('kind','prompt','context','options','answer','explanation','hint','difficulty','goals','base_xp','order','premium','published','card_pages')

def load_package(source=None):
    p=json.loads(Path(source or ROOT/'package.json').read_text())
    qs=p['questions'];types=Counter(q['kind'] for q in qs)
    if len(qs)!=100 or len({q['external_id'] for q in qs})!=100:raise ValidationError('100 benzersiz kayıt gerekli.')
    if [q['number'] for q in qs]!=list(range(1,101)):raise ValidationError('Sıra hatalı.')
    if Counter(q['chapter'] for q in qs)!=Counter({i:10 for i in range(1,11)}):raise ValidationError('Bölüm dağılımı hatalı.')
    if types!=Counter(info=10,choice=19,multi_select=10,fill_blank=10,image=9,scenario=22,sentence_order=10,drag_select=10):raise ValidationError('Tür dağılımı hatalı.')
    from .models import Question
    for q in qs:
        if q['kind'] not in dict(Question.TYPES) or not all(q[k] for k in ('prompt','context','explanation','goals')):raise ValidationError(q['external_id']+': içerik eksik.')
        ids=[o['id'] for o in q['options']]
        if q['kind'] not in ('fill_blank','info') and (len(ids)!=4 or len(set(ids))!=4 or not set(q['answer'])<=set(ids)):raise ValidationError('Yanıt eşleşmesi hatalı.')
        if q['kind']=='sentence_order' and set(q['answer'])!=set(ids):raise ValidationError('Sıralama eksik.')
        if q['kind']!='info' and not q['answer']:raise ValidationError('Cevap eksik.')
        if q['kind']=='image' and str(q['number']) not in p['images']:raise ValidationError('Görsel eksik.')
    return p

def import_package(*, source=None, path_id=26, dry_run=True):
    from .models import LearningPath, Module, Question
    p=load_package(source);digest=hashlib.sha256(json.dumps(p,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    with transaction.atomic():
        path=LearningPath.objects.select_for_update().filter(pk=path_id).first()
        if path and ('İşe Alındın! İlk 30 Günün' not in path.title or path.owner_id):raise ValidationError('ID / başlık / sahip doğrulaması başarısız; işlem yapılmadı.')
        if not path:raise ValidationError('Hedef yol bulunamadı. Kalıcı ID doğrulanmalıdır.')
        prefs=path.preferences or {};reg=prefs.get(KEY,{})
        owned=set(reg.get('questions',{}).values())
        existing=set(path.questions.values_list('id',flat=True))
        unmanaged=existing-owned
        if unmanaged:raise ValidationError(f'Hedefte {len(unmanaged)} kayıtlı olmayan soru var. Otomatik üzerine yazılmadı.')
        if reg and reg.get('digest')!=digest:raise ValidationError('Paket sürümü değişmiş. Mevcut cevapları korumak için otomatik overwrite engellendi.')
        if owned-existing:raise ValidationError('Registry / yol bağlantısı eksik. Otomatik çoğaltma engellendi.')
        report=dict(p['report'],path_id=path.pk,title=path.title,dry_run=dry_run,existing=len(existing),create=100-len(owned),other_paths_untouched=True,progress_preserved=True)
        if dry_run:return report
        module_ids=reg.get('modules',{})
        modules={}
        for index,title in enumerate(p['modules'],1):
            m=Module.objects.filter(pk=module_ids.get(str(index)),path=path).first()
            if not m:
                candidates=Module.objects.filter(path=path,title=title,order=index)
                if candidates.count()>1:raise ValidationError('Tekrarlayan bölüm kaydı.')
                m=candidates.first() or Module.objects.create(path=path,title=title,order=index)
            modules[index]=m
        qids={}
        for data in p['questions']:
            stable=data['external_id'];qid=reg.get('questions',{}).get(stable)
            if qid:
                q=Question.objects.get(pk=qid)
                if q.module_id!=modules[data['chapter']].pk or set(q.paths.values_list('id',flat=True))!={path.pk}:raise ValidationError('Kayıt başka kapsamla paylaşılıyor; işlem durdu.')
                if reg.get('enabled') is False:
                    q.published=True;q.save(update_fields=['published'])
                # Leave content and intro untouched on reruns; students retain attempts.
            else:
                q=Question.objects.create(module=modules[data['chapter']],**{k:data[k] for k in FIELDS})
                q.paths.add(path)
                if data['kind']=='image':
                    # Bundled immutable evidence also works in Render pre-deploy,
                    # where the service's persistent disk is not mounted.
                    name=f'first30/evidence_{data["number"]:03}.png'
                    if not q.image.storage.exists(name):raise ValidationError('Bundled evidence missing.')
                    q.image.name=name;q.save(update_fields=['image'])
            qids[stable]=q.pk
        prefs[KEY]=dict(enabled=True,slug=p['slug'],digest=digest,questions=qids,modules={str(n):m.pk for n,m in modules.items()},type_mapping=p['report']['text_mapping'],audio_intro_keys=[f'grc_day_{i:02}' for i in range(1,11)])
        path.preferences=prefs;path.description=p['description'];path.difficulty='beginner';path.minutes=180;path.published=True
        path.save(update_fields=['preferences','description','difficulty','minutes','published'])
        if path.questions.count()!=100:raise ValidationError('Son kayıt sayısı 100 değil; transaction geri alındı.')
        return dict(report,created=100-len(owned),published=True)
