"""Scoped live media upload. Run only in the authorized Django service shell."""
import hashlib,json,tempfile
from pathlib import Path
from urllib.request import urlopen
from django.core.files.base import ContentFile
from mobile_api.models import LearningPath,Question
from mobile_api.storage import PrivateVoiceStorage

COMMIT='0e5b7d943b11c120f136381dd14cc5a8f5c0d396'
BASE=f'https://raw.githubusercontent.com/volkancyberframework-ux/itauditlab/{COMMIT}/'
p=LearningPath.objects.get(pk=26)
assert p.owner_id is None and 'İşe Alındın! İlk 30 Günün' in p.title
assert p.preferences.get('first30_v2',{}).get('enabled')
manifest_raw=urlopen(BASE+'content/learning-paths/first-30-days/recorded-20261012/manifest.json',timeout=30).read()
manifest=json.loads(manifest_raw)
assert [r['chapter'] for r in manifest]==list(range(1,11))
storage=PrivateVoiceStorage()
for row in manifest:
    name='first30-recorded-20261012/'+row['filename']
    if storage.exists(name):
        with storage.open(name,'rb') as f:raw=f.read()
        assert hashlib.sha256(raw).hexdigest()==row['sha256'],'Existing file differs; no overwrite'
    else:
        raw=urlopen(BASE+'mobile_api/demo_assets/first30_recorded_20261012/'+row['filename'],timeout=30).read()
        assert hashlib.sha256(raw).hexdigest()==row['sha256'],'Download checksum mismatch'
        saved=storage.save(name,ContentFile(raw))
        assert saved==name,'Storage generated another filename; stopped safely'
    print('MEDIA OK',row['filename'],len(raw),flush=True)
helper=urlopen(BASE+'mobile_api/first30_recordings.py',timeout=30).read()
assert hashlib.sha256(helper).hexdigest()=='3f5cc28cd86d3d6b4dbb07485034d60655148e5a6735a3a143fcf0a188e4b1d3'
with tempfile.TemporaryDirectory(prefix='first30-recordings-') as temp:
    Path(temp,'manifest.json').write_bytes(manifest_raw)
    namespace=dict(__package__='mobile_api',__file__=str(Path.cwd()/'mobile_api/first30_recordings.py'))
    exec(compile(helper,'first30_recordings.py','exec'),namespace)
    namespace['ROOT']=Path(temp)
    print('DRY RUN',namespace['replace_recordings'](),flush=True)
    print('APPLIED',namespace['replace_recordings'](dry_run=False),flush=True)
# Verify the exact production FileResponse bytes, not only DB relationships.
from mobile_api.views import private_file
p.refresh_from_db();reg=p.preferences['first30_recorded_20261012']
for row in manifest:
    q=p.questions.get(pk=p.preferences['first30_v1']['questions'][f"grc-first30-q-{(row['chapter']-1)*10+1:03}"])
    assert q.audio_id==reg['audio_ids'][str(row['chapter'])]
    response=private_file(q.audio.file,'audio/mpeg')
    assert response.status_code==200
    digest=hashlib.sha256()
    for chunk in response.streaming_content:digest.update(chunk)
    response.close()
    assert digest.hexdigest()==row['sha256']
print('LIVE VERIFIED: 10 user recordings, 1.2x, production FileResponse checksums match.',flush=True)
