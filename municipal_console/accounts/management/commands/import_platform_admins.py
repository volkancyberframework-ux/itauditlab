import json,sys
from django.core.management.base import BaseCommand,CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from django.db import transaction

class Command(BaseCommand):
    help='Trusted local deployment pipe only: seed separate console admins without syncing existing accounts.'
    @transaction.atomic
    def handle(self,*args,**options):
        entries=json.load(sys.stdin)
        count=0
        for data in entries:
            email=data['email'].strip().lower()
            if not email or get_user_model().objects.filter(email__iexact=email).exists():continue
            identify_hasher(data['password'])
            get_user_model().objects.create(email=email,password=data['password'],first_name=data['first_name'],last_name=data['last_name'],is_active=True,is_staff=True,is_superuser=True,must_change_password=False)
            count+=1
        self.stdout.write(f'{count} bağımsız konsol yöneticisi hazırlandı. Mevcut hesaplar değiştirilmedi.')
