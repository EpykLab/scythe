import unittest
from unittest.mock import Mock, patch
import sys
import os
import time

# Add the scythe package to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.journeys.base import Journey, Step, Action
from scythe.journeys.actions import NavigateAction, ClickAction, FillFormAction, WaitAction, TTPAction, AssertAction
from scythe.journeys.executor import JourneyExecutor
from scythe.core.ttp import TTP
from scythe.auth.base import Authentication


class MockAction(Action):
    """Mock action for testing."""
    
    def __init__(self, name: str, description: str, expected_result: bool = True, execution_result: bool = True):
        super().__init__(name, description, expected_result)
        self.execution_result = execution_result
        self.executed = False
        
    def execute(self, driver, context):
        self.executed = True
        self.store_result('execution_time', time.time())
        return self.execution_result


class MockTTP(TTP):
    """Mock TTP for testing TTPAction."""
    
    def __init__(self, name: str, description: str, expected_result: bool = True, should_succeed = None):
        super().__init__(name, description, expected_result)
        self.success_results = should_succeed if should_succeed is not None else [True]
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


class MockAuthentication(Authentication):
    """Mock authentication for testing."""
    
    def __init__(self, name: str, description: str, auth_success: bool = True):
        super().__init__(name, description)
        self.auth_success = auth_success
        self.auth_called = False
        
    def authenticate(self, driver, target_url):
        self.auth_called = True
        self.authenticated = self.auth_success
        return self.auth_success
    
    def is_authenticated(self, driver):
        return self.authenticated


class TestAction(unittest.TestCase):
    """Test cases for Action base class."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.context = {}
    
    def test_action_initialization(self):
        """Test Action initialization."""
        action = MockAction("Test Action", "Test Description")
        
        self.assertEqual(action.name, "Test Action")
        self.assertEqual(action.description, "Test Description")
        self.assertTrue(action.expected_result)
        self.assertEqual(action.execution_data, {})
    
    def test_action_execution(self):
        """Test action execution."""
        action = MockAction("Test Action", "Test Description", execution_result=True)
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)
        self.assertTrue(action.executed)
        self.assertIn('execution_time', action.execution_data)
    
    def test_action_store_and_get_result(self):
        """Test storing and retrieving action results."""
        action = MockAction("Test Action", "Test Description")
        
        action.store_result("test_key", "test_value")
        self.assertEqual(action.get_result("test_key"), "test_value")
        self.assertEqual(action.get_result("nonexistent", "default"), "default")
    
    def test_action_validate_prerequisites(self):
        """Test prerequisite validation."""
        action = MockAction("Test Action", "Test Description")
        
        # Default implementation should return True
        self.assertTrue(action.validate_prerequisites(self.context))


class TestStep(unittest.TestCase):
    """Test cases for Step class."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.context = {}
    
    def test_step_initialization(self):
        """Test Step initialization."""
        action1 = MockAction("Action 1", "First action")
        action2 = MockAction("Action 2", "Second action")
        
        step = Step("Test Step", "Test Description", actions=[action1, action2])
        
        self.assertEqual(step.name, "Test Step")
        self.assertEqual(step.description, "Test Description")
        self.assertEqual(len(step.actions), 2)
        self.assertFalse(step.continue_on_failure)
        self.assertTrue(step.expected_result)
    
    def test_step_add_action(self):
        """Test adding actions to step."""
        step = Step("Test Step", "Test Description")
        action = MockAction("Test Action", "Test Description")
        
        step.add_action(action)
        
        self.assertEqual(len(step.actions), 1)
        self.assertEqual(step.actions[0], action)
    
    def test_step_execution_success(self):
        """Test successful step execution."""
        action1 = MockAction("Action 1", "First action", execution_result=True)
        action2 = MockAction("Action 2", "Second action", execution_result=True)
        
        step = Step("Test Step", "Test Description", actions=[action1, action2])
        
        with patch('logging.getLogger'):
            result = step.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)
        self.assertTrue(action1.executed)
        self.assertTrue(action2.executed)
        self.assertEqual(len(step.execution_results), 2)
    
    def test_step_execution_failure_no_continue(self):
        """Test step execution with failure and no continue_on_failure."""
        action1 = MockAction("Action 1", "First action", execution_result=True)
        action2 = MockAction("Action 2", "Second action", execution_result=False)
        action3 = MockAction("Action 3", "Third action", execution_result=True)
        
        step = Step("Test Step", "Test Description", actions=[action1, action2, action3], continue_on_failure=False)
        
        with patch('logging.getLogger'):
            result = step.execute(self.mock_driver, self.context)
        
        self.assertFalse(result)
        self.assertTrue(action1.executed)
        self.assertTrue(action2.executed)
        self.assertFalse(action3.executed)  # Should not execute after failure
    
    def test_step_execution_failure_with_continue(self):
        """Test step execution with failure and continue_on_failure."""
        action1 = MockAction("Action 1", "First action", execution_result=True)
        action2 = MockAction("Action 2", "Second action", execution_result=False)
        action3 = MockAction("Action 3", "Third action", execution_result=True)
        
        step = Step("Test Step", "Test Description", actions=[action1, action2, action3], continue_on_failure=True)
        
        with patch('logging.getLogger'):
            result = step.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)  # Should succeed because we have successes
        self.assertTrue(action1.executed)
        self.assertTrue(action2.executed)
        self.assertTrue(action3.executed)  # Should execute despite previous failure
    
    def test_step_store_and_get_data(self):
        """Test storing and retrieving step data."""
        step = Step("Test Step", "Test Description")
        
        step.store_data("test_key", "test_value")
        self.assertEqual(step.get_data("test_key"), "test_value")
        self.assertEqual(step.get_data("nonexistent", "default"), "default")


class TestJourney(unittest.TestCase):
    """Test cases for Journey class."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_driver.current_url = "http://test.com"
    
    def test_journey_initialization(self):
        """Test Journey initialization."""
        step1 = Step("Step 1", "First step")
        step2 = Step("Step 2", "Second step")
        
        journey = Journey("Test Journey", "Test Description", steps=[step1, step2])
        
        self.assertEqual(journey.name, "Test Journey")
        self.assertEqual(journey.description, "Test Description")
        self.assertEqual(len(journey.steps), 2)
        self.assertTrue(journey.expected_result)
        self.assertIsNone(journey.authentication)
        self.assertEqual(journey.context, {})
    
    def test_journey_add_step(self):
        """Test adding steps to journey."""
        journey = Journey("Test Journey", "Test Description")
        step = Step("Test Step", "Test Description")
        
        journey.add_step(step)
        
        self.assertEqual(len(journey.steps), 1)
        self.assertEqual(journey.steps[0], step)
    
    def test_journey_context_management(self):
        """Test journey context management."""
        journey = Journey("Test Journey", "Test Description")
        
        journey.set_context("test_key", "test_value")
        self.assertEqual(journey.get_context("test_key"), "test_value")
        self.assertEqual(journey.get_context("nonexistent", "default"), "default")
        
        journey.clear_context()
        self.assertEqual(journey.context, {})
    
    def test_journey_requires_authentication(self):
        """Test authentication requirement check."""
        journey = Journey("Test Journey", "Test Description")
        self.assertFalse(journey.requires_authentication())
        
        auth = MockAuthentication("Test Auth", "Test Description")
        journey_with_auth = Journey("Test Journey", "Test Description", authentication=auth)
        self.assertTrue(journey_with_auth.requires_authentication())
    
    def test_journey_authentication_success(self):
        """Test successful journey authentication."""
        auth = MockAuthentication("Test Auth", "Test Description", auth_success=True)
        journey = Journey("Test Journey", "Test Description", authentication=auth)
        
        result = journey.authenticate(self.mock_driver, "http://test.com")
        
        self.assertTrue(result)
        self.assertTrue(auth.auth_called)
    
    def test_journey_authentication_failure(self):
        """Test failed journey authentication."""
        auth = MockAuthentication("Test Auth", "Test Description", auth_success=False)
        journey = Journey("Test Journey", "Test Description", authentication=auth)
        
        with patch('logging.getLogger'):
            result = journey.authenticate(self.mock_driver, "http://test.com")
        
        self.assertFalse(result)
        self.assertTrue(auth.auth_called)
    
    def test_journey_execution_success(self):
        """Test successful journey execution."""
        action1 = MockAction("Action 1", "First action", execution_result=True)
        action2 = MockAction("Action 2", "Second action", execution_result=True)
        step = Step("Test Step", "Test Description", actions=[action1, action2])
        
        journey = Journey("Test Journey", "Test Description", steps=[step])
        
        with patch('logging.getLogger'):
            results = journey.execute(self.mock_driver, "http://test.com")
        
        self.assertTrue(results['overall_success'])
        self.assertEqual(results['steps_executed'], 1)
        self.assertEqual(results['steps_succeeded'], 1)
        self.assertEqual(results['steps_failed'], 0)
        self.assertEqual(results['actions_executed'], 2)
        self.assertEqual(results['actions_succeeded'], 2)
    
    def test_journey_execution_with_authentication(self):
        """Test journey execution with authentication."""
        auth = MockAuthentication("Test Auth", "Test Description", auth_success=True)
        action = MockAction("Action 1", "First action", execution_result=True)
        step = Step("Test Step", "Test Description", actions=[action])
        
        journey = Journey("Test Journey", "Test Description", steps=[step], authentication=auth)
        
        with patch('logging.getLogger'):
            results = journey.execute(self.mock_driver, "http://test.com")
        
        self.assertTrue(results['overall_success'])
        self.assertTrue(auth.auth_called)
    
    def test_journey_execution_auth_failure(self):
        """Test journey execution with authentication failure."""
        auth = MockAuthentication("Test Auth", "Test Description", auth_success=False)
        action = MockAction("Action 1", "First action", execution_result=True)
        step = Step("Test Step", "Test Description", actions=[action])
        
        journey = Journey("Test Journey", "Test Description", steps=[step], authentication=auth)
        
        with patch('logging.getLogger'):
            results = journey.execute(self.mock_driver, "http://test.com")
        
        self.assertFalse(results['overall_success'])
        self.assertTrue(auth.auth_called)
        self.assertEqual(results['steps_executed'], 0)  # Should not execute steps
        self.assertIn("Authentication failed", results['errors'])
    
    def test_journey_store_and_get_data(self):
        """Test storing and retrieving journey data."""
        journey = Journey("Test Journey", "Test Description")
        
        journey.store_data("test_key", "test_value")
        self.assertEqual(journey.get_data("test_key"), "test_value")
        self.assertEqual(journey.get_data("nonexistent", "default"), "default")


class TestNavigateAction(unittest.TestCase):
    """Test cases for NavigateAction."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_driver.current_url = "http://test.com/target"
        self.context = {}
    
    def test_navigate_action_success(self):
        """Test successful navigation."""
        action = NavigateAction("http://test.com")
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)
        self.mock_driver.get.assert_called_once_with("http://test.com")
        self.assertEqual(self.context['current_url'], "http://test.com/target")
        self.assertEqual(action.get_result('navigated_url'), "http://test.com")
    
    def test_navigate_action_with_template(self):
        """Test navigation with URL template."""
        self.context['base_url'] = "http://test.com"
        self.context['path'] = "/login"
        
        action = NavigateAction("{base_url}{path}")
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)
        self.mock_driver.get.assert_called_once_with("http://test.com/login")
    
    def test_navigate_action_failure(self):
        """Test navigation failure."""
        self.mock_driver.get.side_effect = Exception("Navigation failed")
        
        action = NavigateAction("http://test.com")
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertFalse(result)
        self.assertEqual(action.get_result('error'), "Navigation failed")


class TestClickAction(unittest.TestCase):
    """Test cases for ClickAction."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_driver.current_url = "http://test.com"
        self.context = {}
        
        # Mock WebDriverWait and element
        self.mock_element = Mock()
        self.mock_element.tag_name = "button"
        self.mock_element.text = "Click me"
        
    @patch('scythe.journeys.actions.WebDriverWait')
    def test_click_action_success(self, mock_wait):
        """Test successful click action."""
        mock_wait.return_value.until.return_value = self.mock_element
        
        action = ClickAction("#submit-button")
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)
        self.mock_element.click.assert_called_once()
        self.assertEqual(action.get_result('element_tag'), "button")
        self.assertEqual(action.get_result('element_text'), "Click me")
    
    @patch('scythe.journeys.actions.WebDriverWait')
    def test_click_action_timeout(self, mock_wait):
        """Test click action timeout."""
        from selenium.common.exceptions import TimeoutException
        mock_wait.return_value.until.side_effect = TimeoutException()
        
        action = ClickAction("#submit-button")
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertFalse(result)
        self.assertIn("Element not found or not clickable", action.get_result('error'))
    
    def test_click_action_invalid_selector_type(self):
        """Test click action with invalid selector type."""
        action = ClickAction("#submit-button", selector_type="invalid")
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertFalse(result)
        self.assertEqual(action.get_result('error'), "Unsupported selector type: invalid")


class TestFillFormAction(unittest.TestCase):
    """Test cases for FillFormAction."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.context = {'username': 'testuser'}
        
        # Mock form elements
        self.mock_username_field = Mock()
        self.mock_password_field = Mock()
        self.mock_password_field.get_attribute.return_value = "password"
    
    @patch('scythe.journeys.actions.WebDriverWait')
    def test_fill_form_success(self, mock_wait):
        """Test successful form filling."""
        mock_wait.return_value.until.side_effect = [self.mock_username_field, self.mock_password_field]
        
        field_data = {
            "#username": "{username}",
            "#password": "testpass"
        }
        
        action = FillFormAction(field_data)
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)
        self.mock_username_field.clear.assert_called_once()
        self.mock_username_field.send_keys.assert_called_with("testuser")
        self.mock_password_field.clear.assert_called_once()
        self.mock_password_field.send_keys.assert_called_with("testpass")
        
        filled_fields = action.get_result('filled_fields')
        self.assertEqual(len(filled_fields), 2)
        self.assertEqual(action.get_result('fields_failed'), 0)
    
    @patch('scythe.journeys.actions.WebDriverWait')
    def test_fill_form_partial_failure(self, mock_wait):
        """Test form filling with some field failures."""
        from selenium.common.exceptions import TimeoutException
        mock_wait.return_value.until.side_effect = [self.mock_username_field, TimeoutException()]
        
        field_data = {
            "#username": "testuser",
            "#password": "testpass"
        }
        
        action = FillFormAction(field_data)
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertFalse(result)
        self.assertEqual(action.get_result('fields_filled'), 1)
        self.assertEqual(action.get_result('fields_failed'), 1)


class TestWaitAction(unittest.TestCase):
    """Test cases for WaitAction."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.context = {}
    
    @patch('time.sleep')
    def test_wait_time_action(self, mock_sleep):
        """Test time-based wait action."""
        action = WaitAction(wait_type="time", duration=2.0)
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)
        mock_sleep.assert_called_once_with(2.0)
        self.assertEqual(action.get_result('wait_time'), 2.0)
    
    @patch('scythe.journeys.actions.WebDriverWait')
    def test_wait_element_action_success(self, mock_wait):
        """Test successful element wait action."""
        mock_element = Mock()
        mock_element.text = "Element text"
        mock_wait.return_value.until.return_value = mock_element
        
        action = WaitAction(wait_type="element", selector="#target", condition="presence", duration=10.0)
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)
        self.assertTrue(action.get_result('element_found'))
        self.assertEqual(action.get_result('element_text'), "Element text")
    
    @patch('scythe.journeys.actions.WebDriverWait')
    def test_wait_element_action_timeout(self, mock_wait):
        """Test element wait action timeout."""
        from selenium.common.exceptions import TimeoutException
        mock_wait.return_value.until.side_effect = TimeoutException()
        
        action = WaitAction(wait_type="element", selector="#target", duration=5.0)
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertFalse(result)
        self.assertIn("Wait condition not met", action.get_result('error'))
    
    def test_wait_unsupported_type(self):
        """Test wait action with unsupported type."""
        action = WaitAction(wait_type="unsupported")
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertFalse(result)
        self.assertEqual(action.get_result('error'), "Unsupported wait type: unsupported")


class TestTTPAction(unittest.TestCase):
    """Test cases for TTPAction."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_driver.current_url = "http://test.com"
        self.context = {'current_url': 'http://test.com'}
    
    def test_ttp_action_success(self):
        """Test successful TTP action execution."""
        ttp = MockTTP("Test TTP", "Test Description", should_succeed=[True, False, True])
        action = TTPAction(ttp)
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)  # Expected to pass and got successes
        self.assertEqual(action.get_result('total_payloads'), 3)
        self.assertEqual(action.get_result('successful_payloads'), 2)
        self.assertEqual(action.get_result('success_rate'), 2/3)
    
    def test_ttp_action_expect_fail(self):
        """Test TTP action expecting failure."""
        ttp = MockTTP("Test TTP", "Test Description", should_succeed=[False, False, False])
        action = TTPAction(ttp, expected_result=False)  # Expecting TTP to fail
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)  # Expected to fail and got no successes
        self.assertEqual(action.get_result('successful_payloads'), 0)
    
    def test_ttp_action_with_authentication(self):
        """Test TTP action with authentication."""
        auth = MockAuthentication("Test Auth", "Test Description", auth_success=True)
        ttp = MockTTP("Test TTP", "Test Description", should_succeed=[True, True, True])
        ttp.authentication = auth
        
        action = TTPAction(ttp)
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)
        self.assertTrue(auth.auth_called)
    
    def test_ttp_action_auth_failure(self):
        """Test TTP action with authentication failure."""
        auth = MockAuthentication("Test Auth", "Test Description", auth_success=False)
        ttp = MockTTP("Test TTP", "Test Description")
        ttp.authentication = auth
        
        action = TTPAction(ttp)
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertFalse(result)
        self.assertEqual(action.get_result('error'), 'TTP authentication failed')


class TestAssertAction(unittest.TestCase):
    """Test cases for AssertAction."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_driver.current_url = "http://test.com/dashboard"
        self.mock_driver.page_source = "<html><body>Welcome to dashboard</body></html>"
        self.context = {'test_value': 'expected'}
    
    def test_assert_url_contains_success(self):
        """Test successful URL contains assertion."""
        action = AssertAction("url_contains", "dashboard")
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)
        self.assertTrue(action.get_result('assertion_passed'))
        self.assertEqual(action.get_result('actual_value'), "http://test.com/dashboard")
    
    def test_assert_url_contains_failure(self):
        """Test failed URL contains assertion."""
        action = AssertAction("url_contains", "login")
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertFalse(result)
        self.assertFalse(action.get_result('assertion_passed'))
    
    def test_assert_page_contains_success(self):
        """Test successful page contains assertion."""
        action = AssertAction("page_contains", "Welcome")
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)
        self.assertTrue(action.get_result('assertion_passed'))
    
    def test_assert_context_value_success(self):
        """Test successful context value assertion."""
        action = AssertAction("context_value", "expected", context_key="test_value")
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)
        self.assertTrue(action.get_result('assertion_passed'))
        self.assertEqual(action.get_result('actual_value'), "expected")
    
    def test_assert_context_value_failure(self):
        """Test failed context value assertion."""
        action = AssertAction("context_value", "different", context_key="test_value")
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertFalse(result)
        self.assertFalse(action.get_result('assertion_passed'))
    
    def test_assert_element_present_success(self):
        """Test successful element present assertion."""
        mock_element = Mock()
        self.mock_driver.find_element.return_value = mock_element
        
        action = AssertAction("element_present", "true", selector="#target")
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertTrue(result)
        self.assertTrue(action.get_result('assertion_passed'))
    
    def test_assert_unsupported_type(self):
        """Test assertion with unsupported type."""
        action = AssertAction("unsupported", "value")
        
        result = action.execute(self.mock_driver, self.context)
        
        self.assertFalse(result)
        self.assertEqual(action.get_result('error'), "Unsupported assertion type: unsupported")


class TestJourneyExecutor(unittest.TestCase):
    """Test cases for JourneyExecutor."""
    
    def setUp(self):
        self.mock_driver = Mock()
        self.mock_driver.current_url = "http://test.com"
        self.mock_driver.quit = Mock()
    
    @patch('scythe.journeys.executor.webdriver.Chrome')
    def test_executor_successful_journey(self, mock_webdriver):
        """Test successful journey execution."""
        mock_webdriver.return_value = self.mock_driver
        
        action = MockAction("Test Action", "Test Description", execution_result=True)
        step = Step("Test Step", "Test Description", actions=[action])
        journey = Journey("Test Journey", "Test Description", steps=[step])
        
        executor = JourneyExecutor(journey=journey, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger'):
            results = executor.run()
        
        self.assertIsNotNone(results)
        self.assertTrue(results['overall_success'])
        self.assertEqual(results['steps_executed'], 1)
        self.assertEqual(results['steps_succeeded'], 1)
        self.assertEqual(results['actions_executed'], 1)
        self.assertEqual(results['actions_succeeded'], 1)
    
    @patch('scythe.journeys.executor.webdriver.Chrome')
    def test_executor_failed_journey(self, mock_webdriver):
        """Test failed journey execution."""
        mock_webdriver.return_value = self.mock_driver
        
        action = MockAction("Test Action", "Test Description", execution_result=False)
        step = Step("Test Step", "Test Description", actions=[action])
        journey = Journey("Test Journey", "Test Description", steps=[step])
        
        executor = JourneyExecutor(journey=journey, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger'):
            results = executor.run()
        
        self.assertIsNotNone(results)
        self.assertFalse(results['overall_success'])
        self.assertEqual(results['steps_executed'], 1)
        self.assertEqual(results['steps_failed'], 1)
        self.assertEqual(results['actions_executed'], 1)
        self.assertEqual(results['actions_failed'], 1)
    
    @patch('scythe.journeys.executor.webdriver.Chrome')
    def test_executor_journey_with_authentication(self, mock_webdriver):
        """Test journey executor with authentication."""
        mock_webdriver.return_value = self.mock_driver
        
        auth = MockAuthentication("Test Auth", "Test Description", auth_success=True)
        action = MockAction("Test Action", "Test Description", execution_result=True)
        step = Step("Test Step", "Test Description", actions=[action])
        journey = Journey("Test Journey", "Test Description", steps=[step], authentication=auth)
        
        executor = JourneyExecutor(journey=journey, target_url="http://test.com", headless=True)
        
        with patch.object(executor, 'logger'):
            results = executor.run()
        
        self.assertTrue(auth.auth_called)
        self.assertTrue(results['overall_success'])
    
    def test_executor_was_successful(self):
        """Test executor success check method."""
        executor = JourneyExecutor(
            journey=Journey("Test", "Test"),
            target_url="http://test.com"
        )
        
        # No results yet
        self.assertFalse(executor.was_successful())
        
        # Mock successful results
        executor.execution_results = {
            'overall_success': True,
            'expected_result': True
        }
        self.assertTrue(executor.was_successful())
        
        # Mock failed results
        executor.execution_results = {
            'overall_success': False,
            'expected_result': True
        }
        self.assertFalse(executor.was_successful())
        
        # Mock expected failure
        executor.execution_results = {
            'overall_success': False,
            'expected_result': False
        }
        self.assertTrue(executor.was_successful())
    
    def test_executor_get_results(self):
        """Test getting execution results."""
        executor = JourneyExecutor(
            journey=Journey("Test", "Test"),
            target_url="http://test.com"
        )
        
        # No results initially
        self.assertIsNone(executor.get_results())
        
        # Mock results
        mock_results = {'test': 'data'}
        executor.execution_results = mock_results
        self.assertEqual(executor.get_results(), mock_results)
    
    def test_executor_get_step_results(self):
        """Test getting step results."""
        executor = JourneyExecutor(
            journey=Journey("Test", "Test"),
            target_url="http://test.com"
        )
        
        # No results initially
        self.assertEqual(executor.get_step_results(), [])
        
        # Mock results with step data
        executor.execution_results = {
            'step_results': [
                {'step_name': 'Step 1', 'actual': True},
                {'step_name': 'Step 2', 'actual': False}
            ]
        }
        
        step_results = executor.get_step_results()
        self.assertEqual(len(step_results), 2)
        self.assertEqual(step_results[0]['step_name'], 'Step 1')
    
    def test_executor_get_action_results(self):
        """Test getting action results."""
        executor = JourneyExecutor(
            journey=Journey("Test", "Test"),
            target_url="http://test.com"
        )
        
        # Mock results with action data
        executor.execution_results = {
            'step_results': [
                {
                    'step_name': 'Step 1',
                    'actions': [
                        {'action_name': 'Action 1', 'actual': True},
                        {'action_name': 'Action 2', 'actual': False}
                    ]
                },
                {
                    'step_name': 'Step 2',
                    'actions': [
                        {'action_name': 'Action 3', 'actual': True}
                    ]
                }
            ]
        }
        
        action_results = executor.get_action_results()
        self.assertEqual(len(action_results), 3)
        self.assertEqual(action_results[0]['action_name'], 'Action 1')
        self.assertEqual(action_results[0]['step_name'], 'Step 1')


if __name__ == '__main__':
    unittest.main()