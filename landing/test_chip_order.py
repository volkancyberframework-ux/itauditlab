import json
import tempfile
import uuid
from pathlib import Path
from django.core.management import call_command
from django.test import TestCase
from landing.chip_models import ChipRequestRound, ChipParticipationRequest
from landing.chip import share_percent


class OrderTests(TestCase):
    def test_reorder_preserves_links_and_next_position(self):
        r, _ = ChipRequestRound.objects.update_or_create(mode='live', defaults={'requested_units':4, 'enabled':False})
        rows = []
        for i, email in enumerate(['first@example.com', 'third@example.com', 'fourth@example.com'], 1):
            rows.append(ChipParticipationRequest.objects.create(round=r, generation=r.generation, nonce=uuid.uuid4(), email=email, quantity=1, start_position=i, provisional_percent=share_percent(i)))
        alias = ChipParticipationRequest.objects.create(round=r, generation=r.generation, nonce=uuid.uuid4(), email=rows[2].email, quantity=1, start_position=4, provisional_percent=share_percent(4), duplicate_of=rows[2])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plan.json'
            path.write_text(json.dumps({'generation':str(r.generation), 'people':[['First',rows[0].email],['Second','second@example.com'],['Third',rows[1].email],['Fourth',rows[2].email]]}))
            call_command('apply_chip_order', file=str(path))
            call_command('apply_chip_order', file=str(path))
            self.assertEqual(len(list(Path(directory).glob('*backup*'))), 2)
        r.refresh_from_db()
        self.assertEqual(r.requested_units, 4)
        self.assertTrue(r.enabled)
        self.assertEqual(list(r.requests.filter(duplicate_of__isnull=True).order_by('start_position').values_list('display_name',flat=True)), ['First','Second','Third','Fourth'])
        rows[2].refresh_from_db()
        alias.refresh_from_db()
        self.assertEqual(rows[2].start_position, 4)
        self.assertEqual(alias.duplicate_of_id, rows[2].pk)
        self.assertEqual(r.requests.count(), 5)
