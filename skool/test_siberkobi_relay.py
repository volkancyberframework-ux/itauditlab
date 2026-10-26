import json
from unittest.mock import patch,Mock
from django.test import SimpleTestCase,RequestFactory,override_settings
from .siberkobi_relay import forward,DESTINATION

@override_settings(GRCUSTASI_TELEGRAM_WEBHOOK_SECRET='synthetic-secret',GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID='123',GRCUSTASI_TELEGRAM_BOT_TOKEN='synthetic-token')
class RelayTests(SimpleTestCase):
    def call(self,text='siberkobi help',actor=123,secret='synthetic-secret',callback=False):
        message={'chat':{'id':actor,'type':'private'},'from':{'id':actor},'text':text}
        payload={'update_id':1,'message':message}
        if callback:payload={'update_id':2,'callback_query':{'data':'sk:test:confirm','from':{'id':actor},'message':message}}
        request=RequestFactory().post('/',json.dumps(payload),content_type='application/json',HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=secret)
        return forward(request,payload)
    @patch('skool.siberkobi_relay.requests.post')
    def test_signed_private_owner_and_callback(self,post):
        post.return_value=Mock(status_code=200)
        self.assertEqual(self.call().status_code,200)
        self.assertEqual(post.call_args.args[0],DESTINATION)
        self.assertIn('X-Siberkobi-Relay-Signature',post.call_args.kwargs['headers'])
        self.assertEqual(self.call(callback=True).status_code,200)
    @patch('skool.siberkobi_relay.requests.post')
    def test_rejects_secret_and_nonowner_preserves_grc(self,post):
        self.assertEqual(self.call(secret='bad').status_code,403)
        self.assertEqual(self.call(actor=999).status_code,200)
        self.assertIsNone(self.call(text='grcustasi list'))
        self.assertIsNone(self.call(text='/create Person'))
        post.assert_not_called()
    @patch('skool.siberkobi_relay.requests.post')
    def test_retry_on_downstream_failure(self,post):
        post.return_value=Mock(status_code=503)
        self.assertEqual(self.call().status_code,503)
