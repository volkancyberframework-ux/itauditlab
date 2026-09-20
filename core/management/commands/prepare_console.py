"""Initialize only the console schema inside the existing PostgreSQL database."""
import json,os,subprocess,sys
from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection

class Command(BaseCommand):
    help='Mevcut veritabanında denetim konsolunu hazırlar; ITAudit tablolarını değiştirmez.'
    def handle(self,*args,**options):
        if connection.vendor!='postgresql':raise CommandError('Ortak kurulum mevcut PostgreSQL veritabanını gerektirir.')
        root=Path(settings.BASE_DIR)/'municipal_console'
        env={**os.environ,'DJANGO_SETTINGS_MODULE':'config.shared_settings'}
        # Serialize blue/green startup migrations without touching public tables.
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_user')
            if cursor.fetchone()[0]=='municipal_console':raise CommandError('Schema adı mevcut veritabanı kullanıcı adıyla çakışıyor; kurulum durduruldu.')
            cursor.execute('SELECT pg_advisory_lock(72748125)')
        try:
            with connection.cursor() as cursor:
                cursor.execute('CREATE SCHEMA IF NOT EXISTS municipal_console')
            subprocess.run([sys.executable,'manage.py','migrate','--noinput'],cwd=root,env=env,check=True)
            entries=[]
            for user in get_user_model().objects.filter(is_superuser=True,is_active=True):
                if user.email and user.has_usable_password():
                    entries.append({key:getattr(user,key) for key in ('email','password','first_name','last_name')})
            # Password hashes travel in a local stdin pipe; never printed or saved in a file.
            subprocess.run([sys.executable,'manage.py','import_platform_admins'],cwd=root,env=env,input=json.dumps(entries),text=True,check=True)
            subprocess.run([sys.executable,'manage.py','collectstatic','--noinput'],cwd=root,env=env,check=True,stdout=subprocess.DEVNULL)
            self.stdout.write('Konsol /denetim/ adresinde mevcut admin e-postası ve parolasıyla kullanıma hazır.')
        finally:
            with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_unlock(72748125)')
