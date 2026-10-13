"""Atomic replacement of existing named audio assets; old files and question IDs stay intact."""
import hashlib,io,json,zipfile
from pathlib import Path
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from .models import AudioAsset
from .storage import PrivateVoiceStorage

def inspect_package(upload):
    with zipfile.ZipFile(upload) as archive:
        infos=archive.infolist()
        if len(infos)!=20 or sum(i.file_size for i in infos)>30*1024*1024:raise ValidationError('19 MP3 ve manifest.json içeren paket gerekli.')
        expected={f'ses{i}.mp3' for i in range(1,19)}|{'tanıtım.mp3','manifest.json'}
        if set(i.filename for i in infos)!=expected or len({i.filename for i in infos})!=len(infos):raise ValidationError('Dosya adları veya sayısı geçersiz.')
        manifest=json.loads(archive.read('manifest.json'));rows=manifest.get('files',[])
        if len(rows)!=19 or manifest.get('speed')!=1.2:raise ValidationError('1,2× kayıt paketi gerekli.')
        files={}
        for row in rows:
            name=Path(row['output']).name
            if name not in expected-{'manifest.json'} or name in files:raise ValidationError('Manifest eşleşmesi hatalı.')
            raw=archive.read(name)
            if not 1000<len(raw)<10*1024*1024 or not(raw[:3]==b'ID3' or raw[0]==255 and raw[1]&224==224):raise ValidationError('MP3 başlığı veya boyutu geçersiz.')
            if hashlib.sha256(raw).hexdigest()!=row['output_sha256']:raise ValidationError('Ses checksum eşleşmedi.')
            if abs(row['output_seconds']-row['source_seconds']/1.2)>.15:raise ValidationError('Hız/duration eşleşmedi.')
            files[name]=(raw,row['output_sha256'])
        if set(files)!=expected-{'manifest.json'}:raise ValidationError('Dosyalar eksik.')
    return files

@transaction.atomic
def replace_package(upload,*,apply=False):
    files=inspect_package(upload);storage=PrivateVoiceStorage();changes=[]
    for name,(raw,digest) in files.items():
        title=Path(name).stem
        qs=AudioAsset.objects.select_for_update().filter(title__iexact=title)
        if qs.count()==0 and title=='tanıtım':asset=AudioAsset(title=title,name_key=title)
        elif qs.count()==1:asset=qs.get()
        else:raise ValidationError(f'{title}: tek bir mevcut audio asset gerekli; işlem durdu.')
        target=f'audio/cases-20261013/{digest[:16]}-{name}'
        changes.append((asset,target,raw,digest))
    report=[{'id':a.pk,'title':a.title,'previous':a.file.name,'file':target,'sha256':digest,'changed':a.file.name!=target} for a,target,raw,digest in changes]
    if not apply:return report
    # Uploads are retained if a database commit fails; no old audio is deleted.
    for asset,target,raw,digest in changes:
        if not storage.exists(target):
            saved=storage.save(target,ContentFile(raw))
            if saved!=target:raise ValidationError('Ses hedefi çakıştı; işlem durdu.')
        with storage.open(target,'rb') as f:
            if hashlib.sha256(f.read()).hexdigest()!=digest:raise ValidationError('Kalıcı ses doğrulanamadı.')
    for row,(asset,target,raw,digest) in zip(report,changes):
        if not asset.pk:asset.save();row['id']=asset.pk
    batch=hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest()
    audit=f'audio/cases-20261013/rollback-{batch}.json'
    if not storage.exists(audit):storage.save(audit,ContentFile(json.dumps(report,ensure_ascii=False).encode()))
    for asset,target,raw,digest in changes:
        if asset.file.name!=target:asset.file=target;asset.save(update_fields=['file'])
    return report

@transaction.atomic
def restore_batch(name):
    import re
    if not re.fullmatch(r'rollback-[a-f0-9]{64}\.json',name):raise ValidationError('Geri alma manifesti geçersiz.')
    storage=PrivateVoiceStorage()
    with storage.open('audio/cases-20261013/'+name,'rb') as f:rows=json.load(f)
    for row in rows:
        asset=AudioAsset.objects.select_for_update().get(pk=row['id'])
        if asset.file.name!=row['file']:raise ValidationError('Ses daha sonra değiştirilmiş; geri alma durdu.')
    for row in rows:
        AudioAsset.objects.filter(pk=row['id']).update(file=row['previous'])
    return len(rows)
