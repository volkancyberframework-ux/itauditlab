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
from .models import MobilePayment

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
            create.return_value.url='https://checkout.stripe.com/test'
            response=self.client.post('/mobiluygulama/checkout',{'token':token_for(self.user),'amount':'1','user_id':'999'})
            self.assertEqual(response.status_code,303)
            kwargs=create.call_args.kwargs
            self.assertNotIn('payment_method_types',kwargs)
            self.assertEqual(kwargs['client_reference_id'],str(self.user.pk));self.assertEqual(kwargs['line_items'][0]['price_data']['unit_amount'],209900)
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

    def test_direct_website_mobile_login(self):
        response=self.client.post('/mobiluygulama',{'email':'BUYER@example.com','password':'Strong-Sample-834'})
        self.assertEqual(response.status_code,302)
        self.assertContains(self.client.get(response.url),'buyer@example.com')
