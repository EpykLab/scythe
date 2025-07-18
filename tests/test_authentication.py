import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the scythe package to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.auth.base import Authentication, AuthenticationError
from scythe.auth.basic import BasicAuth
from scythe.auth.bearer import BearerTokenAuth
from scythe.core.ttp import TTP
from scythe.core.executor import TTPExecutor


class MockAuthentication(Authentication):
    """Mock authentication for testing."""
    
    def __init__(self, name: str, description: str, auth_success: bool = True):
        super().__init__(name, description)
        self.auth_success = auth_success
        self.auth_called = False
        self.is_auth_called = False
        self.logout_called = False
    
    def authenticate(self, driver, target_url):
        self.auth_called = True
        if self.auth_success:
            self.authenticated = True
        return self.auth_success
    
    def is_authenticated(self, driver):
        self.is_auth_called = True
        return self.authenticated


class MockTTP(TTP):
    """Mock TTP for testing authentication integration."""
    
    def __init__(self, name: str, description: str, expected_result: bool = True, authentication=None):
        super().__init__(name, description, expected_result, authentication)
        self.payloads_yielded = []
        self.steps_executed = []
        
    def get_payloads(self):
        payloads = ["test_payload_1", "test_payload_2"]
        self.payloads_yielded = payloads
        yield from payloads
    
    def execute_step(self, driver, payload):
        self.steps_executed.append(payload)
    
    def verify_result(self, driver):
        return True


class TestAuthenticationBase(unittest.TestCase):
    """Test cases for Authentication base class."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_driver.delete_all_cookies = Mock()
        self.mock_driver.execute_script = Mock()
    
    def test_authentication_initialization(self):
        """Test Authentication base class initialization."""
        auth = MockAuthentication("Test Auth", "Test Description")
        
        self.assertEqual(auth.name, "Test Auth")
        self.assertEqual(auth.description, "Test Description")
        self.assertFalse(auth.authenticated)
        self.assertEqual(auth.auth_data, {})
    
    def test_store_and_get_auth_data(self):
        """Test storing and retrieving auth data."""
        auth = MockAuthentication("Test Auth", "Test Description")
        
        auth.store_auth_data("test_key", "test_value")
        self.assertEqual(auth.get_auth_data("test_key"), "test_value")
        self.assertEqual(auth.get_auth_data("nonexistent", "default"), "default")
    
    def test_clear_auth_data(self):
        """Test clearing auth data."""
        auth = MockAuthentication("Test Auth", "Test Description")
        
        auth.store_auth_data("test_key", "test_value")
        auth.authenticated = True
        
        auth.clear_auth_data()
        
        self.assertEqual(auth.auth_data, {})
        self.assertFalse(auth.authenticated)
    
    def test_default_logout(self):
        """Test default logout implementation."""
        auth = MockAuthentication("Test Auth", "Test Description")
        auth.authenticated = True
        
        result = auth.logout(self.mock_driver)
        
        self.assertTrue(result)
        self.assertFalse(auth.authenticated)
        self.mock_driver.delete_all_cookies.assert_called_once()
        self.mock_driver.execute_script.assert_any_call("localStorage.clear();")
        self.mock_driver.execute_script.assert_any_call("sessionStorage.clear();")


class TestBasicAuth(unittest.TestCase):
    """Test cases for BasicAuth class."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_driver.current_url = "http://test.com/dashboard"
        self.mock_driver.page_source = "<html><body>Welcome to dashboard</body></html>"
        
        # Mock form elements
        self.mock_username_field = Mock()
        self.mock_username_field.is_displayed.return_value = True
        self.mock_username_field.is_enabled.return_value = True
        
        self.mock_password_field = Mock()
        self.mock_password_field.is_displayed.return_value = True
        self.mock_password_field.is_enabled.return_value = True
        
        self.mock_submit_button = Mock()
        self.mock_submit_button.is_displayed.return_value = True
        self.mock_submit_button.is_enabled.return_value = True
    
    def test_basic_auth_initialization(self):
        """Test BasicAuth initialization."""
        auth = BasicAuth("testuser", "testpass", login_url="http://test.com/login")
        
        self.assertEqual(auth.username, "testuser")
        self.assertEqual(auth.password, "testpass")
        self.assertEqual(auth.login_url, "http://test.com/login")
        self.assertIn("dashboard", auth.success_indicators)
        self.assertIn("error", auth.failure_indicators)
    
    @patch('time.sleep')
    def test_successful_authentication(self, mock_sleep):
        """Test successful basic authentication."""
        auth = BasicAuth("testuser", "testpass")
        
        # Mock finding form elements
        self.mock_driver.find_element.side_effect = [
            self.mock_username_field,  # username field
            self.mock_password_field,  # password field
            self.mock_submit_button    # submit button
        ]
        
        result = auth.authenticate(self.mock_driver, "http://test.com")
        
        self.assertTrue(result)
        self.assertTrue(auth.authenticated)
        self.mock_username_field.clear.assert_called_once()
        self.mock_username_field.send_keys.assert_called_with("testuser")
        self.mock_password_field.clear.assert_called_once()
        self.mock_password_field.send_keys.assert_called_with("testpass")
        self.mock_submit_button.click.assert_called_once()
    
    def test_authentication_failure_no_username_field(self):
        """Test authentication failure when username field not found."""
        auth = BasicAuth("testuser", "testpass")
        
        # Mock no username field found
        from selenium.common.exceptions import NoSuchElementException
        self.mock_driver.find_element.side_effect = NoSuchElementException()
        
        with self.assertRaises(AuthenticationError) as context:
            auth.authenticate(self.mock_driver, "http://test.com")
        
        self.assertIn("Could not find username field", str(context.exception))
    
    def test_is_authenticated_check(self):
        """Test is_authenticated method."""
        auth = BasicAuth("testuser", "testpass")
        
        # Test not authenticated
        auth.authenticated = False
        self.assertFalse(auth.is_authenticated(self.mock_driver))
        
        # Test authenticated with logout indicator
        auth.authenticated = True
        self.mock_driver.page_source = "<html><body><a href='/logout'>Logout</a></body></html>"
        self.mock_driver.current_url = "http://test.com/dashboard"
        self.assertTrue(auth.is_authenticated(self.mock_driver))
        
        # Test authenticated but on login page (session expired)
        auth.authenticated = True  # Still marked as authenticated internally
        self.mock_driver.current_url = "http://test.com/login"
        self.mock_driver.page_source = "<html><body>Please login</body></html>"
        self.assertFalse(auth.is_authenticated(self.mock_driver))


class TestBearerTokenAuth(unittest.TestCase):
    """Test cases for BearerTokenAuth class."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_driver.current_url = "http://test.com"
        self.mock_driver.page_source = '{"access_token": "test_token_123"}'
    
    def test_bearer_auth_with_existing_token(self):
        """Test BearerTokenAuth with pre-existing token."""
        auth = BearerTokenAuth(token="existing_token_123")
        
        self.assertTrue(auth.authenticated)
        self.assertEqual(auth.token, "existing_token_123")
        self.assertEqual(auth.get_auth_data('token'), "existing_token_123")
    
    def test_bearer_auth_initialization_no_token(self):
        """Test BearerTokenAuth initialization without token."""
        auth = BearerTokenAuth(
            token_url="http://test.com/auth",
            username="testuser",
            password="testpass"
        )
        
        self.assertFalse(auth.authenticated)
        self.assertIsNone(auth.token)
        self.assertEqual(auth.token_url, "http://test.com/auth")
    
    def test_get_auth_headers(self):
        """Test getting authentication headers."""
        auth = BearerTokenAuth(token="test_token_123")
        
        headers = auth.get_auth_headers()
        
        self.assertEqual(headers["Authorization"], "Bearer test_token_123")
    
    def test_get_auth_headers_no_token(self):
        """Test getting auth headers when no token available."""
        auth = BearerTokenAuth()
        
        headers = auth.get_auth_headers()
        
        self.assertEqual(headers, {})
    
    def test_is_authenticated(self):
        """Test is_authenticated method."""
        auth = BearerTokenAuth()
        
        # Not authenticated without token
        self.assertFalse(auth.is_authenticated(self.mock_driver))
        
        # Authenticated with token
        auth.token = "test_token"
        auth.authenticated = True
        self.assertTrue(auth.is_authenticated(self.mock_driver))
    
    def test_logout(self):
        """Test logout functionality."""
        auth = BearerTokenAuth(token="test_token")
        auth.authenticated = True
        
        result = auth.logout(self.mock_driver)
        
        self.assertTrue(result)
        self.assertIsNone(auth.token)
        self.assertFalse(auth.authenticated)
        self.assertEqual(auth.auth_data, {})


class TestTTPAuthentication(unittest.TestCase):
    """Test cases for TTP authentication integration."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_auth = MockAuthentication("Test Auth", "Test Description")
    
    def test_ttp_without_authentication(self):
        """Test TTP without authentication requirement."""
        ttp = MockTTP("Test TTP", "Test Description")
        
        self.assertFalse(ttp.requires_authentication())
        self.assertTrue(ttp.authenticate(self.mock_driver, "http://test.com"))
    
    def test_ttp_with_authentication(self):
        """Test TTP with authentication requirement."""
        ttp = MockTTP("Test TTP", "Test Description", authentication=self.mock_auth)
        
        self.assertTrue(ttp.requires_authentication())
        result = ttp.authenticate(self.mock_driver, "http://test.com")
        
        self.assertTrue(result)
        self.assertTrue(self.mock_auth.auth_called)
    
    def test_ttp_authentication_failure(self):
        """Test TTP when authentication fails."""
        failing_auth = MockAuthentication("Failing Auth", "Fails", auth_success=False)
        ttp = MockTTP("Test TTP", "Test Description", authentication=failing_auth)
        
        result = ttp.authenticate(self.mock_driver, "http://test.com")
        
        self.assertFalse(result)
        self.assertTrue(failing_auth.auth_called)


class TestTTPExecutorAuthentication(unittest.TestCase):
    """Test cases for TTPExecutor authentication integration."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_driver.current_url = "http://test.com"
        self.mock_driver.quit = Mock()
    
    @patch('scythe.core.executor.webdriver.Chrome')
    @patch('time.sleep')
    def test_executor_with_successful_authentication(self, mock_sleep, mock_webdriver):
        """Test TTPExecutor with successful authentication."""
        mock_webdriver.return_value = self.mock_driver
        
        auth = MockAuthentication("Test Auth", "Test Description", auth_success=True)
        ttp = MockTTP("Test TTP", "Test Description", authentication=auth)
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger') as mock_logger:
            executor.run()
            
            # Verify authentication was attempted and successful
            self.assertTrue(auth.auth_called)
            mock_logger.info.assert_any_call("Authentication required for TTP: Test Auth")
            mock_logger.info.assert_any_call("Authentication successful")
            
            # Verify TTP executed normally
            self.assertEqual(len(ttp.steps_executed), 2)  # 2 payloads
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_executor_with_failed_authentication(self, mock_webdriver):
        """Test TTPExecutor with failed authentication."""
        mock_webdriver.return_value = self.mock_driver
        
        auth = MockAuthentication("Test Auth", "Test Description", auth_success=False)
        ttp = MockTTP("Test TTP", "Test Description", authentication=auth)
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger') as mock_logger:
            executor.run()
            
            # Verify authentication was attempted and failed
            self.assertTrue(auth.auth_called)
            mock_logger.error.assert_any_call("Authentication failed - aborting TTP execution")
            
            # Verify TTP did not execute
            self.assertEqual(len(ttp.steps_executed), 0)
    
    @patch('scythe.core.executor.webdriver.Chrome')
    @patch('time.sleep')
    def test_executor_without_authentication(self, mock_sleep, mock_webdriver):
        """Test TTPExecutor without authentication requirement."""
        mock_webdriver.return_value = self.mock_driver
        
        ttp = MockTTP("Test TTP", "Test Description")  # No authentication
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger') as mock_logger:
            executor.run()
            
            # Verify no authentication logs
            calls = [str(call) for call in mock_logger.info.call_args_list]
            auth_calls = [call for call in calls if "Authentication" in call]
            self.assertEqual(len(auth_calls), 0)
            
            # Verify TTP executed normally
            self.assertEqual(len(ttp.steps_executed), 2)


class TestAuthenticationError(unittest.TestCase):
    """Test cases for AuthenticationError exception."""
    
    def test_authentication_error_with_method(self):
        """Test AuthenticationError with auth method specified."""
        error = AuthenticationError("Auth failed", "Basic Auth")
        
        self.assertEqual(str(error), "Auth failed")
        self.assertEqual(error.auth_method, "Basic Auth")
    
    def test_authentication_error_without_method(self):
        """Test AuthenticationError without auth method."""
        error = AuthenticationError("Auth failed")
        
        self.assertEqual(str(error), "Auth failed")
        self.assertIsNone(error.auth_method)


if __name__ == '__main__':
    unittest.main()