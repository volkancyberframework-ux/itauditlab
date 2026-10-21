"""Read one private JSON line from stdin; never commit invitation lists/passwords."""
import json
import sys
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from skool.models import SkoolGuestAccount, SkoolInvitation, SkoolUser


class Command(BaseCommand):
    help = 'Create community guests from one JSON line on stdin: {"emails": [...], "password": "..."}. Existing accounts are preserved.'

    def add_arguments(self, parser):
        parser.add_argument('--stdin', action='store_true', required=True)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        try:
            payload = json.loads(sys.stdin.readline())
        except (ValueError, TypeError) as error:
            raise CommandError('Expected one JSON line on stdin.') from error
        if not isinstance(payload, dict) or not isinstance(payload.get('emails'), list) or not isinstance(payload.get('password'), str):
            raise CommandError('Provide emails as a list and an initial password as a string.')
        password = payload['password']
        if len(password) < 8 or len(password) > 256:
            raise CommandError('Initial password must contain 8–256 characters.')
        emails = []
        for raw in payload['emails']:
            if not isinstance(raw, str):
                raise CommandError('Every email must be a string.')
            email = raw.strip().lower()
            try:
                validate_email(email)
            except ValidationError as error:
                raise CommandError('Input contains an invalid email address; nothing was created.') from error
            if len(email) > 145:
                raise CommandError('Email address is too long for the guest invitation.')
            if email not in emails:
                emails.append(email)
        created, existing = 0, 0
        with transaction.atomic():
            for email in emails:
                if SkoolGuestAccount.objects.filter(email__iexact=email).exists():
                    existing += 1
                    continue
                if not options['dry_run']:
                    invitation, _ = SkoolInvitation.create_invitation('Misafir ' + email)
                    invitation.status = 'claimed'
                    invitation.claimed_at = timezone.now()
                    invitation.save(update_fields=('status', 'claimed_at'))
                    user = SkoolUser.objects.create(invitation=invitation, full_name='Misafir ' + email)
                    account = SkoolGuestAccount(user=user, email=email)
                    account.set_password(password)
                    account.save()
                created += 1
        self.stdout.write(json.dumps({'created': created, 'existing_preserved': existing, 'unique_emails': len(emails), 'duplicates_removed': len(payload['emails']) - len(emails), 'dry_run': options['dry_run']}))
