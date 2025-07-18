import unittest
# Mock import removed as it's not used in this test file
import sys
import os
import time

# Add the scythe package to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.orchestrators.base import OrchestrationResult, OrchestrationStrategy, ExecutionContext
from scythe.orchestrators.scale import ScaleOrchestrator
from scythe.core.ttp import TTP
from scythe.journeys.base import Journey, Step, Action


class MockTTP(TTP):
    """Mock TTP for testing orchestrators."""
    
    def __init__(self, name: str, description: str, expected_result: bool = True, success_results = None):
        super().__init__(name, description, expected_result)
        self.success_results = success_results if success_results is not None else [True]
        self.current_step = 0
        
    def get_payloads(self):
        for i, result in enumerate(self.success_results):
            yield f"test_payload_{i}"
    
    def execute_step(self, driver, payload):
        pass
    
    def verify_result(self, driver):
        if self.current_step < len(self.success_results):
            result = self.success_results[self.current_step]
            self.current_step += 1
            return result
        return False


class MockAction(Action):
    """Mock action for testing."""
    
    def __init__(self, name: str, description: str, expected_result: bool = True, execution_result: bool = True):
        super().__init__(name, description, expected_result)
        self.execution_result = execution_result
        self.executed = False
        
    def execute(self, driver, context):
        self.executed = True
        return self.execution_result


class MockJourney(Journey):
    """Mock Journey for testing orchestrators."""
    
    def __init__(self, name: str, description: str, expected_result: bool = True, step_results = None):
        action = MockAction("Mock Action", "Mock Description", execution_result=True)
        step = Step("Mock Step", "Mock Description", actions=[action])
        super().__init__(name, description, steps=[step], expected_result=expected_result)
        self.step_results = step_results if step_results is not None else [True]


class TestOrchestrationResult(unittest.TestCase):
    """Test cases for OrchestrationResult."""
    
    def test_orchestration_result_creation(self):
        """Test OrchestrationResult creation and properties."""
        start_time = time.time()
        end_time = start_time + 10
        
        result = OrchestrationResult(
            orchestrator_name="Test Orchestrator",
            strategy=OrchestrationStrategy.PARALLEL,
            total_executions=10,
            successful_executions=8,
            failed_executions=2,
            start_time=start_time,
            end_time=end_time,
            execution_time=10.0,
            results=[],
            errors=[],
            metadata={}
        )
        
        self.assertEqual(result.orchestrator_name, "Test Orchestrator")
        self.assertEqual(result.strategy, OrchestrationStrategy.PARALLEL)
        self.assertEqual(result.total_executions, 10)
        self.assertEqual(result.successful_executions, 8)
        self.assertEqual(result.failed_executions, 2)
        self.assertEqual(result.success_rate, 80.0)
        self.assertEqual(result.average_execution_time, 1.0)
    
    def test_orchestration_result_summary(self):
        """Test OrchestrationResult summary generation."""
        result = OrchestrationResult(
            orchestrator_name="Test",
            strategy=OrchestrationStrategy.SEQUENTIAL,
            total_executions=5,
            successful_executions=3,
            failed_executions=2,
            start_time=0,
            end_time=5,
            execution_time=5.0,
            results=[],
            errors=["error1", "error2"],
            metadata={"test": "data"}
        )
        
        summary = result.summary()
        
        self.assertEqual(summary['orchestrator'], "Test")
        self.assertEqual(summary['strategy'], "sequential")
        self.assertEqual(summary['executions']['total'], 5)
        self.assertEqual(summary['executions']['successful'], 3)
        self.assertEqual(summary['executions']['success_rate'], "60.0%")
        self.assertEqual(summary['errors'], 2)
        self.assertEqual(summary['metadata'], {"test": "data"})


class TestExecutionContext(unittest.TestCase):
    """Test cases for ExecutionContext."""
    
    def test_execution_context_creation(self):
        """Test ExecutionContext creation."""
        context = ExecutionContext(
            execution_id="test-123",
            test_name="Test TTP",
            target_url="http://test.com",
            replication_number=1,
            total_replications=10,
            metadata={"batch": 1}
        )
        
        self.assertEqual(context.execution_id, "test-123")
        self.assertEqual(context.test_name, "Test TTP")
        self.assertEqual(context.target_url, "http://test.com")
        self.assertEqual(context.replication_number, 1)
        self.assertEqual(context.total_replications, 10)
        self.assertEqual(context.metadata["batch"], 1)
        self.assertIsNone(context.start_time)
        self.assertIsNone(context.end_time)
    
    def test_execution_context_timing(self):
        """Test ExecutionContext timing functionality."""
        context = ExecutionContext("test", "test", "http://test.com", 1, 1)
        
        # Test start
        context.start()
        self.assertIsNotNone(context.start_time)
        
        # Simulate some execution time
        time.sleep(0.01)
        
        # Test end
        context.end("success")
        self.assertIsNotNone(context.end_time)
        self.assertEqual(context.result, "success")
        self.assertGreater(context.execution_time, 0)
        self.assertTrue(context.is_successful)
    
    def test_execution_context_to_dict(self):
        """Test ExecutionContext to_dict conversion."""
        context = ExecutionContext("test", "test", "http://test.com", 1, 1)
        context.start()
        context.end({"success": True})
        
        result_dict = context.to_dict()
        
        self.assertIn('execution_id', result_dict)
        self.assertIn('test_name', result_dict)
        self.assertIn('execution_time', result_dict)
        self.assertTrue(result_dict['successful'])


class TestScaleOrchestrator(unittest.TestCase):
    """Test cases for ScaleOrchestrator."""
    
    def setUp(self):
        self.orchestrator = ScaleOrchestrator(
            name="Test Scale",
            max_workers=2,
            ramp_up_delay=0.01,
            cool_down_delay=0.01
        )
        self.mock_ttp = MockTTP("Test TTP", "Test Description", success_results=[True, False, True])
        self.mock_journey = MockJourney("Test Journey", "Test Description")
    
    def test_scale_orchestrator_ttp_sequential(self):
        """Test scale orchestrator with TTP in sequential mode."""
        self.orchestrator.strategy = OrchestrationStrategy.SEQUENTIAL
        
        result = self.orchestrator.orchestrate_ttp(
            ttp=self.mock_ttp,
            target_url="http://test.com",
            replications=3
        )
        
        self.assertEqual(result.total_executions, 3)
        self.assertGreater(result.successful_executions, 0)
        self.assertEqual(result.strategy, OrchestrationStrategy.SEQUENTIAL)
        self.assertEqual(result.orchestrator_name, "Test Scale")


if __name__ == '__main__':
    unittest.main()