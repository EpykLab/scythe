import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add the scythe package to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.core.csrf import CSRFProtection


class TestCSRFProtectionInitialization(unittest.TestCase):
    """Test cases for CSRFProtection initialization."""

    def test_default_initialization(self):
        """Test CSRFProtection with default parameters."""
        csrf = CSRFProtection()
        self.assertEqual(csrf.extract_from, 'cookie')
        self.assertEqual(csrf.cookie_name, 'csrftoken')
        self.assertEqual(csrf.header_name, 'X-CSRF-Token')
        self.assertEqual(csrf.body_field, 'csrfToken')
        self.assertEqual(csrf.inject_into, 'header')
        self.assertIsNone(csrf.refresh_endpoint)
        self.assertTrue(csrf.auto_extract)
        self.assertTrue(csrf.retry_on_failure)
        self.assertEqual(csrf.required_for_methods, ['POST', 'PUT', 'PATCH', 'DELETE'])

    def test_custom_initialization(self):
        """Test CSRFProtection with custom parameters."""
        csrf = CSRFProtection(
            extract_from='header',
            cookie_name='custom-csrf',
            header_name='X-Custom-CSRF',
            body_field='_csrf',
            inject_into='body',
            refresh_endpoint='/api/refresh',
            auto_extract=False,
            retry_on_failure=False,
            required_for_methods=['POST', 'DELETE']
        )
        self.assertEqual(csrf.extract_from, 'header')
        self.assertEqual(csrf.cookie_name, 'custom-csrf')
        self.assertEqual(csrf.header_name, 'X-Custom-CSRF')
        self.assertEqual(csrf.body_field, '_csrf')
        self.assertEqual(csrf.inject_into, 'body')
        self.assertEqual(csrf.refresh_endpoint, '/api/refresh')
        self.assertFalse(csrf.auto_extract)
        self.assertFalse(csrf.retry_on_failure)
        self.assertEqual(csrf.required_for_methods, ['POST', 'DELETE'])


class TestCSRFTokenExtraction(unittest.TestCase):
    """Test cases for CSRF token extraction."""

    def setUp(self):
        self.csrf = CSRFProtection(
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )
        self.context = {}

    def test_extract_from_cookie_in_response(self):
        """Test extracting CSRF token from response cookie."""
        mock_response = Mock()
        mock_response.cookies = {'csrftoken': 'token123'}

        token = self.csrf.extract_token(response=mock_response, context=self.context)

        self.assertEqual(token, 'token123')
        self.assertEqual(self.context['csrf_token'], 'token123')

    def test_extract_from_cookie_in_session(self):
        """Test extracting CSRF token from session cookies."""
        mock_session = Mock()
        mock_session.cookies = MagicMock()
        mock_session.cookies.get.return_value = 'session_token'

        token = self.csrf.extract_token(session=mock_session, context=self.context)

        self.assertEqual(token, 'session_token')
        self.assertEqual(self.context['csrf_token'], 'session_token')

    def test_extract_from_header(self):
        """Test extracting CSRF token from response header."""
        csrf = CSRFProtection(extract_from='header', header_name='X-CSRF-Token')
        mock_response = Mock()
        mock_response.headers = {'X-CSRF-Token': 'header_token'}

        token = csrf.extract_token(response=mock_response, context=self.context)

        self.assertEqual(token, 'header_token')
        self.assertEqual(self.context['csrf_token'], 'header_token')

    def test_extract_from_json_body(self):
        """Test extracting CSRF token from JSON response body."""
        csrf = CSRFProtection(extract_from='body', body_field='csrfToken')
        mock_response = Mock()
        mock_response.json.return_value = {'csrfToken': 'body_token', 'other': 'data'}

        token = csrf.extract_token(response=mock_response, context=self.context)

        self.assertEqual(token, 'body_token')
        self.assertEqual(self.context['csrf_token'], 'body_token')

    def test_extract_token_not_found(self):
        """Test extraction when token is not found."""
        mock_response = Mock()
        mock_response.cookies = {}

        token = self.csrf.extract_token(response=mock_response, context=self.context)

        self.assertIsNone(token)

    def test_extract_from_body_invalid_json(self):
        """Test extraction from body when JSON parsing fails."""
        csrf = CSRFProtection(extract_from='body', body_field='csrfToken')
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")

        token = csrf.extract_token(response=mock_response, context=self.context)

        self.assertIsNone(token)


class TestCSRFTokenInjection(unittest.TestCase):
    """Test cases for CSRF token injection."""

    def setUp(self):
        self.csrf = CSRFProtection(
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )
        self.context = {'csrf_token': 'test_token'}

    def test_inject_into_header(self):
        """Test injecting CSRF token into request headers."""
        headers = {'Content-Type': 'application/json'}

        updated_headers, updated_data = self.csrf.inject_token(
            headers=headers,
            method='POST',
            context=self.context
        )

        self.assertEqual(updated_headers['X-CSRF-Token'], 'test_token')
        self.assertEqual(updated_headers['Content-Type'], 'application/json')

    def test_inject_into_body(self):
        """Test injecting CSRF token into request body."""
        csrf = CSRFProtection(inject_into='body', body_field='_csrf')
        csrf._current_token = 'test_token'
        data = {'username': 'test'}

        updated_headers, updated_data = csrf.inject_token(
            data=data,
            method='POST',
            context={'csrf_token': 'test_token'}
        )

        self.assertEqual(updated_data['_csrf'], 'test_token')
        self.assertEqual(updated_data['username'], 'test')

    def test_inject_not_required_for_get(self):
        """Test that CSRF token is not injected for GET requests."""
        headers = {}

        updated_headers, updated_data = self.csrf.inject_token(
            headers=headers,
            method='GET',
            context=self.context
        )

        self.assertNotIn('X-CSRF-Token', updated_headers)

    def test_inject_required_for_post(self):
        """Test that CSRF token is injected for POST requests."""
        headers = {}

        updated_headers, updated_data = self.csrf.inject_token(
            headers=headers,
            method='POST',
            context=self.context
        )

        self.assertIn('X-CSRF-Token', updated_headers)

    def test_inject_required_for_custom_methods(self):
        """Test custom required_for_methods configuration."""
        csrf = CSRFProtection(required_for_methods=['POST', 'DELETE'])
        csrf._current_token = 'test_token'

        # Should inject for POST
        headers, _ = csrf.inject_token(headers={}, method='POST', context={'csrf_token': 'test_token'})
        self.assertIn('X-CSRF-Token', headers)

        # Should inject for DELETE
        headers, _ = csrf.inject_token(headers={}, method='DELETE', context={'csrf_token': 'test_token'})
        self.assertIn('X-CSRF-Token', headers)

        # Should NOT inject for PUT (not in list)
        headers, _ = csrf.inject_token(headers={}, method='PUT', context={'csrf_token': 'test_token'})
        self.assertNotIn('X-CSRF-Token', headers)

    def test_inject_without_token(self):
        """Test injection when no token is available."""
        headers = {}

        updated_headers, updated_data = self.csrf.inject_token(
            headers=headers,
            method='POST',
            context={}  # No token in context
        )

        self.assertNotIn('X-CSRF-Token', updated_headers)

    def test_inject_creates_headers_dict(self):
        """Test that injection creates headers dict if None."""
        updated_headers, _ = self.csrf.inject_token(
            headers=None,
            method='POST',
            context=self.context
        )

        self.assertIsNotNone(updated_headers)
        self.assertEqual(updated_headers['X-CSRF-Token'], 'test_token')


class TestCSRFTokenRefresh(unittest.TestCase):
    """Test cases for CSRF token refresh."""

    def setUp(self):
        self.csrf = CSRFProtection(
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )
        self.mock_session = Mock()
        self.context = {}

    @patch('scythe.core.csrf.logger')
    def test_refresh_with_dedicated_endpoint(self, mock_logger):
        """Test refreshing token using dedicated refresh endpoint."""
        csrf = CSRFProtection(refresh_endpoint='/api/csrf-token')
        mock_response = Mock()
        mock_response.cookies = {'csrftoken': 'new_token'}

        # Mock session.cookies.get() for extract_token
        mock_session_cookies = MagicMock()
        mock_session_cookies.get.return_value = 'new_token'
        self.mock_session.cookies = mock_session_cookies
        self.mock_session.get.return_value = mock_response

        token = csrf.refresh_token(
            session=self.mock_session,
            base_url='https://example.com',
            context=self.context
        )

        self.assertEqual(token, 'new_token')
        self.mock_session.get.assert_called_once_with('https://example.com/api/csrf-token', timeout=10)
        self.assertEqual(self.context['csrf_token'], 'new_token')

    @patch('scythe.core.csrf.logger')
    def test_refresh_without_endpoint_uses_base_url(self, mock_logger):
        """Test refreshing token by hitting base URL when no endpoint configured."""
        # No refresh_endpoint configured
        mock_response = Mock()
        mock_response.cookies = {'csrftoken': 'refreshed_token'}

        # Mock session.cookies.get() for extract_token
        mock_session_cookies = MagicMock()
        mock_session_cookies.get.return_value = 'refreshed_token'
        self.mock_session.cookies = mock_session_cookies
        self.mock_session.get.return_value = mock_response

        token = self.csrf.refresh_token(
            session=self.mock_session,
            base_url='https://example.com',
            context=self.context
        )

        self.assertEqual(token, 'refreshed_token')
        # Should hit base URL directly
        self.mock_session.get.assert_called_once_with('https://example.com', timeout=10)

    @patch('scythe.core.csrf.logger')
    def test_refresh_handles_request_failure(self, mock_logger):
        """Test refresh handles request failures gracefully."""
        self.mock_session.get.side_effect = Exception("Network error")

        token = self.csrf.refresh_token(
            session=self.mock_session,
            base_url='https://example.com',
            context=self.context
        )

        self.assertIsNone(token)

    @patch('scythe.core.csrf.logger')
    def test_refresh_with_absolute_endpoint_url(self, mock_logger):
        """Test refresh with absolute URL endpoint."""
        csrf = CSRFProtection(refresh_endpoint='https://api.example.com/csrf')
        mock_response = Mock()
        mock_response.cookies = {'csrftoken': 'abs_token'}
        self.mock_session.get.return_value = mock_response

        token = csrf.refresh_token(
            session=self.mock_session,
            base_url='https://example.com',
            context=self.context
        )

        # Should use absolute URL directly
        self.mock_session.get.assert_called_once_with('https://api.example.com/csrf', timeout=10)


class TestCSRFFailureHandling(unittest.TestCase):
    """Test cases for CSRF failure handling."""

    def setUp(self):
        self.csrf = CSRFProtection(cookie_name='csrftoken')
        self.mock_session = Mock()
        self.context = {}

    def test_should_retry_on_403(self):
        """Test should_retry returns True for 403 status."""
        mock_response = Mock()
        mock_response.status_code = 403

        self.assertTrue(self.csrf.should_retry(mock_response))

    def test_should_retry_on_419(self):
        """Test should_retry returns True for 419 status."""
        mock_response = Mock()
        mock_response.status_code = 419

        self.assertTrue(self.csrf.should_retry(mock_response))

    def test_should_not_retry_on_other_status(self):
        """Test should_retry returns False for other status codes."""
        for status_code in [200, 400, 401, 404, 500]:
            mock_response = Mock()
            mock_response.status_code = status_code

            self.assertFalse(self.csrf.should_retry(mock_response),
                           f"should_retry should be False for {status_code}")

    @patch.object(CSRFProtection, 'refresh_token')
    def test_handle_csrf_failure_403(self, mock_refresh):
        """Test handling 403 CSRF failure."""
        mock_refresh.return_value = 'new_token'
        mock_response = Mock()
        mock_response.status_code = 403

        result = self.csrf.handle_csrf_failure(
            response=mock_response,
            session=self.mock_session,
            base_url='https://example.com',
            context=self.context
        )

        self.assertTrue(result)
        mock_refresh.assert_called_once()

    @patch.object(CSRFProtection, 'refresh_token')
    def test_handle_csrf_failure_returns_false_on_other_status(self, mock_refresh):
        """Test handle_csrf_failure returns False for non-CSRF status codes."""
        mock_response = Mock()
        mock_response.status_code = 200

        result = self.csrf.handle_csrf_failure(
            response=mock_response,
            session=self.mock_session,
            base_url='https://example.com',
            context=self.context
        )

        self.assertFalse(result)
        mock_refresh.assert_not_called()


class TestCSRFGetToken(unittest.TestCase):
    """Test cases for getting current CSRF token."""

    def test_get_token_from_context(self):
        """Test getting token from context."""
        csrf = CSRFProtection()
        context = {'csrf_token': 'context_token'}

        token = csrf.get_token(context)

        self.assertEqual(token, 'context_token')

    def test_get_token_from_internal_state(self):
        """Test getting token from internal state when not in context."""
        csrf = CSRFProtection()
        csrf._current_token = 'internal_token'

        token = csrf.get_token({})

        self.assertEqual(token, 'internal_token')

    def test_get_token_priority(self):
        """Test that context token takes priority over internal state."""
        csrf = CSRFProtection()
        csrf._current_token = 'internal_token'
        context = {'csrf_token': 'context_token'}

        token = csrf.get_token(context)

        self.assertEqual(token, 'context_token')

    def test_get_token_returns_none(self):
        """Test getting token when none exists."""
        csrf = CSRFProtection()

        token = csrf.get_token({})

        self.assertIsNone(token)


class TestCSRFFrameworkPatterns(unittest.TestCase):
    """Test cases for common framework CSRF patterns."""

    def test_django_pattern(self):
        """Test Django CSRF pattern (csrftoken cookie -> X-CSRFToken header)."""
        csrf = CSRFProtection(
            extract_from='cookie',
            cookie_name='csrftoken',
            header_name='X-CSRFToken',
            inject_into='header'
        )

        # Extract from Django response
        mock_response = Mock()
        mock_response.cookies = {'csrftoken': 'django_token'}
        context = {}
        token = csrf.extract_token(response=mock_response, context=context)
        self.assertEqual(token, 'django_token')

        # Inject into request
        headers, _ = csrf.inject_token(headers={}, method='POST', context=context)
        self.assertEqual(headers['X-CSRFToken'], 'django_token')

    def test_laravel_pattern(self):
        """Test Laravel CSRF pattern (XSRF-TOKEN cookie -> X-XSRF-TOKEN header)."""
        csrf = CSRFProtection(
            extract_from='cookie',
            cookie_name='XSRF-TOKEN',
            header_name='X-XSRF-TOKEN',
            inject_into='header'
        )

        # Extract
        mock_response = Mock()
        mock_response.cookies = {'XSRF-TOKEN': 'laravel_token'}
        context = {}
        token = csrf.extract_token(response=mock_response, context=context)
        self.assertEqual(token, 'laravel_token')

        # Inject
        headers, _ = csrf.inject_token(headers={}, method='POST', context=context)
        self.assertEqual(headers['X-XSRF-TOKEN'], 'laravel_token')

    def test_custom_host_cookie_pattern(self):
        """Test custom __Host-csrf_ cookie pattern."""
        csrf = CSRFProtection(
            extract_from='cookie',
            cookie_name='__Host-csrf_',
            header_name='X-CSRF-Token',
            inject_into='header'
        )

        # Extract
        mock_session = Mock()
        mock_session.cookies = MagicMock()
        mock_session.cookies.get.return_value = 'host_token'
        context = {}
        token = csrf.extract_token(session=mock_session, context=context)
        self.assertEqual(token, 'host_token')

        # Inject
        headers, _ = csrf.inject_token(headers={}, method='POST', context=context)
        self.assertEqual(headers['X-CSRF-Token'], 'host_token')


class TestCSRFRepr(unittest.TestCase):
    """Test cases for CSRFProtection string representation."""

    def test_repr(self):
        """Test __repr__ method."""
        csrf = CSRFProtection(
            extract_from='cookie',
            cookie_name='test-csrf',
            header_name='X-Test-CSRF'
        )

        repr_str = repr(csrf)

        self.assertIn('CSRFProtection', repr_str)
        self.assertIn('cookie', repr_str)
        self.assertIn('test-csrf', repr_str)
        self.assertIn('X-Test-CSRF', repr_str)


if __name__ == '__main__':
    unittest.main()
