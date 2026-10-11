from unittest.mock import patch, MagicMock
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from .models import Organization


class PersonalNamespaceTests(SimpleTestCase):
    def test_personal_address_is_rejected_with_shared_lock(self):
        organization = Organization(name='Test', slug='test', subdomain='Ayse')
        cursor = MagicMock()
        cursor.fetchone.side_effect = [('mobile_api_personalappaddress',), (1,)]
        with patch('django.db.connection') as db:
            db.vendor = 'postgresql'
            db.cursor.return_value.__enter__.return_value = cursor
            with self.assertRaises(ValidationError):
                organization._check_personal_address(lock=True)
        cursor.execute.assert_any_call('SELECT pg_advisory_xact_lock(74123, hashtext(%s))', ['ayse'])
        cursor.execute.assert_any_call('SELECT 1 FROM public.mobile_api_personalappaddress WHERE slug = %s', ['ayse'])

    def test_unused_personal_address_is_allowed(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [('mobile_api_personalappaddress',), None]
        with patch('django.db.connection') as db:
            db.vendor = 'postgresql'
            db.cursor.return_value.__enter__.return_value = cursor
            Organization(subdomain='ayse')._check_personal_address(lock=True)
