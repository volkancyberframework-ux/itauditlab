from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from .models import LearningPath,Question,AudioAsset,LearningSession,QuestionAttempt,UserPathProgress
from .first30_content import import_package
from .first30_revision import apply_revision
from .first30_recordings import replace_recordings,restore_generated_recordings
class First30RecordingsTests(TestCase):
    def setUp(self):
        cache.clear();self.path=LearningPath.objects.create(pk=26,title='🪪 İşe Alındın! İlk 30 Günün')
        import_package(dry_run=False);apply_revision(dry_run=False)
        self.user=get_user_model().objects.create_user(username='recordings',is_mobile=True,mobile_full_access=True)
        self.client=APIClient();self.client.force_authenticate(self.user)
    def test_replace_is_scoped_idempotent_and_preserves_progress(self):
        q=self.path.questions.first();session=LearningSession.objects.create(path=self.path,user=self.user,questions=[q.pk]);attempt=QuestionAttempt.objects.create(question=q,session=session,answer=q.answer,is_correct=True,xp_change=10)
        progress=UserPathProgress.objects.create(user=self.user,path=self.path);progress.completed.add(q)
        before=list(self.path.questions.values('pk','kind','answer','order','prompt'));old_ids=list(self.path.questions.filter(kind='audio').values_list('audio_id',flat=True));before_count=AudioAsset.objects.count()
        self.assertTrue(replace_recordings()['dry_run']);self.assertEqual(AudioAsset.objects.count(),before_count)
        replace_recordings(dry_run=False);self.assertEqual(self.path.questions.filter(kind='audio',audio__name_key__startswith='first30_recorded_').count(),10)
        self.assertEqual(before,list(self.path.questions.values('pk','kind','answer','order','prompt')))
        self.assertEqual(progress.completed.count(),1);attempt.refresh_from_db();self.assertEqual(attempt.xp_change,10)
        self.assertTrue(replace_recordings(dry_run=False)['already_applied']);self.assertEqual(AudioAsset.objects.count(),before_count+10)
        restore_generated_recordings();self.assertEqual(list(self.path.questions.filter(kind='audio').values_list('audio_id',flat=True)),old_ids)
        replace_recordings(dry_run=False);self.assertEqual(AudioAsset.objects.count(),before_count+10)
    def test_all_recordings_available_through_private_audio_api(self):
        replace_recordings(dry_run=False)
        for q in self.path.questions.filter(kind='audio'):
            r=self.client.get(f'/api/mobile/v1/audio/{q.audio_id}/');self.assertEqual(r.status_code,200);self.assertEqual(r['Content-Type'],'audio/mpeg')
            payload=b''.join(r.streaming_content);self.assertTrue(payload.startswith(b'ID3'));self.assertGreater(len(payload),10000);r.close()
