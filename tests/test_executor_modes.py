"""
Comprehensive tests for TTPExecutor in both UI and API modes.

This test file ensures that TTPExecutor correctly handles both execution modes
and would have caught the bug where API mode was not properly implemented.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the scythe package to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.core.ttp import TTP
from scythe.core.executor import TTPExecutor


class MockTTPDualMode(TTP):
    """Mock TTP that supports both UI and API modes."""
    
    def __init__(self, execution_mode='ui', expected_result=True):
        super().__init__(
            name="Mock Dual Mode TTP",
            description="Test TTP supporting both modes",
            expected_result=expected_result,
            execution_mode=execution_mode
        )
        self.ui_execute_called = False
        self.ui_verify_called = False
        self.api_execute_called = False
        self.api_verify_called = False
        self.payloads_list = ['payload1', 'payload2', 'payload3']
    
    def get_payloads(self):
        """Yield test payloads."""
        yield from self.payloads_list
    
    def execute_step(self, driver, payload):
        """Mock UI execution step."""
        self.ui_execute_called = True
    
    def verify_result(self, driver):
        """Mock UI result verification."""
        self.ui_verify_called = True
        return True
    
    def execute_step_api(self, session, payload, context):
        """Mock API execution step."""
        self.api_execute_called = True
        
        # Create a mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '{"success": true}'
        mock_response.url = context.get('target_url', 'http://test.com')
        mock_response.headers = {'X-SCYTHE-TARGET-VERSION': '1.0.0'}
        
        return mock_response
    
    def verify_result_api(self, response, context):
        """Mock API result verification."""
        self.api_verify_called = True
        return response.status_code == 200


class MockTTPUIOnly(TTP):
    """Mock TTP that only supports UI mode (legacy behavior)."""
    
    def __init__(self):
        super().__init__(
            name="Mock UI Only TTP",
            description="Test TTP without API support",
            execution_mode='ui'
        )
    
    def get_payloads(self):
        yield 'payload1'
    
    def execute_step(self, driver, payload):
        pass
    
    def verify_result(self, driver):
        return True


class TestTTPExecutorUIMode(unittest.TestCase):
    """Test cases for TTPExecutor in UI mode."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_driver = Mock()
        self.mock_driver.current_url = "http://test.com"
        self.mock_driver.quit = Mock()
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_ui_mode_initializes_webdriver(self, mock_webdriver):
        """Test that UI mode initializes WebDriver."""
        mock_webdriver.return_value = self.mock_driver
        
        ttp = MockTTPDualMode(execution_mode='ui')
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger'):
            executor.run()
        
        # WebDriver should be initialized
        mock_webdriver.assert_called_once()
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_ui_mode_calls_ui_methods(self, mock_webdriver):
        """Test that UI mode calls execute_step and verify_result."""
        mock_webdriver.return_value = self.mock_driver
        
        ttp = MockTTPDualMode(execution_mode='ui')
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger'):
            executor.run()
        
        # UI methods should be called
        self.assertTrue(ttp.ui_execute_called)
        self.assertTrue(ttp.ui_verify_called)
        
        # API methods should NOT be called
        self.assertFalse(ttp.api_execute_called)
        self.assertFalse(ttp.api_verify_called)
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_ui_mode_driver_cleanup(self, mock_webdriver):
        """Test that WebDriver is properly cleaned up in UI mode."""
        mock_webdriver.return_value = self.mock_driver
        
        ttp = MockTTPDualMode(execution_mode='ui')
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger'):
            executor.run()
        
        # Driver should be quit
        self.mock_driver.quit.assert_called_once()


class TestTTPExecutorAPIMode(unittest.TestCase):
    """Test cases for TTPExecutor in API mode."""
    
    def test_api_mode_does_not_initialize_webdriver(self):
        """Test that API mode does NOT initialize WebDriver."""
        ttp = MockTTPDualMode(execution_mode='api')
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch('scythe.core.executor.webdriver.Chrome') as mock_webdriver:
            with patch.object(executor, 'logger'):
                executor.run()
            
            # WebDriver should NOT be initialized in API mode
            mock_webdriver.assert_not_called()
    
    def test_api_mode_calls_api_methods(self):
        """Test that API mode calls execute_step_api and verify_result_api."""
        ttp = MockTTPDualMode(execution_mode='api')
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger'):
            executor.run()
        
        # API methods should be called
        self.assertTrue(ttp.api_execute_called)
        self.assertTrue(ttp.api_verify_called)
        
        # UI methods should NOT be called
        self.assertFalse(ttp.ui_execute_called)
        self.assertFalse(ttp.ui_verify_called)
    
    def test_api_mode_creates_session(self):
        """Test that API mode creates a requests.Session."""
        ttp = MockTTPDualMode(execution_mode='api')
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch('scythe.core.executor.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            with patch.object(executor, 'logger'):
                executor.run()
            
            # Session should be created
            mock_session_class.assert_called_once()
            
            # Session should be closed
            mock_session.close.assert_called_once()
    
    def test_api_mode_processes_payloads(self):
        """Test that API mode processes all payloads."""
        ttp = MockTTPDualMode(execution_mode='api')
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger'):
            executor.run()
        
        # Should have processed all payloads
        self.assertEqual(len(executor.results), 3)
    
    def test_api_mode_context_setup(self):
        """Test that API mode sets up context correctly."""
        ttp = MockTTPDualMode(execution_mode='api')
        
        # Track the context passed to execute_step_api
        captured_context = {}
        
        def capture_context(session, payload, context):
            captured_context.update(context)
            return ttp.execute_step_api(session, payload, context)
        
        with patch.object(ttp, 'execute_step_api', side_effect=capture_context):
            executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
            
            with patch.object(executor, 'logger'):
                executor.run()
        
        # Context should have required keys
        self.assertIn('target_url', captured_context)
        self.assertEqual(captured_context['target_url'], 'http://test.com')
        self.assertIn('auth_headers', captured_context)
        self.assertIn('rate_limit_resume_at', captured_context)
    
    def test_api_mode_extracts_version_header(self):
        """Test that API mode extracts X-SCYTHE-TARGET-VERSION header."""
        ttp = MockTTPDualMode(execution_mode='api')
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger'):
            executor.run()
        
        # Results should have version info
        for result in executor.results:
            self.assertIn('target_version', result)
            self.assertEqual(result['target_version'], '1.0.0')
    
    def test_api_mode_with_expected_results_true(self):
        """Test API mode with expected_result=True."""
        ttp = MockTTPDualMode(execution_mode='api', expected_result=True)
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger') as mock_logger:
            executor.run()
        
        # Should log expected successes
        self.assertEqual(len(executor.results), 3)
        for result in executor.results:
            self.assertTrue(result['expected'])
            self.assertTrue(result['actual'])
    
    def test_api_mode_with_expected_results_false(self):
        """Test API mode with expected_result=False."""
        ttp = MockTTPDualMode(execution_mode='api', expected_result=False)
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger') as mock_logger:
            executor.run()
        
        # Should log unexpected successes
        self.assertEqual(len(executor.results), 3)
        for result in executor.results:
            self.assertFalse(result['expected'])
            self.assertTrue(result['actual'])
        
        # Should mark as test failure
        self.assertTrue(executor.has_test_failures)


class TestTTPExecutorModeSelection(unittest.TestCase):
    """Test cases for TTPExecutor mode selection logic."""
    
    def test_executor_detects_ui_mode(self):
        """Test that executor detects UI mode from TTP."""
        ttp = MockTTPDualMode(execution_mode='ui')
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        self.assertEqual(executor.ttp.execution_mode, 'ui')
    
    def test_executor_detects_api_mode(self):
        """Test that executor detects API mode from TTP."""
        ttp = MockTTPDualMode(execution_mode='api')
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        self.assertEqual(executor.ttp.execution_mode, 'api')
    
    def test_executor_logs_execution_mode(self):
        """Test that executor logs the execution mode."""
        ttp_ui = MockTTPDualMode(execution_mode='ui')
        executor_ui = TTPExecutor(ttp=ttp_ui, target_url="http://test.com", headless=True)
        
        with patch('scythe.core.executor.webdriver.Chrome') as mock_webdriver:
            mock_driver = Mock()
            mock_driver.current_url = "http://test.com"
            mock_driver.quit = Mock()
            mock_webdriver.return_value = mock_driver
            
            with patch.object(executor_ui, 'logger') as mock_logger:
                executor_ui.run()
                
                # Should log UI mode
                mock_logger.info.assert_any_call("Execution mode: UI")
        
        ttp_api = MockTTPDualMode(execution_mode='api')
        executor_api = TTPExecutor(ttp=ttp_api, target_url="http://test.com", headless=True)
        
        with patch.object(executor_api, 'logger') as mock_logger:
            executor_api.run()
            
            # Should log API mode
            mock_logger.info.assert_any_call("Execution mode: API")
    
    def test_executor_default_mode_is_ui(self):
        """Test that default execution mode is UI."""
        # TTP with no explicit mode should default to UI
        ttp = MockTTPUIOnly()
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        self.assertEqual(executor.ttp.execution_mode, 'ui')


class TestTTPExecutorAPIErrorHandling(unittest.TestCase):
    """Test cases for error handling in API mode."""
    
    def test_api_mode_handles_request_exception(self):
        """Test that API mode handles request exceptions gracefully."""
        ttp = MockTTPDualMode(execution_mode='api')
        
        # Make execute_step_api raise an exception
        def raise_exception(session, payload, context):
            raise Exception("Network error")
        
        with patch.object(ttp, 'execute_step_api', side_effect=raise_exception):
            executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
            
            with patch.object(executor, 'logger') as mock_logger:
                executor.run()
                
                # Should log errors but not crash
                self.assertTrue(any('Error during step' in str(call) for call in mock_logger.error.call_args_list))
    
    def test_api_mode_continues_after_error(self):
        """Test that API mode continues processing after an error."""
        ttp = MockTTPDualMode(execution_mode='api')
        
        call_count = [0]
        
        def fail_first_then_succeed(session, payload, context):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("First call fails")
            return ttp.execute_step_api(session, payload, context)
        
        with patch.object(ttp, 'execute_step_api', side_effect=fail_first_then_succeed):
            executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
            
            with patch.object(executor, 'logger'):
                executor.run()
            
            # Should have processed remaining payloads after error
            self.assertEqual(len(executor.results), 2)  # 3 payloads - 1 error = 2 results


class TestTTPExecutorAuthenticationAPIMode(unittest.TestCase):
    """Test cases for authentication in API mode."""
    
    def test_api_mode_applies_auth_headers(self):
        """Test that API mode applies authentication headers."""
        from scythe.auth.base import Authentication
        
        # Create mock authentication
        mock_auth = Mock(spec=Authentication)
        mock_auth.name = "Test Auth"
        mock_auth.get_auth_headers.return_value = {'Authorization': 'Bearer token123'}
        
        ttp = MockTTPDualMode(execution_mode='api')
        ttp.authentication = mock_auth
        
        captured_session = None
        
        def capture_session(session, payload, context):
            nonlocal captured_session
            captured_session = session
            return ttp.execute_step_api(session, payload, context)
        
        with patch.object(ttp, 'execute_step_api', side_effect=capture_session):
            executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
            
            with patch.object(executor, 'logger'):
                executor.run()
        
        # Auth headers should be called
        mock_auth.get_auth_headers.assert_called()


class TestTTPExecutorWasSuccessfulAPIMode(unittest.TestCase):
    """Test was_successful() method in API mode."""
    
    def test_was_successful_true_when_results_match_expectations(self):
        """Test was_successful returns True when API results match expectations."""
        ttp = MockTTPDualMode(execution_mode='api', expected_result=True)
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger'):
            executor.run()
        
        # Should be successful since results matched expectations
        self.assertTrue(executor.was_successful())
    
    def test_was_successful_false_when_unexpected_success(self):
        """Test was_successful returns False with unexpected successes in API mode."""
        ttp = MockTTPDualMode(execution_mode='api', expected_result=False)
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger'):
            executor.run()
        
        # Should NOT be successful since we got unexpected successes
        self.assertFalse(executor.was_successful())


class TestTTPExecutorBothModes(unittest.TestCase):
    """Test cases comparing UI and API mode behavior."""
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_both_modes_process_same_payloads(self, mock_webdriver):
        """Test that both modes process the same payloads."""
        mock_driver = Mock()
        mock_driver.current_url = "http://test.com"
        mock_driver.quit = Mock()
        mock_webdriver.return_value = mock_driver
        
        # UI mode
        ttp_ui = MockTTPDualMode(execution_mode='ui')
        executor_ui = TTPExecutor(ttp=ttp_ui, target_url="http://test.com", headless=True)
        
        with patch.object(executor_ui, 'logger'):
            executor_ui.run()
        
        # API mode
        ttp_api = MockTTPDualMode(execution_mode='api')
        executor_api = TTPExecutor(ttp=ttp_api, target_url="http://test.com", headless=True)
        
        with patch.object(executor_api, 'logger'):
            executor_api.run()
        
        # Both should process same number of results
        self.assertEqual(len(executor_ui.results), len(executor_api.results))
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_both_modes_respect_expected_result(self, mock_webdriver):
        """Test that both modes respect expected_result setting."""
        mock_driver = Mock()
        mock_driver.current_url = "http://test.com"
        mock_driver.quit = Mock()
        mock_webdriver.return_value = mock_driver
        
        # UI mode with expected_result=False
        ttp_ui = MockTTPDualMode(execution_mode='ui', expected_result=False)
        executor_ui = TTPExecutor(ttp=ttp_ui, target_url="http://test.com", headless=True)
        
        with patch.object(executor_ui, 'logger'):
            executor_ui.run()
        
        # API mode with expected_result=False
        ttp_api = MockTTPDualMode(execution_mode='api', expected_result=False)
        executor_api = TTPExecutor(ttp=ttp_api, target_url="http://test.com", headless=True)
        
        with patch.object(executor_api, 'logger'):
            executor_api.run()
        
        # Both should have test failures (unexpected successes)
        self.assertTrue(executor_ui.has_test_failures)
        self.assertTrue(executor_api.has_test_failures)


if __name__ == '__main__':
    unittest.main()
