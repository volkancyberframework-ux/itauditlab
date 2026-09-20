import secrets
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
class Command(BaseCommand):
    help = 'Create one local demo account; never allowed in production.'
    def handle(self, *args, **kwargs):
        if not settings.DEBUG:
            raise CommandError('Demo hesap yalnızca DEBUG=true iken oluşturulabilir.')
        email = 'demo@grcustasi.local'
        if get_user_model().objects.filter(email=email).exists():
            self.stdout.write('Demo hesabı zaten var. Parolası değiştirilmedi.')
            return
        password = secrets.token_urlsafe(15)
        get_user_model().objects.create_user(email, password, first_name='Demo', must_change_password=True)
        self.stdout.write(f'E-posta: {email}\nGeçici parola: {password}\nİlk girişte parola değişikliği zorunludur.')
