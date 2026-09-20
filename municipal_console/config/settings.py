import os
from django.urls import reverse_lazy
from pathlib import Path
from datetime import timedelta
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'local-development-only-do-not-deploy-this-key')
if not DEBUG and SECRET_KEY == 'local-development-only-do-not-deploy-this-key':
    raise ImproperlyConfigured('Production requires SECRET_KEY.')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
CSRF_TRUSTED_ORIGINS = [v for v in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if v]
INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','accounts','workspace','axes']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','workspace.middleware.TenantMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware','axes.middleware.AxesMiddleware']
ROOT_URLCONF = 'config.urls'
MIDDLEWARE.insert(MIDDLEWARE.index('django.contrib.auth.middleware.AuthenticationMiddleware')+1, 'accounts.privacy.PrivacyMiddleware')
WSGI_APPLICATION = 'config.wsgi.application'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR / 'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','workspace.branding.brand_context']}}]
DATABASES = {'default':dj_database_url.config(default=f'sqlite:///{BASE_DIR / "db.sqlite3"}', conn_max_age=60)}
if not DEBUG and DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise ImproperlyConfigured('Production requires a PostgreSQL DATABASE_URL.')
AUTH_USER_MODEL = 'accounts.User'
AUTHENTICATION_BACKENDS = ['axes.backends.AxesStandaloneBackend','django.contrib.auth.backends.ModelBackend']
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = 'accounts/locked.html'
AUTH_PASSWORD_VALIDATORS = [{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = reverse_lazy('signin')
LOGIN_REDIRECT_URL = reverse_lazy('console')
ROOT_SIGNIN_ENABLED = os.getenv('ROOT_SIGNIN_ENABLED','true').lower() == 'true'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', str(not DEBUG)).lower() == 'true'
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

TENANT_BASE_DOMAIN = os.getenv('TENANT_BASE_DOMAIN', 'grcustasi.com').lower()

SESSION_COOKIE_NAME = 'municipal_sessionid'
CSRF_COOKIE_NAME = 'municipal_csrftoken'
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_DOMAIN = None
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
    ALLOWED_HOSTS.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])
ALLOWED_HOSTS.append('.'+TENANT_BASE_DOMAIN)
TELEGRAM_BOT_TOKEN = os.getenv('GRCUSTASI_TELEGRAM_BOT_TOKEN', os.getenv('TELEGRAM_BOT_TOKEN', ''))
TELEGRAM_CHAT_ID = os.getenv('GRCUSTASI_TELEGRAM_ADMIN_CHAT_ID') or os.getenv('TELEGRAM_ADMIN_CHAT_ID') or os.getenv('TELEGRAM_CHAT_ID','')

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'false').lower() == 'true'
EMAIL_TIMEOUT = 8
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@grcustasi.com')
