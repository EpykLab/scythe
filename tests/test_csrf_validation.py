import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add the scythe package to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.ttps.web.csrf_validation import CSRFValidationTTP
from scythe.core.csrf import CSRFProtection
from scythe.core.executor import TTPExecutor


class TestCSRFValidationTTPInitialization(unittest.TestCase):
    """Test cases for CSRFValidationTTP initialization."""

    def test_basic_initialization(self):
        """Test basic initialization with minimal parameters."""
        csrf = CSRFProtection()
        ttp = CSRFValidationTTP(
            target_endpoints=['/api/users', '/api/posts'],
            csrf_protection=csrf
        )

        self.assertEqual(len(ttp.target_endpoints), 2)
        self.assertEqual(ttp.http_method, 'POST')
        self.assertEqual(ttp.execution_mode, 'api')
        self.assertTrue(ttp.expected_result)
        self.assertIsNotNone(ttp.csrf_protection)

    def test_custom_initialization(self):
        """Test initialization with all custom parameters."""
        csrf = CSRFProtection(
            cookie_name='custom-csrf',
            header_name='X-Custom-CSRF'
        )

        ttp = CSRFValidationTTP(
            target_endpoints=['/api/endpoint1', '/api/endpoint2', '/api/endpoint3'],
            http_method='PUT',
            test_payload={'key': 'value'},
            csrf_protection=csrf,
            expected_rejection_codes=[403, 419, 401],
            expected_success_codes=[200, 201],
            test_invalid_token=False,
            invalid_token_value='custom-invalid',
            expected_result=False
        )

        self.assertEqual(len(ttp.target_endpoints), 3)
        self.assertEqual(ttp.http_method, 'PUT')
        self.assertEqual(ttp.test_payload, {'key': 'value'})
        self.assertEqual(ttp.expected_rejection_codes, [403, 419, 401])
        self.assertEqual(ttp.expected_success_codes, [200, 201])
        self.assertFalse(ttp.test_invalid_token)
        self.assertEqual(ttp.invalid_token_value, 'custom-invalid')
        self.assertFalse(ttp.expected_result)

    def test_initialization_without_csrf_protection(self):
        """Test that TTP can be initialized without CSRF protection."""
        ttp = CSRFValidationTTP(
            target_endpoints=['/api/test'],
            csrf_protection=None
        )

        self.assertIsNone(ttp.csrf_protection)
        # Should only test rejection without tokens
        payloads = list(ttp.get_payloads())
        self.assertEqual(len(payloads), 1)  # Only 'without_token' test


class TestCSRFValidationPayloads(unittest.TestCase):
    """Test cases for payload generation."""

    def test_payload_generation_with_all_tests(self):
        """Test that all three test types are generated per endpoint."""
        csrf = CSRFProtection()
        ttp = CSRFValidationTTP(
            target_endpoints=['/api/users'],
            csrf_protection=csrf,
            test_invalid_token=True
        )

        payloads = list(ttp.get_payloads())

        # Should have 3 tests: without_token, with_valid_token, with_invalid_token
        self.assertEqual(len(payloads), 3)

        # Check test types
        test_types = [p['test_type'] for p in payloads]
        self.assertIn('without_token', test_types)
        self.assertIn('with_valid_token', test_types)
        self.assertIn('with_invalid_token', test_types)

    def test_payload_generation_without_invalid_token_test(self):
        """Test payload generation when invalid token test is disabled."""
        csrf = CSRFProtection()
        ttp = CSRFValidationTTP(
            target_endpoints=['/api/users'],
            csrf_protection=csrf,
            test_invalid_token=False
        )

        payloads = list(ttp.get_payloads())

        # Should have 2 tests: without_token, with_valid_token
        self.assertEqual(len(payloads), 2)

        test_types = [p['test_type'] for p in payloads]
        self.assertIn('without_token', test_types)
        self.assertIn('with_valid_token', test_types)
        self.assertNotIn('with_invalid_token', test_types)

    def test_payload_generation_multiple_endpoints(self):
        """Test payload generation for multiple endpoints."""
        csrf = CSRFProtection()
        ttp = CSRFValidationTTP(
            target_endpoints=['/api/users', '/api/posts', '/api/comments'],
            csrf_protection=csrf,
            test_invalid_token=True
        )

        payloads = list(ttp.get_payloads())

        # Should have 3 endpoints × 3 tests = 9 payloads
        self.assertEqual(len(payloads), 9)

        # Check all endpoints are tested
        endpoints = [p['endpoint'] for p in payloads]
        self.assertEqual(endpoints.count('/api/users'), 3)
        self.assertEqual(endpoints.count('/api/posts'), 3)
        self.assertEqual(endpoints.count('/api/comments'), 3)

    def test_payload_structure(self):
        """Test that payloads have correct structure."""
        csrf = CSRFProtection()
        ttp = CSRFValidationTTP(
            target_endpoints=['/api/test'],
            csrf_protection=csrf
        )

        payloads = list(ttp.get_payloads())
        payload = payloads[0]

        # Check required fields
        self.assertIn('endpoint', payload)
        self.assertIn('test_type', payload)
        self.assertIn('expected_outcome', payload)
        self.assertIn('use_token', payload)
        self.assertIn('use_invalid_token', payload)


class TestCSRFValidationExecution(unittest.TestCase):
    """Test cases for CSRF validation execution."""

    def setUp(self):
        self.csrf = CSRFProtection(
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )
        self.ttp = CSRFValidationTTP(
            target_endpoints=['/api/test'],
            csrf_protection=self.csrf,
            test_payload={'data': 'test'}
        )
        self.mock_session = MagicMock()
        self.context = {
            'target_url': 'https://example.com',
            'csrf_protection': self.csrf,
            'csrf_token': 'valid_token',
            'auth_headers': {}
        }

    def test_execute_without_token(self):
        """Test execution without CSRF token."""
        payload = {
            'endpoint': '/api/test',
            'test_type': 'without_token',
            'expected_outcome': 'rejected',
            'use_token': False,
            'use_invalid_token': False
        }

        mock_response = Mock()
        mock_response.status_code = 403
        self.mock_session.request.return_value = mock_response

        response = self.ttp.execute_step_api(self.mock_session, payload, self.context)

        # Verify request was made without CSRF header
        call_args = self.mock_session.request.call_args
        headers = call_args[1]['headers']
        self.assertNotIn('X-CSRF-Token', headers)
        self.assertEqual(response.status_code, 403)

    def test_execute_with_valid_token(self):
        """Test execution with valid CSRF token."""
        payload = {
            'endpoint': '/api/test',
            'test_type': 'with_valid_token',
            'expected_outcome': 'success',
            'use_token': True,
            'use_invalid_token': False
        }

        mock_response = Mock()
        mock_response.status_code = 200
        self.mock_session.request.return_value = mock_response

        response = self.ttp.execute_step_api(self.mock_session, payload, self.context)

        # Verify request was made with CSRF header
        call_args = self.mock_session.request.call_args
        headers = call_args[1]['headers']
        self.assertIn('X-CSRF-Token', headers)
        self.assertEqual(headers['X-CSRF-Token'], 'valid_token')
        self.assertEqual(response.status_code, 200)

    def test_execute_with_invalid_token(self):
        """Test execution with invalid CSRF token."""
        payload = {
            'endpoint': '/api/test',
            'test_type': 'with_invalid_token',
            'expected_outcome': 'rejected',
            'use_token': True,
            'use_invalid_token': True
        }

        mock_response = Mock()
        mock_response.status_code = 403
        self.mock_session.request.return_value = mock_response

        response = self.ttp.execute_step_api(self.mock_session, payload, self.context)

        # Verify request was made with invalid CSRF header
        call_args = self.mock_session.request.call_args
        headers = call_args[1]['headers']
        self.assertIn('X-CSRF-Token', headers)
        self.assertEqual(headers['X-CSRF-Token'], self.ttp.invalid_token_value)
        self.assertEqual(response.status_code, 403)


class TestCSRFValidationVerification(unittest.TestCase):
    """Test cases for result verification."""

    def setUp(self):
        self.csrf = CSRFProtection()
        self.ttp = CSRFValidationTTP(
            target_endpoints=['/api/test'],
            csrf_protection=self.csrf
        )
        self.context = {}

    def test_verify_rejection_success(self):
        """Test verification when rejection is expected and received."""
        # Setup: Record a test expecting rejection
        self.ttp.validation_results['test_details'].append({
            'endpoint': '/api/test',
            'test_type': 'without_token',
            'expected_outcome': 'rejected',
            'status_code': 403,
            'response_time_ms': 100,
            'error': None,
            'result': 'PENDING',
            'behavior': 'Unknown'
        })

        mock_response = Mock()
        mock_response.status_code = 403

        result = self.ttp.verify_result_api(mock_response, self.context)

        self.assertTrue(result)
        self.assertEqual(self.ttp.validation_results['test_details'][-1]['result'], 'PASS')

    def test_verify_rejection_failure_vulnerability(self):
        """Test verification when rejection expected but request succeeded (VULNERABILITY)."""
        # Setup: Record a test expecting rejection
        self.ttp.validation_results['test_details'].append({
            'endpoint': '/api/test',
            'test_type': 'without_token',
            'expected_outcome': 'rejected',
            'status_code': 200,
            'response_time_ms': 100,
            'error': None,
            'result': 'PENDING',
            'behavior': 'Unknown'
        })

        mock_response = Mock()
        mock_response.status_code = 200

        result = self.ttp.verify_result_api(mock_response, self.context)

        self.assertFalse(result)
        self.assertEqual(self.ttp.validation_results['test_details'][-1]['result'], 'FAIL')
        self.assertGreater(self.ttp.validation_results['endpoints_vulnerable'], 0)

    def test_verify_success_with_valid_token(self):
        """Test verification when success is expected with valid token."""
        # Setup: Record a test expecting success
        self.ttp.validation_results['test_details'].append({
            'endpoint': '/api/test',
            'test_type': 'with_valid_token',
            'expected_outcome': 'success',
            'status_code': 200,
            'response_time_ms': 100,
            'error': None,
            'result': 'PENDING',
            'behavior': 'Unknown'
        })

        mock_response = Mock()
        mock_response.status_code = 200

        result = self.ttp.verify_result_api(mock_response, self.context)

        self.assertTrue(result)
        self.assertEqual(self.ttp.validation_results['test_details'][-1]['result'], 'PASS')

    def test_verify_success_failure_valid_token_rejected(self):
        """Test verification when success expected but valid token was rejected."""
        # Setup: Record a test expecting success
        self.ttp.validation_results['test_details'].append({
            'endpoint': '/api/test',
            'test_type': 'with_valid_token',
            'expected_outcome': 'success',
            'status_code': 403,
            'response_time_ms': 100,
            'error': None,
            'result': 'PENDING',
            'behavior': 'Unknown'
        })

        mock_response = Mock()
        mock_response.status_code = 403

        result = self.ttp.verify_result_api(mock_response, self.context)

        self.assertFalse(result)
        self.assertEqual(self.ttp.validation_results['test_details'][-1]['result'], 'FAIL')


class TestCSRFValidationSummary(unittest.TestCase):
    """Test cases for validation summary."""

    def test_summary_all_protected(self):
        """Test summary when all endpoints are protected."""
        csrf = CSRFProtection()
        ttp = CSRFValidationTTP(
            target_endpoints=['/api/users', '/api/posts'],
            csrf_protection=csrf
        )

        # Simulate all tests passing
        ttp.validation_results['test_details'] = [
            {'endpoint': '/api/users', 'test_type': 'without_token', 'result': 'PASS', 'status_code': 403},
            {'endpoint': '/api/users', 'test_type': 'with_valid_token', 'result': 'PASS', 'status_code': 200},
            {'endpoint': '/api/users', 'test_type': 'with_invalid_token', 'result': 'PASS', 'status_code': 403},
            {'endpoint': '/api/posts', 'test_type': 'without_token', 'result': 'PASS', 'status_code': 403},
            {'endpoint': '/api/posts', 'test_type': 'with_valid_token', 'result': 'PASS', 'status_code': 200},
            {'endpoint': '/api/posts', 'test_type': 'with_invalid_token', 'result': 'PASS', 'status_code': 403},
        ]

        summary = ttp.get_validation_summary()

        self.assertEqual(summary['endpoints_tested'], 2)
        self.assertEqual(summary['endpoints_protected'], 2)
        self.assertEqual(summary['endpoints_vulnerable'], 0)
        self.assertEqual(summary['overall_result'], 'SECURE')
        self.assertEqual(summary['protection_rate'], '2/2')

    def test_summary_some_vulnerable(self):
        """Test summary when some endpoints are vulnerable."""
        csrf = CSRFProtection()
        ttp = CSRFValidationTTP(
            target_endpoints=['/api/users', '/api/posts'],
            csrf_protection=csrf
        )

        # Simulate /api/posts being vulnerable (doesn't reject without token)
        ttp.validation_results['test_details'] = [
            {'endpoint': '/api/users', 'test_type': 'without_token', 'result': 'PASS', 'status_code': 403},
            {'endpoint': '/api/users', 'test_type': 'with_valid_token', 'result': 'PASS', 'status_code': 200},
            {'endpoint': '/api/posts', 'test_type': 'without_token', 'result': 'FAIL', 'status_code': 200},  # VULNERABLE!
            {'endpoint': '/api/posts', 'test_type': 'with_valid_token', 'result': 'PASS', 'status_code': 200},
        ]

        summary = ttp.get_validation_summary()

        self.assertEqual(summary['endpoints_tested'], 2)
        self.assertEqual(summary['endpoints_protected'], 1)
        self.assertEqual(summary['endpoints_vulnerable'], 1)
        self.assertEqual(summary['overall_result'], 'VULNERABLE')
        self.assertEqual(summary['protection_rate'], '1/2')


class TestCSRFValidationUIMode(unittest.TestCase):
    """Test that UI mode is not supported."""

    def test_ui_mode_execute_step_raises(self):
        """Test that execute_step raises NotImplementedError."""
        csrf = CSRFProtection()
        ttp = CSRFValidationTTP(
            target_endpoints=['/api/test'],
            csrf_protection=csrf
        )

        with self.assertRaises(NotImplementedError):
            ttp.execute_step(Mock(), {})

    def test_ui_mode_verify_result_raises(self):
        """Test that verify_result raises NotImplementedError."""
        csrf = CSRFProtection()
        ttp = CSRFValidationTTP(
            target_endpoints=['/api/test'],
            csrf_protection=csrf
        )

        with self.assertRaises(NotImplementedError):
            ttp.verify_result(Mock())


if __name__ == '__main__':
    unittest.main()
