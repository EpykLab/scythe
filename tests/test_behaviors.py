#!/usr/bin/env python3
"""
Test script for Scythe Behaviors functionality.

This script provides basic unit tests for the behavior system to ensure
all behaviors work correctly and integrate properly with the TTPExecutor.
"""

import unittest
import sys
import os
from unittest.mock import Mock

# Add the parent directory to the path so we can import scythe
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.behaviors.base import Behavior
from scythe.behaviors.default import DefaultBehavior
from scythe.behaviors.human import HumanBehavior
from scythe.behaviors.machine import MachineBehavior
from scythe.behaviors.stealth import StealthBehavior
from scythe.core.ttp import TTP
from scythe.core.executor import TTPExecutor


class MockTTP(TTP):
    """Mock TTP for testing behaviors."""
    
    def __init__(self):
        super().__init__(
            name="Mock TTP",
            description="A mock TTP for testing behaviors"
        )
        self.payloads = ["test1", "test2", "test3"]
        self.execute_step_calls = []
        self.verify_result_calls = []
    
    def get_payloads(self):
        yield from self.payloads
    
    def execute_step(self, driver, payload):
        self.execute_step_calls.append(payload)
    
    def verify_result(self, driver):
        self.verify_result_calls.append(True)
        return False  # Always return False for testing


class TestBehaviorBase(unittest.TestCase):
    """Test the base Behavior class."""
    
    def test_behavior_abstract_methods(self):
        """Test that Behavior is abstract and cannot be instantiated."""
        # Verify that Behavior has abstract methods
        self.assertTrue(hasattr(Behavior, '__abstractmethods__'))
        self.assertGreater(len(Behavior.__abstractmethods__), 0)
    
    def test_behavior_configuration(self):
        """Test behavior configuration."""
        behavior = DefaultBehavior()
        config = {"test_param": "test_value", "number": 42}
        behavior.configure(config)
        
        self.assertEqual(behavior.config["test_param"], "test_value")
        self.assertEqual(behavior.config["number"], 42)
    
    def test_random_delay(self):
        """Test the random delay helper method."""
        behavior = DefaultBehavior()
        delay = behavior._random_delay(1.0, 2.0)
        
        self.assertGreaterEqual(delay, 1.0)
        self.assertLessEqual(delay, 2.0)


class TestDefaultBehavior(unittest.TestCase):
    """Test the DefaultBehavior class."""
    
    def setUp(self):
        self.behavior = DefaultBehavior(delay=1.5)
        self.mock_driver = Mock()
    
    def test_initialization(self):
        """Test DefaultBehavior initialization."""
        self.assertEqual(self.behavior.name, "Default Behavior")
        self.assertEqual(self.behavior.delay, 1.5)
    
    def test_get_step_delay(self):
        """Test step delay is consistent."""
        delay1 = self.behavior.get_step_delay(1)
        delay2 = self.behavior.get_step_delay(10)
        
        self.assertEqual(delay1, 1.5)
        self.assertEqual(delay2, 1.5)
    
    def test_should_continue(self):
        """Test that default behavior always continues."""
        self.assertTrue(self.behavior.should_continue(1, 0))
        self.assertTrue(self.behavior.should_continue(100, 50))
    
    def test_on_error(self):
        """Test that default behavior continues on error."""
        error = Exception("Test error")
        self.assertTrue(self.behavior.on_error(error, 1))
    
    def test_lifecycle_methods(self):
        """Test that lifecycle methods can be called without error."""
        try:
            self.behavior.pre_execution(self.mock_driver, "http://test.com")
            self.behavior.pre_step(self.mock_driver, "payload", 1)
            self.behavior.post_step(self.mock_driver, "payload", 1, True)
            self.behavior.post_execution(self.mock_driver, [])
        except Exception as e:
            self.fail(f"Lifecycle methods raised exception: {e}")


class TestHumanBehavior(unittest.TestCase):
    """Test the HumanBehavior class."""
    
    def setUp(self):
        self.behavior = HumanBehavior(
            base_delay=2.0,
            delay_variance=1.0,
            max_consecutive_failures=3
        )
        self.mock_driver = Mock()
    
    def test_initialization(self):
        """Test HumanBehavior initialization."""
        self.assertEqual(self.behavior.name, "Human Behavior")
        self.assertEqual(self.behavior.base_delay, 2.0)
        self.assertEqual(self.behavior.delay_variance, 1.0)
        self.assertEqual(self.behavior.max_consecutive_failures, 3)
    
    def test_variable_delay(self):
        """Test that delays are variable."""
        delays = [self.behavior.get_step_delay(i) for i in range(1, 11)]
        
        # Check that not all delays are the same (variability)
        self.assertGreater(len(set(delays)), 1)
        
        # Check that delays are reasonable
        for delay in delays:
            self.assertGreaterEqual(delay, 0.1)
            self.assertLess(delay, 10.0)
    
    def test_failure_handling(self):
        """Test human-like failure handling."""
        # Should continue with few failures
        self.assertTrue(self.behavior.should_continue(1, 1))
        self.assertTrue(self.behavior.should_continue(1, 2))
        
        # Should stop with many failures
        self.assertFalse(self.behavior.should_continue(1, 3))
        self.assertFalse(self.behavior.should_continue(1, 5))
    
    def test_comfort_factor(self):
        """Test that delays generally decrease as steps progress (comfort factor)."""
        # On average, later delays should be shorter due to comfort factor
        # We'll test this by taking multiple samples
        early_delays = [self.behavior.get_step_delay(1) for _ in range(10)]
        later_delays = [self.behavior.get_step_delay(20) for _ in range(10)]
        
        avg_early = sum(early_delays) / len(early_delays)
        avg_later = sum(later_delays) / len(later_delays)
        
        # Reset consecutive failures to ensure fair comparison
        self.behavior.consecutive_failures = 0
        
        # Later delays should generally be shorter due to comfort factor
        self.assertLess(avg_later, avg_early + 0.5)  # Allow some variance


class TestMachineBehavior(unittest.TestCase):
    """Test the MachineBehavior class."""
    
    def setUp(self):
        self.behavior = MachineBehavior(
            delay=0.5,
            max_retries=3,
            fail_fast=True
        )
        self.mock_driver = Mock()
    
    def test_initialization(self):
        """Test MachineBehavior initialization."""
        self.assertEqual(self.behavior.name, "Machine Behavior")
        self.assertEqual(self.behavior.delay, 0.5)
        self.assertEqual(self.behavior.max_retries, 3)
        self.assertTrue(self.behavior.fail_fast)
    
    def test_consistent_delay(self):
        """Test that delays are consistent."""
        delays = [self.behavior.get_step_delay(i) for i in range(1, 11)]
        
        # All delays should be exactly the same
        self.assertEqual(len(set(delays)), 1)
        self.assertEqual(delays[0], 0.5)
    
    def test_fail_fast_behavior(self):
        """Test fail-fast behavior."""
        # Should continue with few failures
        self.assertTrue(self.behavior.should_continue(1, 1))
        
        # Should stop with many failures when fail_fast is True
        self.assertFalse(self.behavior.should_continue(1, 4))
    
    def test_statistics(self):
        """Test statistics tracking."""
        stats = self.behavior.get_statistics()
        
        self.assertIn("total_errors", stats)
        self.assertIn("current_retry_count", stats)
        self.assertIn("execution_count", stats)
        self.assertEqual(stats["average_delay"], 0.5)
        self.assertEqual(stats["max_retries"], 3)


class TestStealthBehavior(unittest.TestCase):
    """Test the StealthBehavior class."""
    
    def setUp(self):
        self.behavior = StealthBehavior(
            min_delay=2.0,
            max_delay=5.0,
            burst_probability=0.1,
            max_requests_per_session=10
        )
        self.mock_driver = Mock()
    
    def test_initialization(self):
        """Test StealthBehavior initialization."""
        self.assertEqual(self.behavior.name, "Stealth Behavior")
        self.assertEqual(self.behavior.min_delay, 2.0)
        self.assertEqual(self.behavior.max_delay, 5.0)
        self.assertEqual(self.behavior.burst_probability, 0.1)
        self.assertEqual(self.behavior.max_requests_per_session, 10)
    
    def test_variable_delay_range(self):
        """Test that delays are within the specified range."""
        delays = [self.behavior.get_step_delay(i) for i in range(1, 21)]
        
        for delay in delays:
            # Should be at least min_delay (accounting for burst behavior)
            self.assertGreater(delay, 0.1)  # Burst delays can be shorter
            # Should generally be within reasonable bounds
            self.assertLess(delay, 20.0)  # With backoff, could be longer
    
    def test_conservative_failure_handling(self):
        """Test conservative failure handling."""
        # Should be more conservative than other behaviors
        self.assertFalse(self.behavior.should_continue(1, 2))
        
        # Simulate reaching max requests per session
        self.behavior.requests_in_session = 15
        self.assertFalse(self.behavior.should_continue(15, 0))  # Too many requests
    
    def test_session_management(self):
        """Test session request counting."""
        # Initially should allow requests
        self.assertEqual(self.behavior.requests_in_session, 0)
        
        # Simulate some requests
        for i in range(5):
            self.behavior.post_step(self.mock_driver, f"payload{i}", i+1, False)
        
        self.assertEqual(self.behavior.requests_in_session, 5)


class TestBehaviorIntegration(unittest.TestCase):
    """Test behavior integration with TTPExecutor."""
    
    def setUp(self):
        self.mock_ttp = MockTTP()
        self.mock_driver = Mock()
    
    def test_executor_with_behavior(self):
        """Test that TTPExecutor works with behaviors."""
        behavior = DefaultBehavior(delay=0.1)
        executor = TTPExecutor(
            ttp=self.mock_ttp,
            target_url="http://test.com",
            behavior=behavior
        )
        
        # Check that behavior is properly assigned
        self.assertEqual(executor.behavior, behavior)
        if executor.behavior:
            self.assertEqual(executor.behavior.name, "Default Behavior")
    
    def test_executor_without_behavior(self):
        """Test that TTPExecutor works without behaviors (backward compatibility)."""
        executor = TTPExecutor(
            ttp=self.mock_ttp,
            target_url="http://test.com"
        )
        
        # Check that behavior is None
        self.assertIsNone(executor.behavior)
    
    def test_behavior_lifecycle_integration(self):
        """Test that behavior lifecycle methods are called during execution."""
        behavior = Mock(spec=Behavior)
        behavior.name = "Mock Behavior"
        behavior.description = "Mock behavior for testing"
        behavior.get_step_delay.return_value = 0.1
        behavior.should_continue.return_value = True
        behavior.on_error.return_value = True
        
        executor = TTPExecutor(
            ttp=self.mock_ttp,
            target_url="http://test.com",
            behavior=behavior,
            headless=True
        )
        
        # Mock the driver setup to avoid actual browser instantiation
        executor.driver = self.mock_driver
        executor._setup_driver = Mock()
        executor._cleanup = Mock()
        
        # Mock TTP methods to avoid actual execution
        self.mock_ttp.verify_result = Mock(return_value=False)
        
        try:
            executor.run()
        except Exception:
            pass  # We expect some errors due to mocking
        
        # Verify that behavior methods were called
        behavior.pre_execution.assert_called_once()
        behavior.get_step_delay.assert_called()
        behavior.should_continue.assert_called()


def run_behavior_tests():
    """Run all behavior tests."""
    print("Running Scythe Behavior Tests...")
    print("=" * 50)
    
    # Create test suite
    test_classes = [
        TestBehaviorBase,
        TestDefaultBehavior,
        TestHumanBehavior,
        TestMachineBehavior,
        TestStealthBehavior,
        TestBehaviorIntegration
    ]
    
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All behavior tests passed!")
    else:
        print(f"❌ {len(result.failures)} failures, {len(result.errors)} errors")
        
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_behavior_tests()
    sys.exit(0 if success else 1)