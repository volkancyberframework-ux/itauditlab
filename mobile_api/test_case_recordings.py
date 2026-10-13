import io,json,hashlib,zipfile,tempfile
from pathlib import Path
from django.test import TestCase,override_settings
from django.core.exceptions import ValidationError
from mobile_api.case_recordings import replace_package,restore_batch
from mobile_api.models import AudioAsset,Question
class CaseRecordingTests(TestCase):
 def package(self):
  b=io.BytesIO();files=[]
  with zipfile.ZipFile(b,'w') as z:
   for name in [f'ses{i}.mp3' for i in range(1,19)]+['tanıtım.mp3']:
    raw=b'ID3'+name.encode()*1000;z.writestr(name,raw);files.append({'output':name,'output_sha256':hashlib.sha256(raw).hexdigest(),'output_seconds':10,'source_seconds':12})
   z.writestr('manifest.json',json.dumps({'speed':1.2,'files':files}))
  b.seek(0);return b
 def setUp(self):
  self.baseline=AudioAsset.objects.count()
  for i in range(1,19):AudioAsset.objects.create(title=f'ses{i}',name_key=f'ses{i}')
 def test_atomic_upload_same_ids_idempotence_and_rollback(self):
  with tempfile.TemporaryDirectory() as root,override_settings(MOBILE_VOICE_ROOT=root):
   a=AudioAsset.objects.get(title='ses1');q=Question.objects.create(kind='audio',prompt='preserved',audio=a)
   rows=replace_package(self.package());self.assertEqual(len(rows),19);self.assertEqual(AudioAsset.objects.count(),self.baseline+18)
   rows=replace_package(self.package(),apply=True);self.assertTrue(all(r['changed'] for r in rows));self.assertEqual(AudioAsset.objects.count(),self.baseline+19)
   q.refresh_from_db();self.assertEqual(q.audio_id,a.pk);a.refresh_from_db();self.assertTrue(a.file.name.endswith('ses1.mp3'))
   second=replace_package(self.package(),apply=True);self.assertFalse(any(r['changed'] for r in second))
   audit=next(p for p in Path(root).rglob('rollback-*.json') if json.loads(p.read_text())[0]['previous']=='');self.assertEqual(restore_batch(audit.name),19)
   a.refresh_from_db();self.assertEqual(a.file.name,'');self.assertTrue(list(Path(root).rglob('*.mp3')))
 def test_missing_asset_does_not_partially_update(self):
  AudioAsset.objects.filter(title='ses18').delete()
  with self.assertRaises(ValidationError):replace_package(self.package(),apply=True)
  self.assertEqual(AudioAsset.objects.count(),self.baseline+17);self.assertFalse(AudioAsset.objects.filter(title__startswith='ses').exclude(file='').exists())
 def test_admin_requires_permission(self):
  from django.contrib.auth import get_user_model
  u=get_user_model().objects.create_user(username='no-audio-access',is_staff=True)
  self.client.force_login(u);r=self.client.get('/bulamazsinki/mobile_api/audioasset/bulk-recordings/');self.assertEqual(r.status_code,403)
