"""
Tests for LoginBruteforceTTP with CSRF protection.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import requests

from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.core.csrf import CSRFProtection


class TestLoginBruteforceCSRF(unittest.TestCase):
    """Test LoginBruteforceTTP with CSRF protection."""

    def setUp(self):
        """Set up test fixtures."""
        self.csrf = CSRFProtection(
            cookie_name='csrftoken',
            header_name='X-CSRF-Token'
        )

        def simple_generator():
            yield from ['password1', 'password2', 'password3']

        self.ttp = LoginBruteforceTTP(
            payload_generator=simple_generator,
            username='testuser',
            execution_mode='api',
            api_endpoint='/api/login',
            csrf_protection=self.csrf
        )

    def test_initialization_with_csrf(self):
        """Test that TTP initializes with CSRF protection."""
        self.assertIsNotNone(self.ttp.csrf_protection)
        self.assertEqual(self.ttp.csrf_protection.cookie_name, 'csrftoken')
        self.assertEqual(self.ttp.csrf_protection.header_name, 'X-CSRF-Token')

    def test_execute_step_api_injects_csrf_token(self):
        """Test that execute_step_api injects CSRF token into request."""
        # Mock session
        mock_session = Mock(spec=requests.Session)
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_response.text = '{"success": true}'

        # Mock session.cookies
        mock_session_cookies = MagicMock()
        mock_session_cookies.get.return_value = 'test-csrf-token'
        mock_session.cookies = mock_session_cookies

        mock_session.post.return_value = mock_response

        # Context with CSRF protection and existing token
        context = {
            'target_url': 'https://test.com',
            'csrf_protection': self.csrf,
            'csrf_token': 'existing-token-123'
        }

        # Execute
        response = self.ttp.execute_step_api(mock_session, 'password1', context)

        # Verify post was called
        self.assertTrue(mock_session.post.called)
        call_args = mock_session.post.call_args

        # Verify CSRF token was injected into headers
        headers = call_args.kwargs.get('headers', {})
        self.assertIn('X-CSRF-Token', headers)
        self.assertEqual(headers['X-CSRF-Token'], 'existing-token-123')

        # Verify response
        self.assertEqual(response.status_code, 200)

    def test_execute_step_api_extracts_csrf_from_response(self):
        """Test that execute_step_api extracts CSRF token from response."""
        # Mock session
        mock_session = Mock(spec=requests.Session)
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 401  # Failed login
        mock_response.text = '{"error": "invalid credentials"}'

        # Mock session.cookies with CSRF token
        mock_session_cookies = MagicMock()
        mock_session_cookies.get.return_value = 'new-csrf-token-from-response'
        mock_session.cookies = mock_session_cookies

        mock_session.post.return_value = mock_response

        # Context
        context = {
            'target_url': 'https://test.com',
            'csrf_protection': self.csrf
        }

        # Execute
        response = self.ttp.execute_step_api(mock_session, 'wrong_password', context)

        # Verify token was extracted and stored in context
        self.assertIn('csrf_token', context)
        self.assertEqual(context['csrf_token'], 'new-csrf-token-from-response')

    def test_execute_step_api_without_csrf(self):
        """Test that execute_step_api works without CSRF protection."""
        # Create TTP without CSRF
        def simple_generator():
            yield from ['test123']

        ttp_no_csrf = LoginBruteforceTTP(
            payload_generator=simple_generator,
            username='user',
            execution_mode='api',
            api_endpoint='/login'
            # No csrf_protection parameter
        )

        # Mock session
        mock_session = Mock(spec=requests.Session)
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200
        mock_session.post.return_value = mock_response

        # Context without CSRF
        context = {
            'target_url': 'https://test.com'
        }

        # Execute - should work without errors
        response = ttp_no_csrf.execute_step_api(mock_session, 'test123', context)

        # Verify post was called
        self.assertTrue(mock_session.post.called)
        call_args = mock_session.post.call_args

        # Verify no CSRF header was added
        headers = call_args.kwargs.get('headers')
        if headers:
            self.assertNotIn('X-CSRF-Token', headers)

    def test_csrf_with_custom_field_names(self):
        """Test CSRF with custom username/password field names."""
        csrf = CSRFProtection(
            cookie_name='__Host-csrf_',
            header_name='X-CSRF-Token'
        )

        def simple_generator():
            yield from ['pass123']

        ttp = LoginBruteforceTTP(
            payload_generator=simple_generator,
            username='user@example.com',
            execution_mode='api',
            api_endpoint='/auth/login',
            username_field='email',  # Custom field
            password_field='pass',   # Custom field
            csrf_protection=csrf
        )

        # Mock session
        mock_session = Mock(spec=requests.Session)
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200

        mock_session_cookies = MagicMock()
        mock_session_cookies.get.return_value = 'csrf-123'
        mock_session.cookies = mock_session_cookies
        mock_session.post.return_value = mock_response

        context = {
            'target_url': 'https://test.com',
            'csrf_protection': csrf,
            'csrf_token': 'token-abc'
        }

        # Execute
        ttp.execute_step_api(mock_session, 'pass123', context)

        # Verify the custom field names were used
        call_args = mock_session.post.call_args
        body = call_args.kwargs.get('json', {})

        self.assertIn('email', body)
        self.assertIn('pass', body)
        self.assertEqual(body['email'], 'user@example.com')
        self.assertEqual(body['pass'], 'pass123')

    def test_csrf_injection_in_body(self):
        """Test CSRF token injection into request body instead of header."""
        csrf = CSRFProtection(
            extract_from='cookie',
            cookie_name='csrftoken',
            body_field='_csrf',
            inject_into='body'  # Inject into body, not header
        )

        def simple_generator():
            yield from ['password']

        ttp = LoginBruteforceTTP(
            payload_generator=simple_generator,
            username='user',
            execution_mode='api',
            api_endpoint='/login',
            csrf_protection=csrf
        )

        # Mock session
        mock_session = Mock(spec=requests.Session)
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 200

        mock_session_cookies = MagicMock()
        mock_session_cookies.get.return_value = 'token-xyz'
        mock_session.cookies = mock_session_cookies
        mock_session.post.return_value = mock_response

        context = {
            'target_url': 'https://test.com',
            'csrf_protection': csrf,
            'csrf_token': 'my-csrf-token'
        }

        # Execute
        ttp.execute_step_api(mock_session, 'password', context)

        # Verify CSRF was injected into body
        call_args = mock_session.post.call_args
        body = call_args.kwargs.get('json', {})

        self.assertIn('_csrf', body)
        self.assertEqual(body['_csrf'], 'my-csrf-token')

        # Verify it's NOT in headers
        headers = call_args.kwargs.get('headers')
        if headers:
            self.assertNotIn('X-CSRF-Token', headers)


if __name__ == '__main__':
    unittest.main()
