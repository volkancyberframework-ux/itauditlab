import hashlib,hmac,json,time
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase,override_settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient
from .linux_auditor import seed,assign_paid,package
from .models import LearningPath,UserPathProgress,QuestionAttempt,XPTransaction,BootcampMobileGrant
from .bootcamp_membership import prepare,fulfil

@patch('mobile_api.views.MobileThrottle.allow_request',return_value=True)
class LinuxTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.path=LearningPath.objects.get(pk=seed(dry_run=False)['path_id'])
        self.user=get_user_model().objects.create_user(username='linux-paid',email='paid@example.test',is_mobile=True,mobile_full_access=True,mobile_email_verified=True)
        self.client=APIClient();self.client.force_authenticate(self.user)

    def test_complete_all_80_images_and_answers_without_duplicate_rewards(self,_throttle):
        first=None
        for chapter in range(1,6):
            r=self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json')
            self.assertEqual(r.status_code,201,r.data);state=r.data
            self.assertEqual(state['total'],16)
            resumed=self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json')
            self.assertEqual(resumed.data['id'],state['id'])
            for index in range(16):
                q=state['question'];model=self.path.questions.get(pk=q['id']);self.assertEqual(model.module.order,chapter)
                image=self.client.get(f'/api/mobile/v1/questions/{q["id"]}/image/')
                self.assertEqual(image.status_code,200)
                self.assertEqual(hashlib.sha256(b''.join(image.streaming_content)).hexdigest(),package()[1][model.order-1]['sha256'])
                payload={'question_id':model.pk,'answer':model.answer}
                result=self.client.post(f'/api/mobile/v1/sessions/{state["id"]}/answer/',payload,format='json')
                self.assertEqual(result.status_code,200,result.data);self.assertTrue(result.data['correct'])
                if first is None:first=(state['id'],payload)
                state=result.data['session']
            self.assertTrue(state['complete'])
        retry=self.client.post(f'/api/mobile/v1/sessions/{first[0]}/answer/',first[1],format='json')
        self.assertEqual(retry.status_code,200)
        self.assertEqual(QuestionAttempt.objects.filter(session__user=self.user).count(),80)
        self.assertEqual(XPTransaction.objects.filter(user=self.user).count(),80)
        self.assertEqual(UserPathProgress.objects.get(user=self.user,path=self.path).completed.count(),80)
        self.assertEqual(seed(dry_run=False)['create'],0)

    def test_paid_assignment_and_free_exclusion(self,_throttle):
        free=get_user_model().objects.create_user(username='linux-free',is_mobile=True,mobile_email_verified=True)
        self.assertEqual(assign_paid(self.path),1);self.assertEqual(assign_paid(self.path),0)
        self.client.force_authenticate(free)
        listing=self.client.get('/api/mobile/v1/paths/')
        self.assertNotIn(self.path.pk,[p['id'] for p in listing.data])
        self.assertEqual(self.client.post('/api/mobile/v1/sessions/',{'path_id':self.path.pk},format='json').status_code,403)
        self.assertEqual(self.client.get(f'/api/mobile/v1/questions/{self.path.questions.first().pk}/image/').status_code,404)
        self.assertFalse(UserPathProgress.objects.filter(user=free,path=self.path).exists())

    @override_settings(ROOT_URLCONF='mobile_web.urls')
    def test_web_session_and_image(self,_throttle):
        r=self.client.post('/web-api/sessions/',{'path_id':self.path.pk},format='json')
        self.assertEqual(r.status_code,201,r.data)
        self.assertEqual(self.client.get(r.data['question']['image']).status_code,200)

class BootcampMembershipTests(TestCase):
    def session(self,**changes):
        self.grant=prepare('cisa',8999900,'try');self.grant.checkout_session_id='cs_bootcamp';self.grant.save()
        data={'id':'cs_bootcamp','payment_intent':'pi_bootcamp','mode':'payment','payment_status':'paid','currency':'try','amount_subtotal':8999900,'amount_total':7999900,'metadata':{'product':'cisa','bootcamp_checkout_id':str(self.grant.pk)},'customer_details':{'email':'BOOT@example.test'}}
        data.update(changes);return data
    def test_paid_grant_is_lifetime_idempotent_and_preserves_identity(self):
        user=get_user_model().objects.create_user(username='boot',email='boot@example.test',password='original-long-password',mobile_last_date=timezone.localdate()-timedelta(days=1),mobile_email_verified=True)
        original=user.password;s=self.session();fulfil(s);fulfil(s);user.refresh_from_db()
        self.assertTrue(user.mobile_paid);self.assertIsNone(user.mobile_last_date)
        self.assertEqual(user.password,original);self.assertTrue(user.mobile_email_verified)
        self.assertEqual(BootcampMobileGrant.objects.filter(fulfilled_at__isnull=False).count(),1)
    def test_tampered_unpaid_or_ambiguous_payment_cannot_grant(self):
        s=self.session(payment_status='unpaid')
        with self.assertRaises(ValidationError):fulfil(s)
        s['payment_status']='paid';s['amount_subtotal']=1
        with self.assertRaises(ValidationError):fulfil(s)
        self.assertFalse(get_user_model().objects.filter(email='boot@example.test').exists())
    @override_settings(MOBILE_STRIPE_WEBHOOK_SECRET='whsec_linux_test',STRIPE_SECRET_KEY='sk_test_placeholder')
    def test_real_signed_webhook_dispatches_bootcamp_and_rejects_invalid_signature(self):
        s=self.session();event={'id':'evt_boot','type':'checkout.session.completed','livemode':False,'data':{'object':s}}
        body=json.dumps(event);stamp=int(time.time());digest=hmac.new(b'whsec_linux_test',f'{stamp}.{body}'.encode(),hashlib.sha256).hexdigest()
        response=self.client.post('/mobiluygulama/webhook',body,content_type='application/json',HTTP_STRIPE_SIGNATURE=f't={stamp},v1={digest}')
        self.assertEqual(response.status_code,200,response.content)
        self.assertTrue(get_user_model().objects.get(email='boot@example.test').mobile_full_access)
        self.assertEqual(self.client.post('/mobiluygulama/webhook',body,content_type='application/json',HTTP_STRIPE_SIGNATURE='invalid').status_code,400)

class BootcampReceiptTests(TestCase):
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_new_account_receipt_sets_initial_password_once_and_keeps_verification(self):
        from django.core import mail
        from .bootcamp_membership import send_receipt
        user=get_user_model().objects.create_user(username='new-boot',email='new@example.test',is_mobile=True,mobile_full_access=True,mobile_email_verified=False)
        user.set_unusable_password();user.save()
        grant=prepare('cism',8999900,'try');grant.user=user;grant.fulfilled_at=timezone.now();grant.save()
        self.assertTrue(send_receipt(grant.pk));user.refresh_from_db()
        password_hash=user.password
        self.assertTrue(user.has_usable_password());self.assertTrue(user.mobile_must_change_password)
        self.assertFalse(user.mobile_email_verified)
        self.assertIn('ömür boyu',mail.outbox[-1].body)
        self.assertIn('E-postanızı',mail.outbox[-1].body.replace('e-postanızı','E-postanızı'))
        self.assertTrue(send_receipt(grant.pk));user.refresh_from_db()
        self.assertEqual(user.password,password_hash);self.assertEqual(len(mail.outbox),1)
