import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add the scythe package to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.core.csrf import CSRFProtection
from scythe.journeys.actions import ApiRequestAction
from scythe.journeys.base import Journey, Step
from scythe.journeys.executor import JourneyExecutor
from scythe.ttps.web.request_flooding import RequestFloodingTTP


class TestApiRequestActionCSRFIntegration(unittest.TestCase):
    """Integration tests for ApiRequestAction with CSRF protection."""

    def setUp(self):
        self.csrf = CSRFProtection(
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )
        self.context = {
            'target_url': 'https://example.com',
            'csrf_protection': self.csrf,
            'csrf_token': 'initial_token'
        }
        self.mock_driver = Mock()

    @patch('scythe.journeys.actions.requests.Session')
    def test_api_request_injects_csrf_token(self, mock_session_class):
        """Test that ApiRequestAction injects CSRF token into headers."""
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.cookies = {'csrftoken': 'new_token'}
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Set up context with session
        self.context['requests_session'] = mock_session

        action = ApiRequestAction(
            method='POST',
            url='/api/items',
            body_json={'name': 'test'},
            expected_status=200
        )

        result = action.execute(self.mock_driver, self.context)

        # Verify request was made with CSRF header
        call_args = mock_session.request.call_args
        headers = call_args[1]['headers']
        self.assertIn('X-CSRF-Token', headers)
        self.assertEqual(headers['X-CSRF-Token'], 'initial_token')
        self.assertTrue(result)

    @patch('scythe.journeys.actions.requests.Session')
    def test_api_request_extracts_csrf_from_response(self, mock_session_class):
        """Test that ApiRequestAction extracts CSRF token from response."""
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.cookies = {'csrftoken': 'updated_token'}
        mock_session.request.return_value = mock_response

        # Mock session.cookies.get() to return the token
        mock_session.cookies = MagicMock()
        mock_session.cookies.get.return_value = 'updated_token'

        self.context['requests_session'] = mock_session

        action = ApiRequestAction(
            method='POST',
            url='/api/items',
            body_json={'name': 'test'},
            expected_status=200
        )

        action.execute(self.mock_driver, self.context)

        # Verify token was extracted and updated in context
        self.assertEqual(self.context['csrf_token'], 'updated_token')

    @patch('scythe.journeys.actions.requests.Session')
    @patch('scythe.journeys.actions.time.sleep')
    def test_api_request_retries_on_403_csrf_failure(self, mock_sleep, mock_session_class):
        """Test that ApiRequestAction retries on 403 with CSRF refresh."""
        mock_session = MagicMock()

        # First response: 403 (CSRF failure)
        mock_403_response = Mock()
        mock_403_response.status_code = 403
        mock_403_response.headers = {}

        # Refresh response: 200 with new token
        mock_refresh_response = Mock()
        mock_refresh_response.status_code = 200
        mock_refresh_response.cookies = {'csrftoken': 'refreshed_token'}
        mock_refresh_response.headers = {}

        # Retry response: 200 success
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.headers = {}
        mock_success_response.cookies = {'csrftoken': 'final_token'}

        # Mock session.request for the POST, and session.get for the refresh
        mock_session.request.side_effect = [mock_403_response, mock_success_response]
        mock_session.get.return_value = mock_refresh_response

        # Mock session.cookies.get() to return the refreshed token
        mock_session.cookies = MagicMock()
        mock_session.cookies.get.return_value = 'refreshed_token'

        self.context['requests_session'] = mock_session

        action = ApiRequestAction(
            method='POST',
            url='/api/items',
            body_json={'name': 'test'},
            expected_status=200
        )

        result = action.execute(self.mock_driver, self.context)

        # Verify that GET was called to refresh token
        mock_session.get.assert_called_once()

        # Verify request was retried (called twice)
        self.assertEqual(mock_session.request.call_count, 2)

        # Second call should have the refreshed token
        second_call_headers = mock_session.request.call_args_list[1][1]['headers']
        self.assertEqual(second_call_headers['X-CSRF-Token'], 'refreshed_token')

        self.assertTrue(result)

    @patch('scythe.journeys.actions.requests.Session')
    def test_api_request_no_csrf_injection_for_get(self, mock_session_class):
        """Test that CSRF token is not injected for GET requests."""
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.cookies = {}
        mock_session.request.return_value = mock_response

        self.context['requests_session'] = mock_session

        action = ApiRequestAction(
            method='GET',
            url='/api/items',
            expected_status=200
        )

        action.execute(self.mock_driver, self.context)

        # Verify request was made WITHOUT CSRF header
        call_args = mock_session.request.call_args
        headers = call_args[1]['headers']
        self.assertNotIn('X-CSRF-Token', headers or {})

    @patch('scythe.journeys.actions.requests.Session')
    def test_api_request_without_csrf_protection(self, mock_session_class):
        """Test ApiRequestAction works normally without CSRF protection."""
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.cookies = {}
        mock_session.request.return_value = mock_response

        # Context without CSRF protection
        context = {
            'target_url': 'https://example.com',
            'requests_session': mock_session
        }

        action = ApiRequestAction(
            method='POST',
            url='/api/items',
            body_json={'name': 'test'},
            expected_status=200
        )

        result = action.execute(self.mock_driver, context)

        # Should still work without CSRF
        self.assertTrue(result)


class TestJourneyCSRFIntegration(unittest.TestCase):
    """Integration tests for Journey with CSRF protection."""

    def test_journey_initialization_with_csrf(self):
        """Test Journey can be initialized with CSRF protection."""
        csrf = CSRFProtection(
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )

        journey = Journey(
            name="Test Journey",
            description="Test with CSRF",
            csrf_protection=csrf
        )

        self.assertIsNotNone(journey.csrf_protection)
        self.assertEqual(journey.csrf_protection.cookie_name, 'csrftoken')

    @patch('scythe.journeys.executor.requests.Session')
    def test_journey_executor_sets_csrf_in_context(self, mock_session_class):
        """Test JourneyExecutor sets CSRF protection in context."""
        csrf = CSRFProtection(
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )

        journey = Journey(
            name="Test Journey",
            description="Test with CSRF",
            csrf_protection=csrf
        )

        # Create a mock journey execute to capture context
        original_execute = journey.execute
        captured_context = {}

        def mock_execute(driver, target_url):
            captured_context.update(journey.context)
            return {'success': True, 'steps': []}

        journey.execute = mock_execute

        executor = JourneyExecutor(
            journey=journey,
            target_url='https://example.com',
            mode='API'
        )

        try:
            executor.run()
        except:
            pass  # Ignore errors, we just want to check context

        # Verify CSRF protection was set in context
        self.assertIn('csrf_protection', journey.context)
        self.assertIsInstance(journey.context['csrf_protection'], CSRFProtection)


class TestRequestFloodingCSRFIntegration(unittest.TestCase):
    """Integration tests for RequestFloodingTTP with CSRF protection."""

    def test_request_flooding_initialization_with_csrf(self):
        """Test RequestFloodingTTP can be initialized with CSRF protection."""
        csrf = CSRFProtection(
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )

        ttp = RequestFloodingTTP(
            target_endpoints=['/api/test'],
            request_count=10,
            http_method='POST',
            execution_mode='api',
            csrf_protection=csrf
        )

        self.assertIsNotNone(ttp.csrf_protection)
        self.assertEqual(ttp.csrf_protection.cookie_name, 'csrftoken')

    @patch('scythe.ttps.web.request_flooding.time.sleep')
    def test_request_flooding_injects_csrf_in_requests(self, mock_sleep):
        """Test RequestFloodingTTP injects CSRF token in flooding requests."""
        csrf = CSRFProtection(
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )

        ttp = RequestFloodingTTP(
            target_endpoints=['/api/test'],
            request_count=2,
            http_method='POST',
            execution_mode='api',
            csrf_protection=csrf
        )

        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.cookies = {'csrftoken': 'flood_token'}
        mock_session.request.return_value = mock_response

        context = {
            'target_url': 'https://example.com',
            'csrf_protection': csrf,
            'csrf_token': 'flood_token'
        }

        # Execute one step
        payload = {
            'endpoint': '/api/test',
            'data': {},
            'user_agent': 'Test',
            'delay': 0,
            'timeout': 10
        }

        response = ttp.execute_step_api(mock_session, payload, context)

        # Verify CSRF header was included
        call_args = mock_session.request.call_args
        if call_args:
            headers = call_args[1].get('headers', {})
            self.assertIn('X-CSRF-Token', headers)
            self.assertEqual(headers['X-CSRF-Token'], 'flood_token')


class TestCSRFBackwardCompatibility(unittest.TestCase):
    """Test that CSRF changes don't break existing functionality."""

    @patch('scythe.journeys.actions.requests.Session')
    def test_api_request_without_csrf_still_works(self, mock_session_class):
        """Test ApiRequestAction works without CSRF (backward compatibility)."""
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.cookies = {}
        mock_session.request.return_value = mock_response

        context = {
            'target_url': 'https://example.com',
            'requests_session': mock_session
            # No csrf_protection in context
        }

        action = ApiRequestAction(
            method='POST',
            url='/api/items',
            body_json={'name': 'test'},
            expected_status=200
        )

        result = action.execute(Mock(), context)

        # Should work without CSRF
        self.assertTrue(result)
        mock_session.request.assert_called_once()

    def test_journey_without_csrf_still_works(self):
        """Test Journey works without CSRF (backward compatibility)."""
        journey = Journey(
            name="Test Journey",
            description="Test without CSRF"
            # No csrf_protection parameter
        )

        self.assertIsNone(journey.csrf_protection)

    def test_ttp_without_csrf_still_works(self):
        """Test TTP works without CSRF (backward compatibility)."""
        ttp = RequestFloodingTTP(
            target_endpoints=['/api/test'],
            request_count=10,
            execution_mode='api'
            # No csrf_protection parameter
        )

        self.assertIsNone(ttp.csrf_protection)


class TestCSRFWithDifferentFrameworks(unittest.TestCase):
    """Test CSRF integration with different framework patterns."""

    @patch('scythe.journeys.actions.requests.Session')
    def test_django_csrf_pattern(self, mock_session_class):
        """Test Django CSRF pattern in ApiRequestAction."""
        csrf = CSRFProtection(
            extract_from='cookie',
            cookie_name='csrftoken',
            header_name='X-CSRFToken'
        )

        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.cookies = {'csrftoken': 'django_csrf'}
        mock_session.request.return_value = mock_response

        context = {
            'target_url': 'https://example.com',
            'requests_session': mock_session,
            'csrf_protection': csrf,
            'csrf_token': 'django_csrf'
        }

        action = ApiRequestAction(
            method='POST',
            url='/api/items',
            body_json={'name': 'test'}
        )

        action.execute(Mock(), context)

        # Verify Django header name was used
        headers = mock_session.request.call_args[1]['headers']
        self.assertIn('X-CSRFToken', headers)

    @patch('scythe.journeys.actions.requests.Session')
    def test_laravel_csrf_pattern(self, mock_session_class):
        """Test Laravel CSRF pattern in ApiRequestAction."""
        csrf = CSRFProtection(
            extract_from='cookie',
            cookie_name='XSRF-TOKEN',
            header_name='X-XSRF-TOKEN'
        )

        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.cookies = {'XSRF-TOKEN': 'laravel_csrf'}
        mock_session.request.return_value = mock_response

        context = {
            'target_url': 'https://example.com',
            'requests_session': mock_session,
            'csrf_protection': csrf,
            'csrf_token': 'laravel_csrf'
        }

        action = ApiRequestAction(
            method='POST',
            url='/api/items',
            body_json={'name': 'test'}
        )

        action.execute(Mock(), context)

        # Verify Laravel header name was used
        headers = mock_session.request.call_args[1]['headers']
        self.assertIn('X-XSRF-TOKEN', headers)


if __name__ == '__main__':
    unittest.main()
