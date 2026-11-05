"""Reorder provisional requests from a private JSON plan; never verifies payments."""
import json
import os
import uuid
from pathlib import Path
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction
from landing.chip_models import ChipRequestRound, ChipParticipationRequest
from landing.chip import share_percent


class Command(BaseCommand):
    help = 'Apply a private provisional-request order, preserving all receipt links.'

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True)

    def handle(self, *args, **options):
        plan_path = Path(options['file'])
        plan = json.loads(plan_path.read_text())
        people = [(name.strip(), email.strip().lower()) for name, email in plan['people']]
        for name, email in people:
            validate_email(email)
            if not name or len(name) > 160:
                raise CommandError('Invalid display name')
        if len({email for _, email in people}) != len(people):
            raise CommandError('Duplicate email in plan')
        with transaction.atomic():
            round = ChipRequestRound.objects.select_for_update().get(mode=plan.get('mode', 'live'))
            if str(round.generation) != plan['generation']:
                raise CommandError('Generation changed; no changes made')
            rows = list(round.requests.filter(generation=round.generation).order_by('start_position', 'created_at'))
            canonical = {row.email: row for row in rows if row.duplicate_of_id is None}
            extras = [row for row in rows if row.duplicate_of_id is None and row.email not in {e for _, e in people}]
            ordered = [canonical.get(email) for _, email in people] + extras
            if len(ordered) > 43 or any(row.quantity != 1 for row in rows):
                raise CommandError('Unsupported capacity or multi-unit records')
            backup = plan_path.with_name(plan_path.stem + '-backup-' + str(uuid.uuid4()) + '.json')
            fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as stream:
                stream.write(serializers.serialize('json', [round] + rows))
            # Move canonical rows temporarily to avoid immediate unique-rank collisions.
            temporary = uuid.uuid4()
            round.requests.filter(generation=round.generation, duplicate_of__isnull=True).update(generation=temporary)
            for index, row in enumerate(ordered, 1):
                if index <= len(people):
                    name, email = people[index - 1]
                else:
                    name, email = row.display_name, row.email
                if row is None:
                    row = ChipParticipationRequest(round=round, nonce=uuid.uuid4(), quantity=1, email=email)
                row.generation = round.generation
                row.display_name = name
                row.start_position = index
                row.provisional_percent = share_percent(index)
                row.save()
                ordered[index - 1] = row
            round.requested_units = len(ordered)
            round.enabled = True
            round.save(update_fields=['requested_units', 'enabled'])
        self.stdout.write(self.style.SUCCESS(f'Applied {len(ordered)} participants; next position {len(ordered) + 1}; backup {backup}'))
        for index, row in enumerate(ordered, 1):
            self.stdout.write(f'{index}. {row.display_name}')
