"""Route only the console prefix/tenant hosts; leave the existing site untouched."""
import http.client,os,socket
from urllib.parse import quote

SOCKET_PATH=os.getenv('CONSOLE_SOCKET','/tmp/itaudit-console.sock')
BASE_DOMAIN=os.getenv('TENANT_BASE_DOMAIN','grcustasi.com').lower()
RESERVED={'www','admin','api','mail','core','akademi','itauditlab'}
HOP={'connection','keep-alive','proxy-authenticate','proxy-authorization','te','trailer','transfer-encoding','upgrade'}

class UnixConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(SOCKET_PATH)

def console_route(environ):
    path=environ.get('PATH_INFO','/')
    host=environ.get('HTTP_HOST','').split(':')[0].lower()
    suffix='.'+BASE_DOMAIN
    tenant=host.endswith(suffix) and host[:-len(suffix)] not in RESERVED
    if path=='/denetim' or path.startswith('/denetim/'):
        return path[len('/denetim'):] or '/', '/denetim'
    return (path,'') if tenant else None

class ConsoleGateway:
    def __init__(self,application):self.application=application
    def __call__(self,environ,start_response):
        route=console_route(environ)
        if route is None:return self.application(environ,start_response)
        path,prefix=route
        if environ.get('PATH_INFO')=='/denetim':
            start_response('302 Found',[('Location','/denetim/'),('Content-Length','0')]);return [b'']
        try:length=int(environ.get('CONTENT_LENGTH') or 0)
        except ValueError:length=-1
        if length<0 or length>5*1024*1024:
            start_response('413 Payload Too Large',[('Content-Type','text/plain')]);return [b'Upload limit exceeded']
        headers={}
        for key,value in environ.items():
            if key.startswith('HTTP_'):
                name=key[5:].replace('_','-')
                if name.lower() not in HOP and name.lower() not in ('x-console-prefix','x-forwarded-host','x-forwarded-for'):
                    headers[name]=value
        headers['X-Console-Prefix']=prefix
        headers['X-Forwarded-For']=environ.get('REMOTE_ADDR','')
        if environ.get('CONTENT_TYPE'):headers['Content-Type']=environ['CONTENT_TYPE']
        headers['Content-Length']=str(length)
        url=quote(path,safe='/~:@!$&\'()*+,;=-._')
        if environ.get('QUERY_STRING'):url+='?'+environ['QUERY_STRING']
        conn=UnixConnection('localhost',timeout=45)
        try:
            conn.request(environ.get('REQUEST_METHOD','GET'),url,body=environ['wsgi.input'].read(length) if length else None,headers=headers)
            response=conn.getresponse()
            content=response.read()
            out=[(key,value) for key,value in response.getheaders() if key.lower() not in HOP]
            start_response(f'{response.status} {response.reason}',out)
            return [content]
        except (OSError,http.client.HTTPException):
            start_response('503 Service Unavailable',[('Content-Type','text/plain; charset=utf-8'),('Retry-After','10')])
            return ['Denetim konsolu hazırlanıyor. Lütfen kısa süre sonra tekrar deneyin.'.encode()]
        finally:conn.close()
