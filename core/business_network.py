"""Stable plate-code reference and permissioned state changes for the public network."""
import json
from pathlib import Path
from django.db import transaction
from django.utils import timezone

GEOMETRY = Path(__file__).resolve().parent.parent / 'static/data/turkiye-provinces.geojson'
PROVINCES = {feature['properties']['il_kodu']:feature['properties']['il_adi'] for feature in json.loads(GEOMETRY.read_text())['features']}
INITIAL_ACTIVE = frozenset(('35','34','06','19','57','55','31','01','45','09','43'))

def public_snapshot():
    from .models import BusinessNetworkCity
    cities=list(BusinessNetworkCity.objects.order_by('city_code').values('city_code','city_name','is_active'))
    if len(cities)!=81 or {row['city_code']:row['city_name'] for row in cities}!=PROVINCES:
        raise ValueError('Business network reference is incomplete')
    return {'cities':cities,'stats':{'active_count':sum(row['is_active'] for row in cities),'total_count':len(cities)}}

@transaction.atomic
def set_city_state(code,active,actor):
    from .models import BusinessNetworkCity
    city=BusinessNetworkCity.objects.select_for_update().get(pk=code)
    if city.is_active != active:
        city.is_active=active
        city.activated_at=timezone.now() if active else None
        city.updated_by=actor
        city.save(update_fields=('is_active','activated_at','updated_by','updated_at'))
    return city
