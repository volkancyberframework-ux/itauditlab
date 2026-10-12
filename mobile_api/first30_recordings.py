"""Replace only first-month question audio with the user's approved 1.2x recordings."""
import hashlib,json
from pathlib import Path
from django.core.exceptions import ValidationError
from django.db import transaction
from .storage import PrivateVoiceStorage
ROOT=Path(__file__).resolve().parent.parent/'content/learning-paths/first-30-days/recorded-20261012'
KEY='first30_recorded_20261012'

def replace_recordings(*,dry_run=True):
    from .models import LearningPath,Question,AudioAsset
    manifest=json.loads((ROOT/'manifest.json').read_text())
    if [row['chapter'] for row in manifest]!=list(range(1,11)):raise ValidationError('Tam 10 sıralı kayıt gerekli.')
    storage=PrivateVoiceStorage()
    for row in manifest:
        name=f'first30-recorded-20261012/{row["filename"]}'
        with storage.open(name,'rb') as f:
            raw=f.read()
        if hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValidationError('Ses dosyası checksum hatası.')
        if abs(row['seconds']-row['source_seconds']/1.2)>0.15:raise ValidationError('Hız dönüşümü hatalı.')
    digest=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    with transaction.atomic():
        path=LearningPath.objects.select_for_update().get(pk=26)
        if path.owner_id or 'İşe Alındın! İlk 30 Günün' not in path.title:raise ValidationError('Hedef doğrulanamadı.')
        prefs=path.preferences or {};base=prefs.get('first30_v1',{});revision=prefs.get('first30_v2',{});applied=prefs.get(KEY,{})
        if not revision.get('enabled') or len(base.get('questions',{}))!=100:raise ValidationError('Önceki yayın doğrulanamadı.')
        if applied and applied.get('digest')!=digest:raise ValidationError('Farklı ses paketi; işlem durdu.')
        questions=[]
        for i in range(1,11):
            qid=base['questions'][f'grc-first30-q-{(i-1)*10+1:03}'];q=Question.objects.select_for_update().get(pk=qid)
            if q.kind!='audio' or set(q.paths.values_list('pk',flat=True))!={26}:raise ValidationError('Ses sorusu bağlantısı değişmiş.')
            expected=(applied['audio_ids'][str(i)] if applied.get('enabled') else revision['audio_ids'][str(i)])
            if q.audio_id!=expected:raise ValidationError('Ses elle değiştirilmiş; üzerine yazılmadı.')
            questions.append(q)
        report=dict(path_id=26,recordings=10,speed=1.2,original_question_ids_preserved=True,dry_run=dry_run,already_applied=bool(applied.get('enabled')))
        if dry_run or report['already_applied']:return report
        previous_audio={str(i):q.audio_id for i,q in enumerate(questions,1)};new_ids={}
        for i,(q,row) in enumerate(zip(questions,manifest),1):
            key=f'first30_recorded_20261012_day_{i:02}';name=f'first30-recorded-20261012/{row["filename"]}'
            existing=AudioAsset.objects.filter(name_key=key)
            if existing.count()>1:raise ValidationError('Tekrarlayan ses kaydı.')
            asset=existing.first()
            if asset and asset.file.name!=name:raise ValidationError('Mevcut kayıt farklı; değiştirilmedi.')
            if not asset:asset=AudioAsset.objects.create(name_key=key,title=f'İlk 30 Gün · {i}. Bölüm · Kendi kaydın (1,2×)',file=name)
            q.audio=asset;q.save(update_fields=['audio']);new_ids[str(i)]=asset.pk
        prefs[KEY]=dict(digest=digest,enabled=True,audio_ids=new_ids,previous_audio_ids=previous_audio,manifest=manifest)
        path.preferences=prefs;path.save(update_fields=['preferences'])
        return dict(report,replaced=10)

def restore_generated_recordings():
    from .models import LearningPath,Question
    with transaction.atomic():
        path=LearningPath.objects.select_for_update().filter(pk=26).first()
        if not path:return
        prefs=path.preferences or {};applied=prefs.get(KEY,{})
        if not applied.get('enabled'):return
        for i in range(1,11):
            qid=prefs['first30_v1']['questions'][f'grc-first30-q-{(i-1)*10+1:03}']
            q=Question.objects.get(pk=qid)
            if q.audio_id!=applied['audio_ids'][str(i)]:raise ValidationError('Ses bağlantısı elle değişmiş; geri alma durdu.')
            q.audio_id=applied['previous_audio_ids'][str(i)];q.save(update_fields=['audio'])
        applied['enabled']=False;prefs[KEY]=applied;path.preferences=prefs;path.save(update_fields=['preferences'])
