import json
import logging
from pathlib import Path
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from core.business_network import public_snapshot

logger=logging.getLogger(__name__)
COPY=json.loads((Path(__file__).parent/'data/business_network_i18n.json').read_text())

def context():
    try:stats=public_snapshot()['stats']
    except (DatabaseError,ValueError):stats={'active_count':None,'total_count':81}
    return {'network_stats':stats,'network_copy':COPY}

@never_cache
@require_GET
def cities(request):
    try:return JsonResponse(public_snapshot())
    except (DatabaseError,ValueError):
        logger.exception('Business network unavailable')
        return JsonResponse({'error':'network_unavailable'},status=503)

@never_cache
@require_GET
def stats(request):
    try:return JsonResponse(public_snapshot()['stats'])
    except (DatabaseError,ValueError):return JsonResponse({'error':'network_unavailable'},status=503)
