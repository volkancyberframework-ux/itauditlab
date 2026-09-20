import io,unittest
from unittest.mock import patch,MagicMock
from .console_gateway import ConsoleGateway,console_route

class GatewayTests(unittest.TestCase):
    def env(self,path='/',host='www.grcustasi.com',**extra):return {'PATH_INFO':path,'HTTP_HOST':host,'REQUEST_METHOD':'GET','wsgi.input':io.BytesIO(b''),**extra}
    def test_existing_domains_and_paths_stay_on_original_site(self):
        for host in ['grcustasi.com','www.grcustasi.com','itauditlab.onrender.com','siberkobi.co']:
            for path in ['/','/bulamazsinki/','/static/test.css','/api/skool/telegram/']:
                self.assertIsNone(console_route(self.env(path,host)))
    def test_prefix_and_registered_subdomain_shape(self):
        self.assertEqual(console_route(self.env('/denetim/signin/')),('/signin/','/denetim'))
        self.assertEqual(console_route(self.env('/console/','firma.grcustasi.com')),('/console/',''))
        self.assertIsNone(console_route(self.env('/denetim-other/')))
    def test_original_app_is_passed_original_environ(self):
        original=MagicMock(return_value=[b'original']);env=self.env();start=MagicMock()
        self.assertEqual(ConsoleGateway(original)(env,start),[b'original']);original.assert_called_once_with(env,start)
    @patch('itaudit.console_gateway.UnixConnection')
    def test_proxy_overwrites_prefix_and_preserves_cookies_and_query(self,connection):
        upstream=connection.return_value;response=upstream.getresponse.return_value
        response.status=200;response.reason='OK';response.read.return_value=b'console';response.getheaders.return_value=[('Set-Cookie','municipal_sessionid=abc'),('Set-Cookie','municipal_csrftoken=xyz')]
        env=self.env('/denetim/signin/',HTTP_X_CONSOLE_PREFIX='/evil',HTTP_COOKIE='sessionid=legacy; municipal_sessionid=console',QUERY_STRING='next=%2Fdenetim%2Fconsole%2F')
        start=MagicMock();self.assertEqual(ConsoleGateway(MagicMock())(env,start),[b'console'])
        args=upstream.request.call_args
        self.assertEqual(args.args[1],'/signin/?next=%2Fdenetim%2Fconsole%2F')
        self.assertEqual(args.kwargs['headers']['X-Console-Prefix'],'/denetim')
        self.assertEqual(len(start.call_args.args[1]),2)
    @patch('itaudit.console_gateway.UnixConnection')
    def test_unavailable_console_does_not_block_original_site(self,connection):
        connection.return_value.request.side_effect=OSError('not started');original=MagicMock(return_value=[b'original']);gateway=ConsoleGateway(original);start=MagicMock()
        gateway(self.env('/denetim/'),start);self.assertEqual(start.call_args.args[0],'503 Service Unavailable')
        self.assertEqual(gateway(self.env('/'),start),[b'original'])
