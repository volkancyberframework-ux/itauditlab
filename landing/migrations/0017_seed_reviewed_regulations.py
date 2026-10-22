from django.db import migrations
import json
from pathlib import Path

def seed(apps,schema_editor):
    Regulation=apps.get_model('landing','LegalRegulation')
    Revision=apps.get_model('landing','LegalRevision')
    rows=json.loads((Path(__file__).resolve().parents[1]/'data/regulations.json').read_text())
    for data in rows:
        obj,created=Regulation.objects.get_or_create(id=data['id'],defaults={k:v for k,v in data.items() if k!='id'})
        if created:Revision.objects.create(regulation=obj,actor='Reviewed release 2026-10-22',snapshot=data)

class Migration(migrations.Migration):
    dependencies=[('landing','0016_legalregulation_legalrevision')]
    operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
