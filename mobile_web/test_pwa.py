import json
from pathlib import Path
from django.test import TestCase,override_settings
from django.conf import settings
@override_settings(ROOT_URLCONF='mobile_web.urls',ALLOWED_HOSTS=['app.grcustasi.com','testserver'])
class PwaTests(TestCase):
 def test_install_script_injection_and_worker_scope(self):
  r=self.client.get('/',HTTP_HOST='app.grcustasi.com');html=b''.join(r.streaming_content);self.assertIn(b'/web-features/pwa.js',html)
  r=self.client.get('/grc-pwa-sw.js');self.assertEqual(r.status_code,200);self.assertEqual(r['Service-Worker-Allowed'],'/');self.assertEqual(r['Content-Type'],'text/javascript')
  source=b''.join(r.streaming_content);self.assertIn(b"r.headers.has('Authorization')",source);self.assertIn(b'(api|web-api|media)',source)
  self.assertEqual(self.client.get('/web-features/offline.html').status_code,200)
 def test_manifest_and_icons(self):
  from PIL import Image
  root=Path(settings.BASE_DIR)/'mobile/web';m=json.loads((root/'manifest.json').read_text());self.assertEqual(m['display'],'standalone');self.assertEqual(m['scope'],'/')
  for icon in m['icons']:
   with Image.open(root/icon['src']) as im:self.assertEqual(f'{im.width}x{im.height}',icon['sizes'])
