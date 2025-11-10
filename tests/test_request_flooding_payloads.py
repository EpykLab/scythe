import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the scythe package to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.payloads.generators import StaticPayloadGenerator, PayloadGenerator


class CustomPayloadGenerator(PayloadGenerator):
    """Custom payload generator for testing."""

    def __init__(self, payloads):
        self.payloads = payloads

    def __iter__(self):
        yield from self.payloads


# Mock selenium to avoid import errors
sys.modules['selenium'] = Mock()
sys.modules['selenium.webdriver'] = Mock()
sys.modules['selenium.webdriver.common'] = Mock()
sys.modules['selenium.webdriver.common.by'] = Mock()
sys.modules['selenium.webdriver.remote'] = Mock()
sys.modules['selenium.webdriver.remote.webdriver'] = Mock()
sys.modules['selenium.common'] = Mock()
sys.modules['selenium.common.exceptions'] = Mock()

from scythe.ttps.web.request_flooding import RequestFloodingTTP


class TestRequestFloodingPayloads(unittest.TestCase):
    """Test RequestFloodingTTP payload iteration functionality."""

    def test_single_dict_payload(self):
        """Test with a single dict (original behavior)."""
        ttp = RequestFloodingTTP(
            target_endpoints=['/api/test'],
            request_count=5,
            payload_data={'user': 'test', 'action': 'login'},
            execution_mode='api'
        )

        payloads = list(ttp.get_payloads())

        self.assertEqual(len(payloads), 5)

        # All payloads should have the same data
        for payload in payloads:
            self.assertEqual(payload['data'], {'user': 'test', 'action': 'login'})

    def test_list_of_dicts_payload(self):
        """Test with a list of dicts that cycles through."""
        payload_list = [
            {'user': 'user1', 'action': 'login'},
            {'user': 'user2', 'action': 'logout'},
            {'user': 'user3', 'action': 'update'},
        ]

        ttp = RequestFloodingTTP(
            target_endpoints=['/api/test'],
            request_count=7,  # More than list length to test cycling
            payload_data=payload_list,
            execution_mode='api'
        )

        payloads = list(ttp.get_payloads())

        self.assertEqual(len(payloads), 7)

        # Verify cycling through the list
        self.assertEqual(payloads[0]['data'], payload_list[0])
        self.assertEqual(payloads[1]['data'], payload_list[1])
        self.assertEqual(payloads[2]['data'], payload_list[2])
        self.assertEqual(payloads[3]['data'], payload_list[0])  # Cycles back
        self.assertEqual(payloads[4]['data'], payload_list[1])
        self.assertEqual(payloads[5]['data'], payload_list[2])
        self.assertEqual(payloads[6]['data'], payload_list[0])

    def test_static_payload_generator(self):
        """Test with StaticPayloadGenerator."""
        payload_gen = StaticPayloadGenerator([
            {'query': 'test1', 'limit': 10},
            {'query': 'test2', 'limit': 20},
            {'query': 'test3', 'limit': 30},
        ])

        ttp = RequestFloodingTTP(
            target_endpoints=['/api/search'],
            request_count=3,
            payload_data=payload_gen,
            execution_mode='api'
        )

        payloads = list(ttp.get_payloads())

        self.assertEqual(len(payloads), 3)
        self.assertEqual(payloads[0]['data'], {'query': 'test1', 'limit': 10})
        self.assertEqual(payloads[1]['data'], {'query': 'test2', 'limit': 20})
        self.assertEqual(payloads[2]['data'], {'query': 'test3', 'limit': 30})

    def test_custom_payload_generator(self):
        """Test with a custom PayloadGenerator."""
        custom_payloads = [
            {'type': 'search', 'term': 'test'},
            {'type': 'filter', 'category': 'books'},
            {'type': 'sort', 'order': 'asc'},
        ]

        payload_gen = CustomPayloadGenerator(custom_payloads)

        ttp = RequestFloodingTTP(
            target_endpoints=['/api/query'],
            request_count=3,
            payload_data=payload_gen,
            execution_mode='api'
        )

        payloads = list(ttp.get_payloads())

        self.assertEqual(len(payloads), 3)
        for i, payload in enumerate(payloads):
            self.assertEqual(payload['data'], custom_payloads[i])

    def test_none_payload(self):
        """Test with None payload_data."""
        ttp = RequestFloodingTTP(
            target_endpoints=['/api/test'],
            request_count=3,
            payload_data=None,
            execution_mode='api'
        )

        payloads = list(ttp.get_payloads())

        self.assertEqual(len(payloads), 3)
        for payload in payloads:
            self.assertEqual(payload['data'], {})

    def test_empty_list_payload(self):
        """Test with empty list payload_data."""
        ttp = RequestFloodingTTP(
            target_endpoints=['/api/test'],
            request_count=3,
            payload_data=[],
            execution_mode='api'
        )

        payloads = list(ttp.get_payloads())

        self.assertEqual(len(payloads), 3)
        for payload in payloads:
            self.assertEqual(payload['data'], {})

    def test_resource_exhaustion_with_list(self):
        """Test resource_exhaustion pattern adds params to list payloads."""
        payload_list = [
            {'query': 'test1'},
            {'query': 'test2'},
        ]

        ttp = RequestFloodingTTP(
            target_endpoints=['/api/data'],
            request_count=2,
            attack_pattern='resource_exhaustion',
            payload_data=payload_list,
            execution_mode='api'
        )

        payloads = list(ttp.get_payloads())

        self.assertEqual(len(payloads), 2)

        # Verify resource exhaustion params are added
        for i, payload in enumerate(payloads):
            self.assertIn('limit', payload['data'])
            self.assertIn('search', payload['data'])
            self.assertIn('recursive', payload['data'])
            # Original query should be preserved
            self.assertIn('query', payload['data'])
            self.assertEqual(payload['data']['query'], f'test{i+1}')

    def test_resource_exhaustion_with_dict(self):
        """Test resource_exhaustion pattern adds params to dict payload."""
        ttp = RequestFloodingTTP(
            target_endpoints=['/api/data'],
            request_count=2,
            attack_pattern='resource_exhaustion',
            payload_data={'custom': 'value'},
            execution_mode='api'
        )

        payloads = list(ttp.get_payloads())

        self.assertEqual(len(payloads), 2)

        # Verify resource exhaustion params are added
        for payload in payloads:
            self.assertIn('limit', payload['data'])
            self.assertIn('search', payload['data'])
            self.assertIn('recursive', payload['data'])
            # Original custom field should be preserved
            self.assertIn('custom', payload['data'])
            self.assertEqual(payload['data']['custom'], 'value')

    def test_payload_structure(self):
        """Test that payload structure includes all necessary fields."""
        ttp = RequestFloodingTTP(
            target_endpoints=['/api/test'],
            request_count=1,
            payload_data={'test': 'data'},
            execution_mode='api'
        )

        payloads = list(ttp.get_payloads())
        payload = payloads[0]

        # Verify payload structure
        self.assertIn('request_id', payload)
        self.assertIn('endpoint', payload)
        self.assertIn('data', payload)
        self.assertIn('user_agent', payload)
        self.assertIn('delay', payload)
        self.assertIn('timeout', payload)

        self.assertEqual(payload['request_id'], 0)
        self.assertEqual(payload['endpoint'], '/api/test')
        self.assertEqual(payload['data'], {'test': 'data'})

    def test_multiple_endpoints_with_list_payloads(self):
        """Test cycling through both endpoints and payloads."""
        payload_list = [
            {'data': 'A'},
            {'data': 'B'},
        ]

        ttp = RequestFloodingTTP(
            target_endpoints=['/api/endpoint1', '/api/endpoint2'],
            request_count=4,
            payload_data=payload_list,
            execution_mode='api'
        )

        payloads = list(ttp.get_payloads())

        self.assertEqual(len(payloads), 4)

        # Verify endpoints cycle
        self.assertEqual(payloads[0]['endpoint'], '/api/endpoint1')
        self.assertEqual(payloads[1]['endpoint'], '/api/endpoint2')
        self.assertEqual(payloads[2]['endpoint'], '/api/endpoint1')
        self.assertEqual(payloads[3]['endpoint'], '/api/endpoint2')

        # Verify data cycles independently
        self.assertEqual(payloads[0]['data'], {'data': 'A'})
        self.assertEqual(payloads[1]['data'], {'data': 'B'})
        self.assertEqual(payloads[2]['data'], {'data': 'A'})
        self.assertEqual(payloads[3]['data'], {'data': 'B'})

    def test_backward_compatibility(self):
        """Test that existing code using dict still works (backward compatibility)."""
        # This simulates the old usage pattern
        ttp = RequestFloodingTTP(
            target_endpoints=['/api/search'],
            request_count=3,
            payload_data={'query': 'test', 'limit': 100},
            http_method='POST',
            execution_mode='api'
        )

        payloads = list(ttp.get_payloads())

        # Should work exactly as before
        self.assertEqual(len(payloads), 3)
        for payload in payloads:
            self.assertEqual(payload['data'], {'query': 'test', 'limit': 100})


if __name__ == '__main__':
    unittest.main()
