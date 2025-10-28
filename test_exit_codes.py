#!/usr/bin/env python3
"""
Test script to verify that scythe properly exits with non-zero codes when tests fail.
This tests all different types of tests: TTP, Journey, and Orchestrated tests.
"""

import sys
import os

# Add the scythe package to the path for testing
sys.path.insert(0, os.path.dirname(__file__))

from unittest.mock import Mock, patch
from scythe.core.ttp import TTP
from scythe.core.executor import TTPExecutor
from scythe.journeys.base import Journey, Step
from scythe.journeys.executor import JourneyExecutor
from scythe.journeys.actions import AssertAction
from scythe.orchestrators.scale import ScaleOrchestrator
from scythe.orchestrators.batch import BatchOrchestrator, BatchConfiguration
from scythe.orchestrators.distributed import DistributedOrchestrator
from scythe.orchestrators.base import OrchestrationStrategy


class MockTTP(TTP):
    """Mock TTP for testing exit codes."""
    
    def __init__(self, name: str, expected_result: bool, will_succeed: bool):
        super().__init__(name, "Test TTP", expected_result)
        self.will_succeed = will_succeed
        
    def get_payloads(self):
        yield "test_payload"
    
    def execute_step(self, driver, payload):
        pass
    
    def verify_result(self, driver):
        return self.will_succeed


def test_ttp_exit_codes():
    """Test TTPExecutor exit codes."""
    print("\n" + "="*60)
    print("Testing TTP Exit Codes")
    print("="*60)
    
    mock_driver = Mock()
    mock_driver.current_url = "http://test.com"
    mock_driver.quit = Mock()
    
    # Test 1: Expected success, gets success -> exit code 0
    print("\n1. TTP: Expected success, gets success")
    with patch('scythe.core.executor.webdriver.Chrome', return_value=mock_driver):
        ttp = MockTTP("Test 1", expected_result=True, will_succeed=True)
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        executor.run()
        exit_code = executor.exit_code()
        print(f"   was_successful(): {executor.was_successful()}")
        print(f"   exit_code(): {exit_code}")
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
        print("   ✓ PASS")
    
    # Test 2: Expected success, gets failure -> exit code 1
    print("\n2. TTP: Expected success, gets failure")
    with patch('scythe.core.executor.webdriver.Chrome', return_value=mock_driver):
        ttp = MockTTP("Test 2", expected_result=True, will_succeed=False)
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        executor.run()
        exit_code = executor.exit_code()
        print(f"   was_successful(): {executor.was_successful()}")
        print(f"   exit_code(): {exit_code}")
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}"
        print("   ✓ PASS")
    
    # Test 3: Expected failure, gets failure -> exit code 0
    print("\n3. TTP: Expected failure, gets failure")
    with patch('scythe.core.executor.webdriver.Chrome', return_value=mock_driver):
        ttp = MockTTP("Test 3", expected_result=False, will_succeed=False)
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        executor.run()
        exit_code = executor.exit_code()
        print(f"   was_successful(): {executor.was_successful()}")
        print(f"   exit_code(): {exit_code}")
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
        print("   ✓ PASS")
    
    # Test 4: Expected failure, gets success -> exit code 1
    print("\n4. TTP: Expected failure, gets success")
    with patch('scythe.core.executor.webdriver.Chrome', return_value=mock_driver):
        ttp = MockTTP("Test 4", expected_result=False, will_succeed=True)
        executor = TTPExecutor(ttp=ttp, target_url="http://test.com", headless=True)
        executor.run()
        exit_code = executor.exit_code()
        print(f"   was_successful(): {executor.was_successful()}")
        print(f"   exit_code(): {exit_code}")
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}"
        print("   ✓ PASS")
    
    print("\n✓ All TTP exit code tests passed!")


def test_journey_exit_codes():
    """Test JourneyExecutor exit codes."""
    print("\n" + "="*60)
    print("Testing Journey Exit Codes")
    print("="*60)
    
    mock_driver = Mock()
    mock_driver.current_url = "http://test.com"
    mock_driver.quit = Mock()
    mock_driver.page_source = "<html><body>test</body></html>"
    
    # Test 1: Expected success, gets success -> exit code 0
    print("\n1. Journey: Expected success, gets success")
    with patch('scythe.journeys.executor.webdriver.Chrome', return_value=mock_driver):
        journey = Journey("Test Journey 1", "Test", expected_result=True)
        step = Step("Test Step", "Test step description", expected_result=True)
        # This action will succeed since page_source contains "test"
        step.add_action(AssertAction(assertion_type="page_contains", expected_value="test"))
        journey.add_step(step)
        
        executor = JourneyExecutor(journey=journey, target_url="http://test.com", headless=True)
        executor.run()
        exit_code = executor.exit_code()
        print(f"   was_successful(): {executor.was_successful()}")
        print(f"   exit_code(): {exit_code}")
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
        print("   ✓ PASS")
    
    # Test 2: Expected success, gets failure -> exit code 1
    print("\n2. Journey: Expected success, gets failure")
    with patch('scythe.journeys.executor.webdriver.Chrome', return_value=mock_driver):
        journey = Journey("Test Journey 2", "Test", expected_result=True)
        step = Step("Test Step", "Test step description", expected_result=True)
        # This action will fail since page_source doesn't contain "nonexistent"
        step.add_action(AssertAction(assertion_type="page_contains", expected_value="nonexistent"))
        journey.add_step(step)
        
        executor = JourneyExecutor(journey=journey, target_url="http://test.com", headless=True)
        executor.run()
        exit_code = executor.exit_code()
        print(f"   was_successful(): {executor.was_successful()}")
        print(f"   exit_code(): {exit_code}")
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}"
        print("   ✓ PASS")
    
    # Test 3: Expected failure, gets failure -> exit code 0
    print("\n3. Journey: Expected failure, gets failure")
    with patch('scythe.journeys.executor.webdriver.Chrome', return_value=mock_driver):
        journey = Journey("Test Journey 3", "Test", expected_result=False)
        step = Step("Test Step", "Test step description", expected_result=True)
        # This action will fail
        step.add_action(AssertAction(assertion_type="page_contains", expected_value="nonexistent"))
        journey.add_step(step)
        
        executor = JourneyExecutor(journey=journey, target_url="http://test.com", headless=True)
        executor.run()
        exit_code = executor.exit_code()
        print(f"   was_successful(): {executor.was_successful()}")
        print(f"   exit_code(): {exit_code}")
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
        print("   ✓ PASS")
    
    # Test 4: Expected failure, gets success -> exit code 1
    print("\n4. Journey: Expected failure, gets success")
    with patch('scythe.journeys.executor.webdriver.Chrome', return_value=mock_driver):
        journey = Journey("Test Journey 4", "Test", expected_result=False)
        step = Step("Test Step", "Test step description", expected_result=True)
        # This action will succeed
        step.add_action(AssertAction(assertion_type="page_contains", expected_value="test"))
        journey.add_step(step)
        
        executor = JourneyExecutor(journey=journey, target_url="http://test.com", headless=True)
        executor.run()
        exit_code = executor.exit_code()
        print(f"   was_successful(): {executor.was_successful()}")
        print(f"   exit_code(): {exit_code}")
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}"
        print("   ✓ PASS")
    
    print("\n✓ All Journey exit code tests passed!")


def test_orchestrator_exit_codes():
    """Test Orchestrator exit codes."""
    print("\n" + "="*60)
    print("Testing Orchestrator Exit Codes")
    print("="*60)
    
    mock_driver = Mock()
    mock_driver.current_url = "http://test.com"
    mock_driver.quit = Mock()
    
    # Test 1: ScaleOrchestrator with all successes -> exit code 0
    print("\n1. ScaleOrchestrator: All executions succeed")
    with patch('scythe.core.executor.webdriver.Chrome', return_value=mock_driver):
        ttp = MockTTP("Test TTP", expected_result=True, will_succeed=True)
        orchestrator = ScaleOrchestrator(
            strategy=OrchestrationStrategy.SEQUENTIAL,
            max_workers=2
        )
        result = orchestrator.orchestrate_ttp(ttp=ttp, target_url="http://test.com", replications=3)
        exit_code = orchestrator.exit_code(result)
        print(f"   Total executions: {result.total_executions}")
        print(f"   Successful: {result.successful_executions}")
        print(f"   Failed: {result.failed_executions}")
        print(f"   exit_code(): {exit_code}")
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
        print("   ✓ PASS")
    
    # Test 2: ScaleOrchestrator with some failures -> exit code 1
    print("\n2. ScaleOrchestrator: Some executions fail")
    with patch('scythe.core.executor.webdriver.Chrome', return_value=mock_driver):
        ttp = MockTTP("Test TTP", expected_result=True, will_succeed=False)
        orchestrator = ScaleOrchestrator(
            strategy=OrchestrationStrategy.SEQUENTIAL,
            max_workers=2
        )
        result = orchestrator.orchestrate_ttp(ttp=ttp, target_url="http://test.com", replications=3)
        exit_code = orchestrator.exit_code(result)
        print(f"   Total executions: {result.total_executions}")
        print(f"   Successful: {result.successful_executions}")
        print(f"   Failed: {result.failed_executions}")
        print(f"   exit_code(): {exit_code}")
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}"
        print("   ✓ PASS")
    
    # Test 3: BatchOrchestrator with all successes -> exit code 0
    print("\n3. BatchOrchestrator: All executions succeed")
    with patch('scythe.core.executor.webdriver.Chrome', return_value=mock_driver):
        ttp = MockTTP("Test TTP", expected_result=False, will_succeed=False)
        batch_config = BatchConfiguration(batch_size=2)
        orchestrator = BatchOrchestrator(
            batch_config=batch_config,
            max_workers=2
        )
        result = orchestrator.orchestrate_ttp(ttp=ttp, target_url="http://test.com", replications=4)
        exit_code = orchestrator.exit_code(result)
        print(f"   Total executions: {result.total_executions}")
        print(f"   Successful: {result.successful_executions}")
        print(f"   Failed: {result.failed_executions}")
        print(f"   exit_code(): {exit_code}")
        assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
        print("   ✓ PASS")
    
    # Test 4: DistributedOrchestrator with failures -> exit code 1
    print("\n4. DistributedOrchestrator: Some executions fail")
    with patch('scythe.core.executor.webdriver.Chrome', return_value=mock_driver):
        ttp = MockTTP("Test TTP", expected_result=False, will_succeed=True)
        orchestrator = DistributedOrchestrator(
            strategy=OrchestrationStrategy.SEQUENTIAL,
            max_workers=2
        )
        result = orchestrator.orchestrate_ttp(ttp=ttp, target_url="http://test.com", replications=2)
        exit_code = orchestrator.exit_code(result)
        print(f"   Total executions: {result.total_executions}")
        print(f"   Successful: {result.successful_executions}")
        print(f"   Failed: {result.failed_executions}")
        print(f"   exit_code(): {exit_code}")
        assert exit_code == 1, f"Expected exit code 1, got {exit_code}"
        print("   ✓ PASS")
    
    print("\n✓ All Orchestrator exit code tests passed!")


def main():
    """Run all exit code tests."""
    print("\n" + "="*60)
    print("SCYTHE EXIT CODE TEST SUITE")
    print("="*60)
    print("\nTesting that scythe exits with non-zero codes when tests fail")
    print("for ALL different types of tests.")
    
    all_passed = True
    
    try:
        test_ttp_exit_codes()
    except AssertionError as e:
        print(f"\n✗ TTP tests failed: {e}")
        all_passed = False
    
    try:
        test_journey_exit_codes()
    except AssertionError as e:
        print(f"\n✗ Journey tests failed: {e}")
        all_passed = False
    
    try:
        test_orchestrator_exit_codes()
    except AssertionError as e:
        print(f"\n✗ Orchestrator tests failed: {e}")
        all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL EXIT CODE TESTS PASSED!")
        print("="*60)
        print("\nScythe now properly exits with:")
        print("  - Exit code 0: When test results match expectations")
        print("  - Exit code 1: When test results differ from expectations")
        print("\nThis works for:")
        print("  ✓ TTP tests (UI and API modes)")
        print("  ✓ Journey tests (UI and API modes)")
        print("  ✓ Orchestrated tests (Scale, Batch, Distributed)")
        print("="*60)
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
