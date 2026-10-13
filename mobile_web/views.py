from pathlib import Path
from django.conf import settings
from django.http import FileResponse, Http404, StreamingHttpResponse
from django.views.decorators.http import require_safe


@require_safe
def app(request, path=''):
    root = Path(getattr(settings, 'MOBILE_WEB_ROOT', Path(settings.BASE_DIR) / 'mobile_web' / 'dist')).resolve()
    filename = path or 'index.html'
    target = (root / filename).resolve()
    if not target.is_relative_to(root) or not target.is_file() or any(part.startswith('.') for part in Path(filename).parts):
        raise Http404
    if filename == 'index.html' and request.get_host().split(':')[0] == 'app.grcustasi.com':
        # Never edit or rebuild the Flutter source or generated distribution.
        html = target.read_text()
        html = html.replace('</head>', '<link rel="stylesheet" href="/web-features/web-learning.css"></head>')
        html = html.replace('<script src="flutter_bootstrap.js"', '<script src="/web-features/bridge.js"></script><script src="/web-features/pwa.js" defer></script><script src="flutter_bootstrap.js"')
        response = StreamingHttpResponse(iter([html.encode()]), content_type='text/html; charset=utf-8')
    else:
        response = FileResponse(target.open('rb'))
    response['Cache-Control'] = 'no-cache' if target.suffix in ('.html', '.js', '.json') else 'public, max-age=3600'
    response['Permissions-Policy'] = 'microphone=(self), camera=()'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@require_safe
def web_asset(request,path):
    root=(Path(__file__).parent/'web').resolve();target=(root/path).resolve()
    if not target.is_relative_to(root) or not target.is_file() or target.suffix not in ('.js','.mjs','.css','.html') or any(part.startswith('.') for part in Path(path).parts):
        raise Http404
    response=FileResponse(target.open('rb'),content_type='text/css' if target.suffix=='.css' else 'text/html' if target.suffix=='.html' else 'text/javascript')
    response['Cache-Control']='no-cache';response['X-Content-Type-Options']='nosniff';return response

@require_safe
def pwa_worker(request):
    response=web_asset(request,'grc-pwa-sw.js')
    response['Service-Worker-Allowed']='/'
    return response
