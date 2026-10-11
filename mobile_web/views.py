from pathlib import Path
from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.http import require_safe


@require_safe
def app(request, path=''):
    root = Path(getattr(settings, 'MOBILE_WEB_ROOT', Path(settings.BASE_DIR) / 'mobile_web' / 'dist')).resolve()
    filename = path or 'index.html'
    target = (root / filename).resolve()
    if not target.is_relative_to(root) or not target.is_file() or any(part.startswith('.') for part in Path(filename).parts):
        raise Http404
    response = FileResponse(target.open('rb'))
    response['Cache-Control'] = 'no-cache' if target.suffix in ('.html', '.js', '.json') else 'public, max-age=3600'
    response['Permissions-Policy'] = 'microphone=(self), camera=()'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
