"""Same PostgreSQL instance as ITAudit, isolated table namespace and sessions."""
import os
os.environ.setdefault('DEBUG','false')
from .settings import *
from django.core.exceptions import ImproperlyConfigured

if DATABASES['default']['ENGINE']!='django.db.backends.postgresql':
    raise ImproperlyConfigured('Shared deployment requires the existing PostgreSQL DATABASE_URL.')
DATABASES['default'].setdefault('OPTIONS',{})['options']='-c search_path=municipal_console'
STATIC_URL='/denetim/static/'
WHITENOISE_STATIC_PREFIX='/static/'
# Existing environment values are reused. No second SMTP or Telegram setup.
EMAIL_HOST=os.getenv('EMAIL_HOST','smtp.gmail.com')
EMAIL_PORT=int(os.getenv('EMAIL_PORT','587'))
EMAIL_HOST_USER=os.getenv('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD=os.getenv('EMAIL_HOST_PASSWORD','')
DEFAULT_FROM_EMAIL=os.getenv('DEFAULT_FROM_EMAIL',EMAIL_HOST_USER)

PUBLIC_CONSOLE_URL=os.getenv('PUBLIC_BASE_URL','https://www.grcustasi.com').rstrip('/')+'/denetim'
