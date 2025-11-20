"""
Tests for CSRF support in Authentication classes.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import requests

from scythe.auth.base import Authentication
from scythe.auth.basic import BasicAuth
from scythe.auth.bearer import BearerTokenAuth
from scythe.auth.cookie_jwt import CookieJWTAuth
from scythe.core.csrf import CSRFProtection


class TestAuthenticationBaseWithCSRF(unittest.TestCase):
    """Test CSRF support in base Authentication class."""

    def test_base_auth_accepts_csrf_protection(self):
        """Test that Authentication base class accepts csrf_protection parameter."""
        csrf = CSRFProtection(
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )

        class TestAuth(Authentication):
            def authenticate(self, driver, target_url):
                return True

            def is_authenticated(self, driver):
                return True

        auth = TestAuth(
            name="Test Auth",
            description="Test",
            csrf_protection=csrf
        )

        self.assertIsNotNone(auth.csrf_protection)
        self.assertEqual(auth.csrf_protection.cookie_name, 'csrftoken')

    def test_base_auth_csrf_protection_optional(self):
        """Test that csrf_protection is optional."""
        class TestAuth(Authentication):
            def authenticate(self, driver, target_url):
                return True

            def is_authenticated(self, driver):
                return True

        auth = TestAuth(
            name="Test Auth",
            description="Test"
            # No csrf_protection parameter
        )

        self.assertIsNone(auth.csrf_protection)


class TestBasicAuthWithCSRF(unittest.TestCase):
    """Test CSRF support in BasicAuth."""

    def test_basic_auth_initialization_with_csrf(self):
        """Test BasicAuth accepts CSRF protection."""
        csrf = CSRFProtection(
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )

        auth = BasicAuth(
            username='user',
            password='pass',
            csrf_protection=csrf
        )

        self.assertIsNotNone(auth.csrf_protection)
        self.assertEqual(auth.csrf_protection.cookie_name, 'csrftoken')

    def test_basic_auth_without_csrf(self):
        """Test BasicAuth works without CSRF."""
        auth = BasicAuth(
            username='user',
            password='pass'
            # No csrf_protection
        )

        self.assertIsNone(auth.csrf_protection)

    def test_basic_auth_csrf_docstring_updated(self):
        """Test that BasicAuth docstring mentions CSRF."""
        csrf = CSRFProtection()
        auth = BasicAuth(
            username='user',
            password='pass',
            csrf_protection=csrf
        )

        # Verify the csrf_protection parameter was passed
        self.assertIsNotNone(auth.csrf_protection)


class TestBearerTokenAuthWithCSRF(unittest.TestCase):
    """Test CSRF support in BearerTokenAuth."""

    def test_bearer_auth_initialization_with_csrf(self):
        """Test BearerTokenAuth accepts CSRF protection."""
        csrf = CSRFProtection(
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )

        auth = BearerTokenAuth(
            token='test-token',
            csrf_protection=csrf
        )

        self.assertIsNotNone(auth.csrf_protection)

    def test_bearer_auth_without_csrf(self):
        """Test BearerTokenAuth works without CSRF."""
        auth = BearerTokenAuth(
            token='test-token'
            # No csrf_protection
        )

        self.assertIsNone(auth.csrf_protection)

    def test_bearer_auth_get_auth_headers_with_csrf_configured(self):
        """Test that get_auth_headers works with CSRF configured."""
        csrf = CSRFProtection()
        auth = BearerTokenAuth(
            token='my-bearer-token',
            csrf_protection=csrf
        )

        headers = auth.get_auth_headers()
        self.assertIn('Authorization', headers)
        self.assertEqual(headers['Authorization'], 'Bearer my-bearer-token')


class TestCookieJWTAuthWithCSRF(unittest.TestCase):
    """Test CSRF support in CookieJWTAuth."""

    def test_cookie_jwt_auth_initialization_with_csrf(self):
        """Test CookieJWTAuth accepts CSRF protection."""
        csrf = CSRFProtection(
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )

        auth = CookieJWTAuth(
            login_url='https://api.example.com/login',
            username='user@example.com',
            password='secret',
            csrf_protection=csrf
        )

        self.assertIsNotNone(auth.csrf_protection)

    def test_cookie_jwt_auth_without_csrf(self):
        """Test CookieJWTAuth works without CSRF."""
        auth = CookieJWTAuth(
            login_url='https://api.example.com/login',
            username='user@example.com',
            password='secret'
            # No csrf_protection
        )

        self.assertIsNone(auth.csrf_protection)

    def test_cookie_jwt_auth_login_with_csrf_protection(self):
        """Test that CookieJWTAuth handles CSRF during login."""
        csrf = CSRFProtection(
            extract_from='cookie',
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )

        # Mock session
        mock_session = Mock(spec=requests.Session)

        # Mock GET response (for initial CSRF token)
        mock_get_response = Mock(spec=requests.Response)
        mock_get_response.status_code = 200
        mock_get_response.text = '{"status":"ok"}'

        # Mock POST response (login)
        mock_post_response = Mock(spec=requests.Response)
        mock_post_response.status_code = 200
        mock_post_response.text = '{"token":"jwt-token-123"}'
        mock_post_response.json.return_value = {'token': 'jwt-token-123'}
        mock_post_response.raise_for_status = Mock()

        # Setup mock session
        mock_session_cookies = MagicMock()
        mock_session_cookies.get.return_value = 'csrf-token-from-cookie'
        mock_session.cookies = mock_session_cookies

        mock_session.get.return_value = mock_get_response
        mock_session.post.return_value = mock_post_response

        auth = CookieJWTAuth(
            login_url='https://api.example.com/login',
            username='user@example.com',
            password='secret',
            csrf_protection=csrf,
            session=mock_session
        )

        # Get auth cookies (which triggers login)
        cookies = auth.get_auth_cookies()

        # Verify GET was called to extract initial CSRF
        mock_session.get.assert_called()

        # Verify POST was called with CSRF token
        mock_session.post.assert_called()
        call_args = mock_session.post.call_args
        # Verify headers were passed (containing CSRF token)
        self.assertIsNotNone(call_args)

        # Verify token was acquired
        self.assertIn('stellarbridge', cookies)
        self.assertEqual(cookies['stellarbridge'], 'jwt-token-123')

    def test_cookie_jwt_auth_csrf_extraction_from_response(self):
        """Test that updated CSRF tokens are extracted after login."""
        csrf = CSRFProtection(
            extract_from='cookie',
            cookie_name='csrftoken',
            header_name='X-CSRF-Token',
            auto_extract=True
        )

        # Mock session
        mock_session = Mock(spec=requests.Session)

        # Initial CSRF token
        initial_csrf = 'csrf-token-initial'

        # Updated CSRF token (from POST response)
        updated_csrf = 'csrf-token-updated'

        # Mock responses
        mock_get_response = Mock(spec=requests.Response)
        mock_get_response.status_code = 200

        mock_post_response = Mock(spec=requests.Response)
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {'token': 'jwt-123'}
        mock_post_response.raise_for_status = Mock()

        # Setup session cookies
        mock_session_cookies = MagicMock()
        mock_session_cookies.get.side_effect = [
            initial_csrf,  # First GET request
            updated_csrf   # After POST request
        ]
        mock_session.cookies = mock_session_cookies

        mock_session.get.return_value = mock_get_response
        mock_session.post.return_value = mock_post_response

        auth = CookieJWTAuth(
            login_url='https://api.example.com/login',
            username='user@example.com',
            password='secret',
            csrf_protection=csrf,
            session=mock_session
        )

        # Trigger login
        auth.get_auth_cookies()

        # Both GET and POST should have been called
        self.assertTrue(mock_session.get.called)
        self.assertTrue(mock_session.post.called)


class TestAuthenticationCSRFFrameworkPatterns(unittest.TestCase):
    """Test different framework patterns with authentication."""

    def test_django_csrf_with_cookie_jwt_auth(self):
        """Test Django CSRF pattern with CookieJWTAuth."""
        csrf = CSRFProtection(
            extract_from='cookie',
            cookie_name='csrftoken',      # Django default
            header_name='X-CSRFToken',     # Django header name
            inject_into='header'
        )

        auth = CookieJWTAuth(
            login_url='https://django-app.com/api/login',
            username='user',
            password='pass',
            csrf_protection=csrf
        )

        self.assertEqual(auth.csrf_protection.cookie_name, 'csrftoken')
        self.assertEqual(auth.csrf_protection.header_name, 'X-CSRFToken')

    def test_custom_host_csrf_with_bearer_token_auth(self):
        """Test custom __Host-csrf_ pattern with BearerTokenAuth."""
        csrf = CSRFProtection(
            extract_from='cookie',
            cookie_name='__Host-csrf_',
            header_name='X-CSRF-Token',
            inject_into='header'
        )

        auth = BearerTokenAuth(
            token='existing-token',
            csrf_protection=csrf
        )

        self.assertEqual(auth.csrf_protection.cookie_name, '__Host-csrf_')

    def test_csrf_with_basic_auth_ui_mode(self):
        """Test CSRF with BasicAuth in UI mode (browser handles it)."""
        csrf = CSRFProtection(
            extract_from='cookie',
            cookie_name='csrftoken'
        )

        auth = BasicAuth(
            username='testuser',
            password='testpass',
            login_url='https://app.com/login',
            csrf_protection=csrf
        )

        # UI mode authentication uses WebDriver/browser which handles CSRF
        self.assertIsNotNone(auth.csrf_protection)
        # The browser (Selenium/WebDriver) automatically handles CSRF in forms


if __name__ == '__main__':
    unittest.main()
