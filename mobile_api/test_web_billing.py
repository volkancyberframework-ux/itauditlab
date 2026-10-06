import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone as utc
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.core.cache import cache
from django.utils import timezone
from .web_billing import token_for, add_month, PRODUCT
from .models import MobilePayment, MobileCheckoutRequest

@override_settings(STRIPE_SECRET_KEY='sk_test_fixture', MOBILE_STRIPE_WEBHOOK_SECRET='whsec_fixture')
class WebPaymentTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username='buyer',email='buyer@example.com',password='Strong-Sample-834',is_mobile=True)
        self.event = {'id':'evt_one','type':'checkout.session.completed','created':int(time.time()),'livemode':False,'data':{'object':{'id':'cs_test_one','payment_intent':'pi_one','mode':'payment','payment_status':'paid','amount_total':209900,'currency':'try','client_reference_id':str(self.user.pk),'metadata':{'product':PRODUCT,'mobile_user_id':str(self.user.pk)}}}}

    def send(self,event=None,signed=True):
        body=json.dumps(event or self.event).encode(); stamp=str(int(time.time()))
        signature=hmac.new(b'whsec_fixture',stamp.encode()+b'.'+body,hashlib.sha256).hexdigest()
        return self.client.post('/mobiluygulama/webhook',body,content_type='application/json',HTTP_STRIPE_SIGNATURE=f't={stamp},v1={signature}' if signed else 'invalid')

    def test_signed_payment_grants_month_and_duplicate_does_not_extend(self):
        self.assertEqual(self.send().status_code,200)
        self.user.refresh_from_db(); until=self.user.mobile_paid_until
        self.assertTrue(self.user.mobile_paid);self.assertFalse(self.user.mobile_free)
        self.assertEqual(until,add_month(timezone.localtime(datetime.fromtimestamp(self.event['created'],tz=utc.utc))))
        self.event['id']='evt_duplicate';self.assertEqual(self.send().status_code,200)
        self.user.refresh_from_db();self.assertEqual(self.user.mobile_paid_until,until);self.assertEqual(MobilePayment.objects.count(),1)

    def test_renewal_extends_current_end(self):
        self.send();self.user.refresh_from_db();until=self.user.mobile_paid_until
        obj=self.event['data']['object'];obj['id']='cs_test_two';obj['payment_intent']='pi_two';self.event['id']='evt_two'
        self.send();self.user.refresh_from_db();self.assertEqual(self.user.mobile_paid_until,add_month(until))

    def test_unsigned_wrong_price_currency_mode_account_and_unpaid(self):
        self.assertEqual(self.send(signed=False).status_code,400)
        obj=self.event['data']['object']
        for key,value in [('amount_total',1),('currency','usd'),('mode','subscription'),('client_reference_id','999')]:
            original=obj[key];obj[key]=value;self.assertEqual(self.send().status_code,400);obj[key]=original
        self.event['livemode']=True;self.assertEqual(self.send().status_code,400);self.event['livemode']=False
        obj['payment_status']='unpaid';self.assertEqual(self.send().status_code,200)
        self.assertFalse(MobilePayment.objects.exists())

    def test_success_url_never_grants_access(self):
        response=self.client.get('/mobiluygulama/success?session_id=cs_test_one')
        self.assertContains(response,'doğrulaması bekleniyor');self.assertFalse(MobilePayment.objects.exists())

    def test_checkout_is_bound_to_signed_mobile_account(self):
        with patch('mobile_api.web_billing.stripe.checkout.Session.create') as create:
            create.return_value.url='https://checkout.stripe.com/test'; create.return_value.id='cs_test_checkout'
            response=self.client.post('/mobiluygulama/checkout',{'token':token_for(self.user),'amount':'1','user_id':'999'})
            self.assertEqual(response.status_code,303)
            kwargs=create.call_args.kwargs
            self.assertNotIn('payment_method_types',kwargs)
            self.assertEqual(MobileCheckoutRequest.objects.get(pk=kwargs['client_reference_id']).user,self.user);self.assertEqual(kwargs['line_items'][0]['price_data']['unit_amount'],209900)
        self.assertEqual(self.client.post('/mobiluygulama/checkout',{'token':'tampered'}).status_code,400)

    def test_token_invalid_after_password_change_and_for_web_account(self):
        token=token_for(self.user);self.user.set_password('Different-Strong-873');self.user.save()
        self.assertEqual(self.client.post('/mobiluygulama/checkout',{'token':token}).status_code,400)
        self.user.is_mobile=False;self.user.save()
        self.assertEqual(self.client.post('/mobiluygulama/checkout',{'token':token_for(self.user)}).status_code,400)

    def test_expired_paid_account_keeps_free_login(self):
        from .access import check_mobile_access
        self.user.mobile_paid_until=timezone.now()-timedelta(seconds=1);self.user.save()
        check_mobile_access(self.user)
        self.assertTrue(self.user.mobile_free);self.assertFalse(self.user.mobile_paid)

    def test_month_end_and_leap_year(self):
        self.assertEqual(add_month(datetime(2028,1,31,tzinfo=utc.utc)).day,29)
        self.assertEqual(add_month(datetime(2027,1,31,tzinfo=utc.utc)).day,28)

    def test_page_only_asks_email(self):
        response = self.client.get('/mobiluygulama')
        self.assertContains(response, 'name="email"')
        self.assertNotContains(response, 'type="password"')
        self.assertContains(response, 'volkan@grcustasi.com')

    def checkout_event(self, email):
        with patch('mobile_api.web_billing.stripe.checkout.Session.create') as create:
            create.return_value.url = 'https://checkout.stripe.com/test'
            create.return_value.id = 'cs_test_email'
            response = self.client.post('/mobiluygulama/checkout', {'email':email})
            self.assertEqual(response.status_code,303)
            pending = MobileCheckoutRequest.objects.get(pk=create.call_args.kwargs['client_reference_id'])
        event = json.loads(json.dumps(self.event))
        obj = event['data']['object']
        obj['id'] = pending.checkout_session_id
        obj['client_reference_id'] = str(pending.pk)
        obj['metadata'] = {'product': PRODUCT, 'mobile_checkout_id': str(pending.pk)}
        return event

    def test_existing_website_password_is_preserved_and_receipt_sent_once(self):
        from django.core import mail
        self.user.is_mobile=False; self.user.save()
        password_hash=self.user.password
        event=self.checkout_event('BUYER@example.com')
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.send(event).status_code,200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.mobile_paid); self.assertTrue(self.user.is_mobile)
        self.assertEqual(self.user.password,password_hash)
        self.assertFalse(self.user.mobile_must_change_password)
        self.assertEqual(len(mail.outbox),1)
        self.assertIn('mevcut şifresi geçerlidir',mail.outbox[0].body)
        with self.captureOnCommitCallbacks(execute=True): self.send(event)
        self.assertEqual(len(mail.outbox),1)

    def test_new_account_created_only_after_payment_and_forced_to_change_password(self):
        from django.core import mail
        from rest_framework.test import APIClient
        User=get_user_model()
        event=self.checkout_event('new@example.com')
        self.assertFalse(User.objects.filter(email='new@example.com').exists())
        with self.captureOnCommitCallbacks(execute=True): self.send(event)
        user=User.objects.get(email='new@example.com')
        self.assertTrue(user.mobile_paid); self.assertTrue(user.mobile_must_change_password)
        self.assertFalse(user.is_staff); self.assertFalse(user.is_superuser)
        password=mail.outbox[0].body.split('İlk giriş şifreniz: ')[1].split('\n')[0]
        self.assertTrue(user.check_password(password))
        client=APIClient(); login=client.post('/api/mobile/v1/auth/login/',{'email':user.email,'password':password},format='json')
        self.assertEqual(login.status_code,403)
        self.assertFalse(user.mobile_email_verified)
        from .email_verification import verification_url
        from urllib.parse import urlparse
        self.assertIn(verification_url(user).split('/auth/verify-email/')[0], mail.outbox[0].body)
        self.assertEqual(self.client.post(urlparse(verification_url(user)).path).status_code,200)
        login=client.post('/api/mobile/v1/auth/login/',{'email':user.email,'password':password},format='json')
        self.assertEqual(login.status_code,200)
        client.credentials(HTTP_AUTHORIZATION='Bearer '+login.data['access'])
        self.assertTrue(client.get('/api/mobile/v1/profile/').data['must_change_password'])
        self.assertEqual(client.get('/api/mobile/v1/paths/').status_code,403)
        response=client.post('/api/mobile/v1/auth/change-password/',{'new_password':'My-New-Secure-7189','confirm_password':'My-New-Secure-7189'},format='json')
        self.assertEqual(response.status_code,200)
        user.refresh_from_db(); self.assertFalse(user.mobile_must_change_password)
        self.assertTrue(user.check_password('My-New-Secure-7189'))
        client.credentials(HTTP_AUTHORIZATION='Bearer '+response.data['access'])
        self.assertEqual(client.get('/api/mobile/v1/paths/').status_code,200)
        with self.captureOnCommitCallbacks(execute=True): self.send(event)
        user.refresh_from_db(); self.assertTrue(user.check_password('My-New-Secure-7189'))
        self.assertEqual(len(mail.outbox),1)

    def test_mail_failure_keeps_paid_access_and_can_retry(self):
        from .payment_mail import send_payment_receipt
        event=self.checkout_event('pending@example.com')
        with patch('mobile_api.payment_mail.send_mail',side_effect=RuntimeError('SMTP')):
            with self.captureOnCommitCallbacks(execute=True): self.send(event)
        payment=MobilePayment.objects.get(); user=payment.user
        self.assertTrue(user.mobile_paid); self.assertFalse(user.has_usable_password())
        self.assertIsNone(payment.receipt_sent_at)
        self.assertTrue(payment.receipt_error)
        self.assertTrue(send_payment_receipt(payment.pk))
        user.refresh_from_db(); self.assertTrue(user.has_usable_password())

    def test_csrf_is_required_and_fresh_token_handles_both_origins(self):
        from django.test import Client
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/mobiluygulama/checkout',{'email':'buyer@example.com'}).status_code,403)
        for origin in ['https://grcustasi.com','https://www.grcustasi.com']:
            token=client.get('/mobiluygulama/csrf').json()['token']
            with patch('mobile_api.web_billing.stripe.checkout.Session.create') as create:
                create.return_value.id='cs_'+origin.split('//')[1]
                create.return_value.url='https://checkout.stripe.com/test'
                self.assertEqual(client.post('/mobiluygulama/checkout',{'email':'buyer@example.com','csrfmiddlewaretoken':token},secure=True,HTTP_ORIGIN=origin).status_code,303)

    def test_https_checkout_without_origin_uses_origin_only_referer(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        page = client.get('/mobiluygulama', secure=True)
        self.assertEqual(page['Referrer-Policy'], 'strict-origin')
        self.assertContains(page, 'name="referrer" content="strict-origin"')
        token = client.get('/mobiluygulama/csrf', secure=True).json()['token']
        data = {'email': 'buyer@example.com', 'csrfmiddlewaretoken': token}
        # A valid token alone must not bypass the HTTPS source check.
        self.assertEqual(client.post('/mobiluygulama/checkout', data, secure=True).status_code, 403)
        self.assertEqual(client.post('/mobiluygulama/checkout', data, secure=True,
                                     HTTP_REFERER='https://untrusted.example/').status_code, 403)
        with patch('mobile_api.web_billing.stripe.checkout.Session.create') as create:
            create.return_value.id = 'cs_referer'
            create.return_value.url = 'https://checkout.stripe.com/test'
            response = client.post('/mobiluygulama/checkout', data, secure=True,
                                   HTTP_REFERER='https://testserver/')
            self.assertEqual(response.status_code, 303)
            self.assertEqual(response['Referrer-Policy'], 'no-referrer')

    def test_renewal_preserves_usable_initial_password(self):
        from django.core import mail
        self.user.mobile_must_change_password=True; self.user.save()
        password_hash=self.user.password
        with self.captureOnCommitCallbacks(execute=True): self.send()
        self.user.refresh_from_db()
        self.assertEqual(self.user.password,password_hash)
        self.assertTrue(self.user.mobile_must_change_password)
        self.assertIn('mevcut şifresi geçerlidir',mail.outbox[0].body)
