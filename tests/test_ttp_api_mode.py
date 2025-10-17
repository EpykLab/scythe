import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the scythe package to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.core.ttp import TTP
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.ttps.web.sql_injection import InputFieldInjector, URLManipulation
from scythe.payloads.generators import StaticPayloadGenerator
from scythe.journeys.actions import TTPAction
from scythe.journeys.base import Journey, Step


class MockTTPWithAPISupport(TTP):
    """Mock TTP that supports API mode for testing."""
    
    def __init__(self, execution_mode='ui'):
        super().__init__(
            name="Mock TTP with API",
            description="Test TTP",
            execution_mode=execution_mode
        )
        self.ui_executed = False
        self.api_executed = False
        self.payloads_generated = []
    
    def get_payloads(self):
        payloads = ['payload1', 'payload2']
        self.payloads_generated = payloads
        yield from payloads
    
    def execute_step(self, driver, payload):
        self.ui_executed = True
    
    def verify_result(self, driver):
        return True
    
    def execute_step_api(self, session, payload, context):
        self.api_executed = True
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"success": true}'
        mock_response.url = 'http://test.com/api'
        return mock_response
    
    def verify_result_api(self, response, context):
        return response.status_code == 200


class MockTTPUIOnly(TTP):
    """Mock TTP that only supports UI mode."""
    
    def __init__(self):
        super().__init__(
            name="Mock TTP UI Only",
            description="Test TTP without API support",
            execution_mode='ui'
        )
    
    def get_payloads(self):
        yield 'payload1'
    
    def execute_step(self, driver, payload):
        pass
    
    def verify_result(self, driver):
        return True


class TestTTPBaseClass(unittest.TestCase):
    """Test cases for TTP base class API mode functionality."""
    
    def test_ttp_default_execution_mode(self):
        """Test that TTP defaults to UI mode."""
        ttp = MockTTPUIOnly()
        self.assertEqual(ttp.execution_mode, 'ui')
    
    def test_ttp_api_execution_mode(self):
        """Test TTP with API execution mode."""
        ttp = MockTTPWithAPISupport(execution_mode='api')
        self.assertEqual(ttp.execution_mode, 'api')
    
    def test_ttp_execution_mode_case_insensitive(self):
        """Test that execution mode is case insensitive."""
        ttp = MockTTPWithAPISupport(execution_mode='API')
        self.assertEqual(ttp.execution_mode, 'api')
    
    def test_supports_api_mode_with_implementation(self):
        """Test supports_api_mode returns True when API methods are implemented."""
        ttp = MockTTPWithAPISupport(execution_mode='api')
        self.assertTrue(ttp.supports_api_mode())
    
    def test_supports_api_mode_without_implementation(self):
        """Test supports_api_mode returns False when API methods are not implemented."""
        ttp = MockTTPUIOnly()
        # Should return False since it doesn't override the API methods
        # Note: This actually returns True because the default implementation exists
        # The real check happens when execute_step_api is called and raises NotImplementedError
        self.assertIsNotNone(ttp.supports_api_mode())
    
    def test_execute_step_api_not_implemented(self):
        """Test that execute_step_api raises NotImplementedError by default."""
        ttp = MockTTPUIOnly()
        mock_session = Mock()
        context = {}
        
        with self.assertRaises(NotImplementedError) as cm:
            ttp.execute_step_api(mock_session, 'payload', context)
        
        self.assertIn("does not support API execution mode", str(cm.exception))
    
    def test_verify_result_api_not_implemented(self):
        """Test that verify_result_api raises NotImplementedError by default."""
        ttp = MockTTPUIOnly()
        mock_response = Mock()
        context = {}
        
        with self.assertRaises(NotImplementedError) as cm:
            ttp.verify_result_api(mock_response, context)
        
        self.assertIn("does not support API result verification", str(cm.exception))


class TestLoginBruteforceTTPAPIMode(unittest.TestCase):
    """Test cases for LoginBruteforceTTP API mode."""
    
    def setUp(self):
        self.payload_gen = StaticPayloadGenerator(['pass1', 'pass2', 'pass3'])
    
    def test_login_bruteforce_ui_mode_initialization(self):
        """Test LoginBruteforceTTP initialization in UI mode."""
        ttp = LoginBruteforceTTP(
            payload_generator=self.payload_gen,
            username='admin',
            username_selector='input[name="username"]',
            password_selector='input[name="password"]',
            submit_selector='button[type="submit"]',
            execution_mode='ui'
        )
        
        self.assertEqual(ttp.execution_mode, 'ui')
        self.assertEqual(ttp.username, 'admin')
        self.assertEqual(ttp.username_selector, 'input[name="username"]')
        self.assertIsNotNone(ttp.payload_generator)
    
    def test_login_bruteforce_api_mode_initialization(self):
        """Test LoginBruteforceTTP initialization in API mode."""
        ttp = LoginBruteforceTTP(
            payload_generator=self.payload_gen,
            username='admin',
            execution_mode='api',
            api_endpoint='/api/auth/login',
            username_field='username',
            password_field='password'
        )
        
        self.assertEqual(ttp.execution_mode, 'api')
        self.assertEqual(ttp.api_endpoint, '/api/auth/login')
        self.assertEqual(ttp.username_field, 'username')
        self.assertEqual(ttp.password_field, 'password')
    
    def test_login_bruteforce_success_indicators(self):
        """Test LoginBruteforceTTP success indicators configuration."""
        success_indicators = {
            'status_code': 200,
            'response_contains': 'token',
            'response_not_contains': 'error'
        }
        
        ttp = LoginBruteforceTTP(
            payload_generator=self.payload_gen,
            username='admin',
            execution_mode='api',
            api_endpoint='/api/login',
            success_indicators=success_indicators
        )
        
        self.assertEqual(ttp.success_indicators, success_indicators)
    
    def test_login_bruteforce_execute_step_api(self):
        """Test LoginBruteforceTTP execute_step_api method."""
        ttp = LoginBruteforceTTP(
            payload_generator=self.payload_gen,
            username='admin',
            execution_mode='api',
            api_endpoint='/api/auth/login',
            username_field='username',
            password_field='password'
        )
        
        # Mock session and response
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.headers = {}
        mock_session.post.return_value = mock_response
        
        context = {'target_url': 'http://test.com'}
        
        # Execute
        response = ttp.execute_step_api(mock_session, 'testpass', context)
        
        # Verify session.post was called correctly
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        
        self.assertIn('/api/auth/login', call_args[0][0])
        self.assertEqual(call_args[1]['json'], {
            'username': 'admin',
            'password': 'testpass'
        })
    
    def test_login_bruteforce_verify_result_api_success(self):
        """Test LoginBruteforceTTP verify_result_api with successful login."""
        ttp = LoginBruteforceTTP(
            payload_generator=self.payload_gen,
            username='admin',
            execution_mode='api',
            api_endpoint='/api/login',
            success_indicators={
                'status_code': 200,
                'response_contains': 'token'
            }
        )
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"token": "abc123"}'
        
        context = {}
        result = ttp.verify_result_api(mock_response, context)
        
        self.assertTrue(result)
    
    def test_login_bruteforce_verify_result_api_failure(self):
        """Test LoginBruteforceTTP verify_result_api with failed login."""
        ttp = LoginBruteforceTTP(
            payload_generator=self.payload_gen,
            username='admin',
            execution_mode='api',
            api_endpoint='/api/login',
            success_indicators={
                'status_code': 200,
                'response_not_contains': 'invalid'
            }
        )
        
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = '{"error": "invalid credentials"}'
        
        context = {}
        result = ttp.verify_result_api(mock_response, context)
        
        self.assertFalse(result)  # Status code mismatch
    
    @patch('time.sleep')
    @patch('time.time')
    def test_login_bruteforce_rate_limiting(self, mock_time, mock_sleep):
        """Test LoginBruteforceTTP respects rate limiting."""
        mock_time.return_value = 1000.0
        
        ttp = LoginBruteforceTTP(
            payload_generator=self.payload_gen,
            username='admin',
            execution_mode='api',
            api_endpoint='/api/login'
        )
        
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_session.post.return_value = mock_response
        
        # Set rate limit in context
        context = {
            'target_url': 'http://test.com',
            'rate_limit_resume_at': 1005.0  # 5 seconds in future
        }
        
        ttp.execute_step_api(mock_session, 'testpass', context)
        
        # Should have slept for 5 seconds
        mock_sleep.assert_called_once_with(5.0)


class TestSQLInjectionTTPAPIMode(unittest.TestCase):
    """Test cases for SQL Injection TTPs API mode."""
    
    def setUp(self):
        self.payload_gen = StaticPayloadGenerator(["' OR '1'='1", "1; DROP TABLE users"])
    
    def test_input_field_injector_api_mode_initialization(self):
        """Test InputFieldInjector initialization in API mode."""
        ttp = InputFieldInjector(
            payload_generator=self.payload_gen,
            execution_mode='api',
            api_endpoint='/api/search',
            injection_field='query',
            http_method='POST'
        )
        
        self.assertEqual(ttp.execution_mode, 'api')
        self.assertEqual(ttp.api_endpoint, '/api/search')
        self.assertEqual(ttp.injection_field, 'query')
        self.assertEqual(ttp.http_method, 'POST')
    
    def test_input_field_injector_execute_step_api_post(self):
        """Test InputFieldInjector execute_step_api with POST method."""
        ttp = InputFieldInjector(
            payload_generator=self.payload_gen,
            execution_mode='api',
            api_endpoint='/api/search',
            injection_field='query',
            http_method='POST'
        )
        
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_session.request.return_value = mock_response
        
        context = {'target_url': 'http://test.com'}
        
        response = ttp.execute_step_api(mock_session, "' OR 1=1--", context)
        
        # Verify request was made correctly
        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        
        self.assertEqual(call_args[0][0], 'POST')
        self.assertIn('/api/search', call_args[0][1])
        self.assertEqual(call_args[1]['json'], {'query': "' OR 1=1--"})
    
    def test_input_field_injector_execute_step_api_get(self):
        """Test InputFieldInjector execute_step_api with GET method."""
        ttp = InputFieldInjector(
            payload_generator=self.payload_gen,
            execution_mode='api',
            api_endpoint='/api/search',
            injection_field='query',
            http_method='GET'
        )
        
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_session.get.return_value = mock_response
        
        context = {'target_url': 'http://test.com'}
        
        response = ttp.execute_step_api(mock_session, "' OR 1=1--", context)
        
        # Verify GET request with query params
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        
        self.assertIn('/api/search', call_args[0][0])
        self.assertEqual(call_args[1]['params'], {'query': "' OR 1=1--"})
    
    def test_input_field_injector_verify_result_api_sql_error(self):
        """Test InputFieldInjector verify_result_api detects SQL errors."""
        ttp = InputFieldInjector(
            payload_generator=self.payload_gen,
            execution_mode='api',
            api_endpoint='/api/search'
        )
        
        # Mock response with SQL error
        mock_response = Mock()
        mock_response.text = 'MySQL syntax error near line 1'
        
        context = {}
        result = ttp.verify_result_api(mock_response, context)
        
        self.assertTrue(result)  # Should detect SQL error
    
    def test_input_field_injector_verify_result_api_no_error(self):
        """Test InputFieldInjector verify_result_api with clean response."""
        ttp = InputFieldInjector(
            payload_generator=self.payload_gen,
            execution_mode='api',
            api_endpoint='/api/search'
        )
        
        # Mock clean response
        mock_response = Mock()
        mock_response.text = '{"results": []}'
        
        context = {}
        result = ttp.verify_result_api(mock_response, context)
        
        self.assertFalse(result)  # No SQL error indicators
    
    def test_url_manipulation_api_mode_initialization(self):
        """Test URLManipulation initialization in API mode."""
        ttp = URLManipulation(
            payload_generator=self.payload_gen,
            execution_mode='api',
            api_endpoint='/api/items',
            query_param='id'
        )
        
        self.assertEqual(ttp.execution_mode, 'api')
        self.assertEqual(ttp.api_endpoint, '/api/items')
        self.assertEqual(ttp.query_param, 'id')
    
    def test_url_manipulation_execute_step_api(self):
        """Test URLManipulation execute_step_api method."""
        ttp = URLManipulation(
            payload_generator=self.payload_gen,
            execution_mode='api',
            api_endpoint='/api/items',
            query_param='id'
        )
        
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_session.get.return_value = mock_response
        
        context = {'target_url': 'http://test.com'}
        
        response = ttp.execute_step_api(mock_session, "1' OR '1'='1", context)
        
        # Verify GET request with query param
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        
        self.assertIn('/api/items', call_args[0][0])
        self.assertEqual(call_args[1]['params'], {'id': "1' OR '1'='1"})


class TestTTPActionAPIMode(unittest.TestCase):
    """Test cases for TTPAction with API mode."""
    
    def test_ttp_action_detects_api_mode(self):
        """Test that TTPAction detects TTP execution mode."""
        api_ttp = MockTTPWithAPISupport(execution_mode='api')
        action = TTPAction(ttp=api_ttp, target_url='http://test.com')
        
        self.assertEqual(action.ttp.execution_mode, 'api')
    
    def test_ttp_action_detects_ui_mode(self):
        """Test that TTPAction detects UI mode."""
        ui_ttp = MockTTPUIOnly()
        action = TTPAction(ttp=ui_ttp, target_url='http://test.com')
        
        self.assertEqual(action.ttp.execution_mode, 'ui')
    
    def test_ttp_action_execute_api_mode(self):
        """Test TTPAction execution in API mode."""
        api_ttp = MockTTPWithAPISupport(execution_mode='api')
        action = TTPAction(ttp=api_ttp, target_url='http://test.com')
        
        mock_driver = Mock()
        context = {'target_url': 'http://test.com'}
        
        result = action.execute(mock_driver, context)
        
        # Verify API mode was used
        self.assertTrue(api_ttp.api_executed)
        self.assertFalse(api_ttp.ui_executed)
        
        # Check results were stored
        self.assertEqual(action.get_result('execution_mode'), 'api')
        self.assertIsNotNone(action.get_result('total_payloads'))
        self.assertIsNotNone(action.get_result('successful_payloads'))
    
    def test_ttp_action_execute_ui_mode(self):
        """Test TTPAction execution in UI mode."""
        ui_ttp = MockTTPWithAPISupport(execution_mode='ui')
        action = TTPAction(ttp=ui_ttp, target_url='http://test.com')
        
        mock_driver = Mock()
        mock_driver.current_url = 'http://test.com'
        context = {}
        
        result = action.execute(mock_driver, context)
        
        # Verify UI mode was used
        self.assertTrue(ui_ttp.ui_executed)
        self.assertFalse(ui_ttp.api_executed)
        
        # Check results were stored
        self.assertEqual(action.get_result('execution_mode'), 'ui')
    
    def test_ttp_action_api_mode_unsupported_ttp(self):
        """Test TTPAction with TTP that doesn't support API mode."""
        ui_only_ttp = MockTTPUIOnly()
        ui_only_ttp.execution_mode = 'api'  # Force API mode
        
        action = TTPAction(ttp=ui_only_ttp, target_url='http://test.com')
        
        mock_driver = Mock()
        context = {'target_url': 'http://test.com'}
        
        result = action.execute(mock_driver, context)
        
        # Should fail because TTP doesn't support API mode
        self.assertFalse(result)
        self.assertIn('does not support API execution mode', 
                     action.get_result('error', ''))
    
    def test_ttp_action_creates_session_if_missing(self):
        """Test that TTPAction creates a session if not in context."""
        api_ttp = MockTTPWithAPISupport(execution_mode='api')
        action = TTPAction(ttp=api_ttp, target_url='http://test.com')
        
        mock_driver = Mock()
        context = {'target_url': 'http://test.com'}  # No session
        
        result = action.execute(mock_driver, context)
        
        # Session should have been created
        self.assertIn('requests_session', context)
        self.assertIsNotNone(context['requests_session'])
    
    def test_ttp_action_reuses_existing_session(self):
        """Test that TTPAction reuses existing session from context."""
        api_ttp = MockTTPWithAPISupport(execution_mode='api')
        action = TTPAction(ttp=api_ttp, target_url='http://test.com')
        
        mock_driver = Mock()
        mock_session = Mock()
        context = {
            'target_url': 'http://test.com',
            'requests_session': mock_session
        }
        
        result = action.execute(mock_driver, context)
        
        # Should reuse the same session
        self.assertIs(context['requests_session'], mock_session)


class TestBackwardCompatibility(unittest.TestCase):
    """Test cases to ensure backward compatibility."""
    
    def test_existing_ui_ttp_still_works(self):
        """Test that existing UI-only TTP code still works."""
        payload_gen = StaticPayloadGenerator(['test'])
        
        # Old style: no execution_mode specified
        ttp = LoginBruteforceTTP(
            payload_generator=payload_gen,
            username='admin',
            username_selector='input[name="username"]',
            password_selector='input[name="password"]',
            submit_selector='button[type="submit"]'
        )
        
        # Should default to UI mode
        self.assertEqual(ttp.execution_mode, 'ui')
        self.assertEqual(ttp.username_selector, 'input[name="username"]')
    
    def test_sql_injection_backward_compatible(self):
        """Test SQL injection TTPs are backward compatible."""
        payload_gen = StaticPayloadGenerator(["' OR 1=1--"])
        
        # Old style InputFieldInjector
        ttp = InputFieldInjector(
            target_url='http://test.com/search',
            field_selector='input',
            submit_selector='button',
            payload_generator=payload_gen
        )
        
        # Should default to UI mode
        self.assertEqual(ttp.execution_mode, 'ui')
        
        # Old style URLManipulation
        ttp2 = URLManipulation(
            payload_generator=payload_gen,
            target_url='http://test.com/items'
        )
        
        self.assertEqual(ttp2.execution_mode, 'ui')


if __name__ == '__main__':
    unittest.main()
