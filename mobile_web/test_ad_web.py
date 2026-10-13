from collections import Counter
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from mobile_api.ad_auditor import package,seed,KEY
from mobile_api.models import LearningPath,Question,QuestionAttempt,XPTransaction,UserPathProgress
from mobile_api.cisa_simulator import answer_key

@override_settings(ROOT_URLCONF='mobile_web.urls')
class ADWebTests(TestCase):
 def setUp(self):
  from django.core.cache import cache
  cache.clear();seed(dry_run=False)
  self.path=LearningPath.objects.get(preferences__ad_auditor_v1__enabled=True)
  self.user=get_user_model().objects.create_user(username='ad-web-test',is_mobile=True,mobile_full_access=True)
  self.client=APIClient();self.client.force_authenticate(self.user)
 def start(self):
  r=self.client.post('/web-api/sessions/',{'path_id':self.path.pk},format='json');self.assertEqual(r.status_code,201,r.data);return r.data
 def test_distribution_seed_and_native_isolation(self):
  p=package()[0];self.assertEqual(len(p['questions']),75)
  self.assertEqual(Counter(q.module.order for q in self.path.questions.all()),{i:15 for i in range(1,6)})
  self.assertEqual(Counter(q.difficulty for q in self.path.questions.all()),dict(beginner=30,intermediate=35,advanced=10))
  self.assertFalse(self.path.published);self.assertEqual(seed(dry_run=False)['create'],0)
  self.assertFalse(any(p['id']==self.path.pk for p in self.client.get('/api/mobile/v1/paths/').data))
  data=self.client.get('/web-api/paths/').data;path=next(p for p in data if p['id']==self.path.pk);self.assertTrue(path['direct_start']);self.assertTrue(path['web_has_images'])
 def test_all_75_grading_progress_keys_summaries(self):
  orders=[]
  for chapter in range(1,6):
   state=self.start();self.assertEqual(state['total'],15)
   while state['question']:
    from django.core.cache import cache
    cache.clear()
    q=Question.objects.get(pk=state['question']['id']);self.assertEqual(q.module.order,chapter);orders.append(q.order)
    self.assertEqual(state['question']['audio'],[]);self.assertTrue(all(set(o)=={'id','text'} for o in state['question']['options']))
    image=self.client.get(f'/web-api/questions/{q.pk}/image/');self.assertEqual(image.status_code,200);self.assertTrue(b''.join(image.streaming_content).startswith(b'\x89PNG'))
    submitted=q.answer[0] if q.kind=='fill_blank' else q.answer
    r=self.client.post(f'/web-api/sessions/{state["id"]}/answer/',{'question_id':q.pk,'answer':submitted},format='json');self.assertEqual(r.status_code,200,r.data);self.assertTrue(r.data['correct'])
    for key in answer_key(q):self.assertIn(key,r.data['explanation'])
    self.assertNotIn('http',r.data['explanation']);self.assertNotIn('Kaynak:',r.data['explanation']);state=r.data['session']
   self.assertEqual(state['evaluation']['chapters'][-1]['correct'],15);self.assertEqual(state['evaluation']['complete'],chapter==5)
  self.assertEqual(orders,list(range(1,76)));self.assertEqual(UserPathProgress.objects.get(user=self.user,path=self.path).completed.count(),75)
  self.assertEqual(XPTransaction.objects.filter(user=self.user).count(),75)
 def test_wrong_answer_resume_replay_and_access(self):
  state=self.start();q=Question.objects.get(pk=state['question']['id']);wrong=next(o['id'] for o in q.options if o['id'] not in q.answer)
  url=f'/web-api/sessions/{state["id"]}/answer/';body={'question_id':q.pk,'answer':[wrong]}
  r=self.client.post(url,body,format='json');self.assertEqual(r.status_code,200,r.data);self.assertFalse(r.data['correct']);self.assertEqual(r.data['xp_change'],0)
  self.assertIn('Bu cevap neden uygun değil',r.data['explanation']);self.assertEqual(self.start()['question']['number'],2)
  self.client.post(url,body,format='json');self.assertEqual(QuestionAttempt.objects.filter(session__user=self.user).count(),1)
  other=get_user_model().objects.create_user(username='restricted',is_mobile=True);self.client.force_authenticate(other)
  self.assertEqual(self.client.post('/web-api/sessions/',{'path_id':self.path.pk},format='json').status_code,403)
  self.assertEqual(self.client.get(f'/web-api/questions/{q.pk}/image/').status_code,404)
 def test_image_auth_and_module_assets(self):
  q=self.path.questions.first();self.client.force_authenticate(None)
  self.assertEqual(self.client.get(f'/web-api/questions/{q.pk}/image/').status_code,401)
  for asset in ['bridge.js','web-learning.mjs','viewer-math.mjs','fullscreen-image-viewer.mjs','web-learning.css']:
   self.assertEqual(self.client.get('/web-features/'+asset).status_code,200)
  self.assertEqual(self.client.get('/web-features/../web_api.py').status_code,404)
 @override_settings(ALLOWED_HOSTS=['app.grcustasi.com','testserver'])
 def test_refresh_cookie_rotation_origin_and_bootstrap(self):
  self.assertEqual(self.client.get('/web-api/paths/',HTTP_X_GRC_WEB_BRIDGE='1').status_code,401)
  self.client.force_authenticate(None);token=str(RefreshToken.for_user(self.user))
  r=self.client.post('/web-api/auth/refresh/',{'refresh':token},format='json',HTTP_HOST='app.grcustasi.com');self.assertEqual(r.status_code,200,r.data)
  cookie=r.cookies['grc_web_refresh'];self.assertTrue(cookie['secure']);self.assertTrue(cookie['httponly']);self.assertEqual(cookie['path'],'/web-api/')
  r=self.client.post('/web-api/auth/refresh/',{},format='json',HTTP_HOST='app.grcustasi.com',HTTP_ORIGIN='https://evil.test');self.assertEqual(r.status_code,403)
  r=self.client.post('/web-api/auth/refresh/',{},format='json',HTTP_HOST='app.grcustasi.com',HTTP_ORIGIN='https://app.grcustasi.com');self.assertEqual(r.status_code,200,r.data)
  self.assertNotEqual(token,r.data['refresh'])

 def test_dryrun_and_changed_content_guard(self):
  from django.core.exceptions import ValidationError
  count=Question.objects.count();self.assertEqual(seed(dry_run=True)['create'],0);self.assertEqual(Question.objects.count(),count)
  q=self.path.questions.first();q.prompt='Edited locally';q.save(update_fields=['prompt'])
  with self.assertRaises(ValidationError):seed(dry_run=False)
  q.refresh_from_db();self.assertEqual(q.prompt,'Edited locally')
