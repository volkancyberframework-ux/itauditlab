"""Explicit presentation revision; preserves question IDs, answers, attempts and XP."""
import hashlib,json
from collections import Counter
from pathlib import Path
from django.core.exceptions import ValidationError
from django.db import transaction
from .first30_content import ROOT,FIELDS,KEY
REVISION_ROOT=ROOT/'v2'
REVISION_KEY='first30_v2'
CYCLE=['audio','multi_select','sentence_order','drag_select','fill_blank','image','scenario','choice','scenario','info']

def load_revision():
    package=json.loads((REVISION_ROOT/'package.json').read_text())
    records=package['questions']
    if len(records)!=100 or len({q['external_id'] for q in records})!=100:raise ValidationError('100 benzersiz soru gerekli.')
    if [q['order'] for q in records]!=list(range(1,101)) or [q['kind'] for q in records]!=CYCLE*10:raise ValidationError('Tür döngüsü veya sıra hatalı.')
    old={q['external_id']:q for q in json.loads((ROOT/'package.json').read_text())['questions']}
    for q in records:
        if q['answer']!=old[q['external_id']]['answer']:raise ValidationError('Eski cevap anahtarı değiştirilmiş.')
        if q['kind']=='info' and (len(q['card_pages'])!=4 or sum(len(p['body'].split()) for p in q['card_pages'])<130):raise ValidationError('Öğretici kart eksik.')
        if q['chapter']!=old[q['external_id']]['chapter']:raise ValidationError('Bölüm kimliği değişmiş.')
    digest=hashlib.sha256(json.dumps(package,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return package,digest

def apply_revision(*,dry_run=True,path_id=26):
    from .models import LearningPath,Question,AudioAsset,LearningSession
    package,digest=load_revision()
    source=json.loads((ROOT/'package.json').read_text());source_digest=hashlib.sha256(json.dumps(source,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    with transaction.atomic():
        path=LearningPath.objects.select_for_update().get(pk=path_id)
        if path.owner_id or 'İşe Alındın! İlk 30 Günün' not in path.title:raise ValidationError('Hedef doğrulanamadı.')
        prefs=path.preferences or {};base=prefs.get(KEY,{});revision=prefs.get(REVISION_KEY,{})
        if len(base.get('questions',{}))!=100 or base.get('digest')!=source_digest:raise ValidationError('Önceki paket doğrulanamadı.')
        if revision and revision.get('digest')!=digest:raise ValidationError('Farklı revizyon; otomatik overwrite engellendi.')
        ids=set(base['questions'].values())
        if set(path.questions.values_list('pk',flat=True))!=ids:raise ValidationError('Yol / registry bağlantısı değişmiş.')
        rows={q.pk:q for q in Question.objects.select_for_update().filter(pk__in=ids)}
        old={q['external_id']:q for q in source['questions']}
        for q in rows.values():
            if set(q.paths.values_list('pk',flat=True))!={path.pk}:raise ValidationError('Paylaşılan soru değiştirilemez.')
        if not revision:
            for stable,qid in base['questions'].items():
                q=rows[qid]
                if any(getattr(q,k)!=old[stable][k] for k in FIELDS):raise ValidationError(f'{stable}: mevcut içerik elle düzenlenmiş; üzerine yazılmadı.')
        from .storage import PrivateVoiceStorage
        storage=PrivateVoiceStorage()
        for i in range(1,11):
            name=f'first30-v2/grc_day_{i:02}.mp3'
            with storage.open(name,'rb') as f:
                header=f.read(3)
                if header!=b'ID3' and not (header[0]==255 and header[1]&224==224):raise ValidationError('Ses dosyası geçersiz.')
        report=dict(package['report'],path_id=path.pk,dry_run=dry_run,already_applied=bool(revision and revision.get('enabled')),attempts_and_xp_preserved=True)
        if dry_run or report['already_applied']:return report
        if not revision:
            backup={str(qid):dict({k:getattr(q,k) for k in FIELDS},image=rows[qid].image.name,audio_id=rows[qid].audio_id,intro_id=rows[qid].intro_id) for qid,q in rows.items()}
            revision=dict(backup=backup,previous_description=path.description)
        audio_ids={}
        for i in range(1,11):
            key=f'first30_v2_grc_day_{i:02}';matches=AudioAsset.objects.filter(name_key=key)
            if matches.count()>1:raise ValidationError('Tekrarlayan ses kaydı.')
            name=f'first30-v2/grc_day_{i:02}.mp3';asset=matches.first()
            if asset and asset.file.name!=name:raise ValidationError('Mevcut ses kaydına dokunulmadı.')
            if not asset:asset=AudioAsset.objects.create(title=f'İlk 30 Gün · {i}. Bölüm · Türkçe sahne',file=name,name_key=key)
            audio_ids[str(i)]=asset.pk
        order_map={}
        for record in package['questions']:
            q=rows[base['questions'][record['external_id']]]
            for field in FIELDS:setattr(q,field,record[field])
            if q.kind=='audio':q.audio_id=audio_ids[str(record['chapter'])]
            if record['source_number']==8:q.image.name='first30-v2/evidence_008.png'
            q.save();order_map[q.pk]=q.order
        # Reorder only unanswered positions in existing sessions. Keep attempted
        # positions and every session/attempt ID intact.
        for session in LearningSession.objects.select_for_update().filter(path=path,completed_at__isnull=True,is_archived=False):
            attempted=set(session.attempts.values_list('question_id',flat=True))
            unattempted=iter(sorted([i for i in session.questions if i not in attempted],key=lambda i:order_map.get(i,10000)))
            session.questions=[i if i in attempted else next(unattempted) for i in session.questions]
            session.save(update_fields=['questions'])
        revision.update(digest=digest,enabled=True,audio_ids=audio_ids,cycle=CYCLE,report=package['report'])
        prefs[REVISION_KEY]=revision;path.preferences=prefs
        path.description='NEXORA’da ilk 30 günün: karakterlerin rolleri açık, her bölümde farklı soru türleri. Türkçe sesli sahneler, görsel kanıtlar ve 40 sayfalık öğretici kartlarla karar vererek öğren.'
        path.save(update_fields=['preferences','description'])
        return dict(report,updated=100)

def rollback_revision():
    from .models import LearningPath,Question
    with transaction.atomic():
        path=LearningPath.objects.select_for_update().filter(pk=26).first()
        if not path:return
        revision=(path.preferences or {}).get(REVISION_KEY,{})
        if not revision.get('enabled'):return
        for qid,data in revision['backup'].items():
            q=Question.objects.get(pk=int(qid))
            for key,value in data.items():setattr(q,key,value)
            q.save()
        revision['enabled']=False;path.preferences[REVISION_KEY]=revision
        path.description=revision['previous_description'];path.save(update_fields=['preferences','description'])
