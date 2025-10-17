import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the scythe package to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.core.ttp import TTP
from scythe.core.executor import TTPExecutor



class MockTTP(TTP):
    """Mock TTP for testing expected results functionality."""
    
    def __init__(self, name: str, description: str, expected_result: bool = True, success_results = None):
        super().__init__(name, description, expected_result)
        self.success_results = success_results if success_results is not None else [False, False, True]  # Default pattern
        self.current_step = 0
        
    def get_payloads(self):
        """Yield test payloads."""
        for i in range(len(self.success_results)):
            yield f"test_payload_{i}"
    
    def execute_step(self, driver, payload):
        """Mock execution step."""
        pass
    
    def verify_result(self, driver):
        """Return predefined results for testing."""
        if self.current_step < len(self.success_results):
            result = self.success_results[self.current_step]
            self.current_step += 1
            return result
        return False


class TestExpectedResults(unittest.TestCase):
    """Test cases for ExpectPass/ExpectFail functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_driver = Mock()
        self.mock_driver.current_url = "http://test.com"
        self.mock_driver.quit = Mock()
        
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_expect_pass_with_success(self, mock_webdriver):
        """Test TTP that expects to pass and does pass."""
        mock_webdriver.return_value = self.mock_driver
        
        # Create TTP that expects success and gets it
        ttp = MockTTP(
            name="Test TTP",
            description="Test description",
            expected_result=True,
            success_results=[True]
        )
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger') as mock_logger:
            executor.run()
            
            # Should log expected success
            mock_logger.info.assert_any_call("EXPECTED SUCCESS: 'test_payload_0'")
            
            # Should have one result
            self.assertEqual(len(executor.results), 1)
            result = executor.results[0]
            self.assertTrue(result['expected'])
            self.assertTrue(result['actual'])
            self.assertEqual(result['payload'], 'test_payload_0')
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_expect_pass_with_failure(self, mock_webdriver):
        """Test TTP that expects to pass but fails."""
        mock_webdriver.return_value = self.mock_driver
        
        # Create TTP that expects success but fails
        ttp = MockTTP(
            name="Test TTP",
            description="Test description", 
            expected_result=True,
            success_results=[False]
        )
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger') as mock_logger:
            executor.run()
            
            # Should log expected failure
            mock_logger.info.assert_any_call("EXPECTED FAILURE: 'test_payload_0' (security control working)")
            
            # Should have no results (no successes)
            self.assertEqual(len(executor.results), 0)
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_expect_fail_with_failure(self, mock_webdriver):
        """Test TTP that expects to fail and does fail."""
        mock_webdriver.return_value = self.mock_driver
        
        # Create TTP that expects failure and gets it
        ttp = MockTTP(
            name="Test TTP",
            description="Test description",
            expected_result=False,
            success_results=[False]
        )
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger') as mock_logger:
            executor.run()
            
            # Should log expected failure
            mock_logger.info.assert_any_call("EXPECTED FAILURE: 'test_payload_0'")
            
            # Should have no results
            self.assertEqual(len(executor.results), 0)
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_expect_fail_with_success(self, mock_webdriver):
        """Test TTP that expects to fail but succeeds."""
        mock_webdriver.return_value = self.mock_driver
        
        # Create TTP that expects failure but succeeds
        ttp = MockTTP(
            name="Test TTP",
            description="Test description",
            expected_result=False,
            success_results=[True]
        )
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger') as mock_logger:
            executor.run()
            
            # Should log unexpected success
            mock_logger.warning.assert_any_call("UNEXPECTED SUCCESS: 'test_payload_0' (expected to fail)")
            
            # Should have one result marked as unexpected
            self.assertEqual(len(executor.results), 1)
            result = executor.results[0]
            self.assertFalse(result['expected'])
            self.assertTrue(result['actual'])
            self.assertEqual(result['payload'], 'test_payload_0')
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_mixed_results_expect_pass(self, mock_webdriver):
        """Test TTP with mixed results when expecting pass."""
        mock_webdriver.return_value = self.mock_driver
        
        # Create TTP with mixed results
        ttp = MockTTP(
            name="Test TTP",
            description="Test description",
            expected_result=True,
            success_results=[False, True, False, True]
        )
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger'):
            executor.run()
            
            # Should have two successes
            self.assertEqual(len(executor.results), 2)
            
            # Both should be expected successes
            for result in executor.results:
                self.assertTrue(result['expected'])
                self.assertTrue(result['actual'])
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_mixed_results_expect_fail(self, mock_webdriver):
        """Test TTP with mixed results when expecting fail."""
        mock_webdriver.return_value = self.mock_driver
        
        # Create TTP with mixed results, expecting failure
        ttp = MockTTP(
            name="Test TTP",
            description="Test description",
            expected_result=False,
            success_results=[False, True, False, True]
        )
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger'):
            executor.run()
            
            # Should have two successes, both unexpected
            self.assertEqual(len(executor.results), 2)
            
            # Both should be unexpected successes
            for result in executor.results:
                self.assertFalse(result['expected'])
                self.assertTrue(result['actual'])
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_summary_with_expected_successes(self, mock_webdriver):
        """Test summary output with expected successes."""
        mock_webdriver.return_value = self.mock_driver
        
        ttp = MockTTP(
            name="Test TTP",
            description="Test description",
            expected_result=True,
            success_results=[True, True]
        )
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger') as mock_logger:
            executor.run()
            
            # Check summary logs
            mock_logger.info.assert_any_call("Total results: 2")
            mock_logger.info.assert_any_call("Expected successes: 2")
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_summary_with_unexpected_successes(self, mock_webdriver):
        """Test summary output with unexpected successes."""
        mock_webdriver.return_value = self.mock_driver
        
        ttp = MockTTP(
            name="Test TTP",
            description="Test description",
            expected_result=False,
            success_results=[True, True]
        )
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger') as mock_logger:
            executor.run()
            
            # Check summary logs
            mock_logger.info.assert_any_call("Total results: 2")
            mock_logger.warning.assert_any_call("Unexpected successes: 2")
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_summary_no_results_expect_pass(self, mock_webdriver):
        """Test summary when no results and expecting pass."""
        mock_webdriver.return_value = self.mock_driver
        
        ttp = MockTTP(
            name="Test TTP",
            description="Test description",
            expected_result=True,
            success_results=[False]
        )
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger') as mock_logger:
            executor.run()
            
            # Check summary for no results when expecting success
            mock_logger.info.assert_any_call("No successes detected (expected to find vulnerabilities).")
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_summary_no_results_expect_fail(self, mock_webdriver):
        """Test summary when no results and expecting fail."""
        mock_webdriver.return_value = self.mock_driver
        
        ttp = MockTTP(
            name="Test TTP",
            description="Test description",
            expected_result=False,
            success_results=[False]
        )
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger') as mock_logger:
            executor.run()
            
            # Check summary for no results when expecting failure
            mock_logger.info.assert_any_call("No successes detected (security controls working as expected).")
    
    def test_ttp_default_expected_result(self):
        """Test that TTP defaults to expecting success (True)."""
        ttp = MockTTP("Test", "Description")
        self.assertTrue(ttp.expected_result)
    
    def test_ttp_explicit_expected_result(self):
        """Test TTP with explicitly set expected result."""
        ttp_pass = MockTTP("Test", "Description", expected_result=True)
        ttp_fail = MockTTP("Test", "Description", expected_result=False)
        
        self.assertTrue(ttp_pass.expected_result)
        self.assertFalse(ttp_fail.expected_result)
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_was_successful_with_expected_results(self, mock_webdriver):
        """Test was_successful() returns True when all results match expectations."""
        mock_webdriver.return_value = self.mock_driver
        
        # Test with expected successes
        ttp = MockTTP(
            name="Test TTP",
            description="Test description",
            expected_result=True,
            success_results=[True, True]
        )
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        executor.run()
        
        # Should return True since results matched expectations
        self.assertTrue(executor.was_successful())
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_was_successful_with_unexpected_results(self, mock_webdriver):
        """Test was_successful() returns False when results don't match expectations."""
        mock_webdriver.return_value = self.mock_driver
        
        # Test with unexpected successes (expected to fail but succeeded)
        ttp = MockTTP(
            name="Test TTP",
            description="Test description",
            expected_result=False,
            success_results=[True]
        )
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        executor.run()
        
        # Should return False since we got unexpected success
        self.assertFalse(executor.was_successful())
    
    @patch('scythe.core.executor.webdriver.Chrome')
    def test_was_successful_with_unexpected_failures(self, mock_webdriver):
        """Test was_successful() returns False when expected success but got failure."""
        mock_webdriver.return_value = self.mock_driver
        
        # Test expecting success but getting failure
        ttp = MockTTP(
            name="Test TTP",
            description="Test description",
            expected_result=True,
            success_results=[False, False]
        )
        
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        executor.run()
        
        # Should return False since we expected success but got failures
        self.assertFalse(executor.was_successful())


if __name__ == '__main__':
    unittest.main()