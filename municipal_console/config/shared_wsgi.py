import os
os.environ['DJANGO_SETTINGS_MODULE']='config.shared_settings'
from django.core.wsgi import get_wsgi_application
_django=get_wsgi_application()

def application(environ,start_response):
    # Only reachable over a private Unix socket. The public gateway overwrites this header.
    prefix=environ.pop('HTTP_X_CONSOLE_PREFIX','')
    environ['SCRIPT_NAME']='/denetim' if prefix=='/denetim' else ''
    return _django(environ,start_response)
