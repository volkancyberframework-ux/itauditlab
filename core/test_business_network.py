import json
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import OperationalError
from django.test import TestCase, Client
from django.urls import reverse
from .business_network import PROVINCES, INITIAL_ACTIVE, public_snapshot
from .models import BusinessNetworkCity

class BusinessNetworkTests(TestCase):
    def setUp(self):
        self.admin=get_user_model().objects.create_superuser(username='network-admin',email='network@example.com',password='test-only')
        self.url=reverse('admin:core_businessnetworkcity_toggle',args=['16'])
    def test_seed_has_all_81_unique_codes_and_11_active_provinces(self):
        self.assertEqual(len(PROVINCES),81)
        self.assertEqual(set(PROVINCES),{f'{code:02}' for code in range(1,82)})
        self.assertEqual(BusinessNetworkCity.objects.count(),81)
        self.assertEqual(set(BusinessNetworkCity.objects.filter(is_active=True).values_list('city_code',flat=True)),INITIAL_ACTIVE)
        self.assertTrue(BusinessNetworkCity.objects.get(pk='43').is_active)
        self.assertEqual(public_snapshot()['stats'],{'active_count':11,'total_count':81})
    def test_public_endpoints_are_readonly_and_exclude_editor_identity(self):
        response=self.client.get('/api/business-network/cities/')
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.json()['cities']),81)
        self.assertNotIn('updated_by',response.content.decode())
        self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(self.client.post('/api/business-network/cities/').status_code,405)
        self.assertEqual(self.client.get('/api/business-network/stats/').json()['active_count'],11)
    def test_admin_can_toggle_and_state_survives_fresh_requests(self):
        self.client.force_login(self.admin)
        response=self.client.patch(self.url,data=json.dumps({'is_active':True}),content_type='application/json')
        self.assertEqual(response.status_code,200)
        city=BusinessNetworkCity.objects.get(pk='16')
        self.assertTrue(city.is_active);self.assertEqual(city.updated_by,self.admin);self.assertIsNotNone(city.activated_at)
        self.assertEqual(Client().get('/api/business-network/stats/').json()['active_count'],12)
        from landing.business_network import context
        self.assertEqual(context()['network_stats']['development_count'],69)
        stamp=city.updated_at
        self.client.patch(self.url,data=json.dumps({'is_active':True}),content_type='application/json')
        city.refresh_from_db();self.assertEqual(city.updated_at,stamp)
        self.client.patch(self.url,data=json.dumps({'is_active':False}),content_type='application/json')
        self.assertEqual(Client().get('/api/business-network/stats/').json()['active_count'],11)
        self.assertEqual(context()['network_stats']['development_count'],70)
    def test_staff_without_specific_permission_cannot_change_state(self):
        user=get_user_model().objects.create_user(username='viewer',password='test',is_staff=True)
        self.client.force_login(user)
        self.assertEqual(self.client.patch(self.url,data='{"is_active":true}',content_type='application/json').status_code,403)
        user.user_permissions.add(Permission.objects.get(codename='change_businessnetworkcity'))
        self.assertEqual(self.client.patch(self.url,data='{"is_active":true}',content_type='application/json').status_code,200)
    def test_anonymous_and_nonstaff_cannot_mutate(self):
        self.assertEqual(self.client.patch(self.url,data='{"is_active":true}',content_type='application/json').status_code,302)
        user=get_user_model().objects.create_user(username='student-network',password='test')
        self.client.force_login(user)
        self.assertEqual(self.client.patch(self.url,data='{"is_active":true}',content_type='application/json').status_code,302)
        self.assertFalse(BusinessNetworkCity.objects.get(pk='16').is_active)
    def test_csrf_required_even_for_superuser(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.admin)
        self.assertEqual(client.patch(self.url,data='{"is_active":true}',content_type='application/json').status_code,403)
    def test_invalid_payloads_and_codes_are_rejected(self):
        self.client.force_login(self.admin)
        for payload in ['invalid','[]','{"is_active":"false"}','{"is_active":true,"city_name":"Wrong"}']:
            self.assertEqual(self.client.patch(self.url,data=payload,content_type='application/json').status_code,400)
        self.assertEqual(self.client.patch(reverse('admin:core_businessnetworkcity_toggle',args=['99']),data='{"is_active":true}',content_type='application/json').status_code,404)
        self.assertEqual(self.client.get(self.url).status_code,405)
    def test_admin_map_and_fixed_reference_management(self):
        self.client.force_login(self.admin)
        response=self.client.get(reverse('admin:core_businessnetworkcity_changelist'))
        self.assertContains(response,'data-network-admin')
        self.assertContains(response,'data-toggle-city="43"')
        self.assertEqual(self.client.get(reverse('admin:core_businessnetworkcity_add')).status_code,403)
    def test_seed_is_idempotent_and_preserves_existing_admin_choices(self):
        import importlib
        from django.apps import apps
        BusinessNetworkCity.objects.filter(pk='43').update(is_active=False)
        BusinessNetworkCity.objects.filter(pk='16').update(is_active=True)
        importlib.import_module('core.migrations.0031_seed_business_network').seed(apps,None)
        self.assertFalse(BusinessNetworkCity.objects.get(pk='43').is_active)
        self.assertTrue(BusinessNetworkCity.objects.get(pk='16').is_active)
        self.assertEqual(BusinessNetworkCity.objects.count(),81)
    def test_unavailable_api_degrades_without_failing_home(self):
        with patch('landing.business_network.public_snapshot',side_effect=OperationalError('offline')):
            self.assertEqual(self.client.get('/api/business-network/cities/').status_code,503)
            self.assertContains(self.client.get('/'),'data-business-network')
    def test_geometry_is_real_polygons_and_correctly_keyed(self):
        from .business_network import GEOMETRY
        geo=json.loads(GEOMETRY.read_text())
        for feature in geo['features']:
            self.assertIn(feature['geometry']['type'],('Polygon','MultiPolygon'))
            self.assertEqual(feature['id'],feature['properties']['il_kodu'])
            self.assertEqual(PROVINCES[feature['id']],feature['properties']['il_adi'])
        self.assertEqual(PROVINCES['34'],'İstanbul');self.assertEqual(PROVINCES['35'],'İzmir');self.assertEqual(PROVINCES['43'],'Kütahya')
    def test_eight_languages_have_complete_contact_copy(self):
        from landing.business_network import COPY
        self.assertEqual(set(COPY),{'tr','en','fr','es','ja','zh-CN','vi','ar'})
        for language,copy in COPY.items():
            self.assertEqual(set(copy),set(COPY['tr']))
            self.assertTrue(all(copy.values()))
