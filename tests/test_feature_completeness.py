import unittest
import sys
import os

# Add the scythe package to the path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.core.ttp import TTP
from scythe.auth.basic import BasicAuth
from scythe.auth.bearer import BearerTokenAuth
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import NavigateAction, ClickAction, FillFormAction, AssertAction, TTPAction
from scythe.orchestrators.scale import ScaleOrchestrator
from scythe.orchestrators.distributed import DistributedOrchestrator, NetworkProxy, CredentialSet
from scythe.orchestrators.batch import BatchOrchestrator, BatchConfiguration
from scythe.behaviors import HumanBehavior, MachineBehavior, StealthBehavior
from selenium.webdriver.remote.webdriver import WebDriver
from typing import Generator, Any


class MockTTP(TTP):
    """Mock TTP for testing feature completeness."""

    def __init__(self, name: str, description: str, expected_result: bool = True,
                 should_succeed: bool = False, authentication=None):
        super().__init__(name, description, expected_result, authentication)
        self.should_succeed = should_succeed

    def get_payloads(self) -> Generator[Any, None, None]:
        yield "test_payload_1"
        yield "test_payload_2"

    def execute_step(self, driver: WebDriver, payload: Any) -> None:
        pass

    def verify_result(self, driver: WebDriver) -> bool:
        return self.should_succeed


class TestFeature1ExpectedResults(unittest.TestCase):
    """Test Feature 1: ExpectPass/ExpectFail functionality."""

    def test_expected_result_parameter_exists(self):
        """Test that TTP has expected_result parameter."""
        ttp = MockTTP("Test TTP", "Test Description", expected_result=False)
        self.assertFalse(ttp.expected_result)

        ttp2 = MockTTP("Test TTP 2", "Test Description", expected_result=True)
        self.assertTrue(ttp2.expected_result)

    def test_expected_result_default_value(self):
        """Test that expected_result defaults to True."""
        ttp = MockTTP("Test TTP", "Test Description")
        self.assertTrue(ttp.expected_result)

    def test_expected_vs_actual_results(self):
        """Test expected vs actual result comparison logic."""
        # TTP that expects to succeed and will succeed - GOOD
        ttp1 = MockTTP("Success TTP", "Should succeed",
                      expected_result=True, should_succeed=True)

        # TTP that expects to fail and will fail - GOOD
        ttp2 = MockTTP("Failure TTP", "Should fail",
                      expected_result=False, should_succeed=False)

        # TTP that expects to succeed but will fail - BAD
        ttp3 = MockTTP("Unexpected Failure", "Should succeed but won't",
                      expected_result=True, should_succeed=False)

        # TTP that expects to fail but will succeed - BAD
        ttp4 = MockTTP("Unexpected Success", "Should fail but won't",
                      expected_result=False, should_succeed=True)

        # Simple direct comparison of expected vs actual
        self.assertEqual(ttp1.expected_result, ttp1.should_succeed)  # True == True
        self.assertEqual(ttp2.expected_result, ttp2.should_succeed)  # False == False
        self.assertNotEqual(ttp3.expected_result, ttp3.should_succeed)  # True != False
        self.assertNotEqual(ttp4.expected_result, ttp4.should_succeed)  # False != True


class TestFeature2Authentication(unittest.TestCase):
    """Test Feature 2: TTP Authentication mode."""

    def test_basic_auth_exists(self):
        """Test that BasicAuth class exists and works."""
        auth = BasicAuth(
            username="testuser",
            password="testpass",
            login_url="http://example.com/login"
        )
        self.assertEqual(auth.username, "testuser")
        self.assertEqual(auth.password, "testpass")
        self.assertEqual(auth.login_url, "http://example.com/login")
        self.assertEqual(auth.name, "Basic Authentication")

    def test_bearer_auth_exists(self):
        """Test that BearerTokenAuth class exists and works."""
        auth = BearerTokenAuth(token="test_token_123")
        self.assertEqual(auth.token, "test_token_123")
        self.assertEqual(auth.name, "Bearer Token Authentication")

    def test_ttp_authentication_integration(self):
        """Test that TTPs can use authentication."""
        auth = BasicAuth(username="user", password="pass")
        ttp = MockTTP("Auth TTP", "TTP with auth", authentication=auth)

        self.assertTrue(ttp.requires_authentication())
        self.assertEqual(ttp.authentication, auth)

    def test_ttp_without_authentication(self):
        """Test that TTPs work without authentication."""
        ttp = MockTTP("No Auth TTP", "TTP without auth")
        self.assertFalse(ttp.requires_authentication())
        self.assertIsNone(ttp.authentication)

    def test_authentication_method_names(self):
        """Test authentication method naming."""
        basic_auth = BasicAuth(username="user", password="pass")
        bearer_auth = BearerTokenAuth(token="token")

        self.assertIn("Basic", basic_auth.name)
        self.assertIn("Bearer", bearer_auth.name)


class TestFeature3Journeys(unittest.TestCase):
    """Test Feature 3: Journeys framework."""

    def test_journey_creation(self):
        """Test that journeys can be created."""
        journey = Journey("Test Journey", "Test Description")
        self.assertEqual(journey.name, "Test Journey")
        self.assertEqual(journey.description, "Test Description")
        self.assertEqual(len(journey.steps), 0)

    def test_step_creation(self):
        """Test that steps can be created."""
        step = Step("Test Step", "Test Description")
        self.assertEqual(step.name, "Test Step")
        self.assertEqual(step.description, "Test Description")
        self.assertEqual(len(step.actions), 0)

    def test_action_creation(self):
        """Test that different action types can be created."""
        nav_action = NavigateAction(url="http://example.com")
        click_action = ClickAction(selector="#button")
        fill_action = FillFormAction(field_data={"#field": "value"})
        assert_action = AssertAction(assertion_type="url_contains",
                                   expected_value="example")

        self.assertEqual(nav_action.url, "http://example.com")
        self.assertEqual(click_action.selector, "#button")
        self.assertEqual(fill_action.field_data, {"#field": "value"})
        self.assertEqual(assert_action.assertion_type, "url_contains")

    def test_journey_step_action_hierarchy(self):
        """Test that journey -> step -> action hierarchy works."""
        journey = Journey("Test Journey", "Test Description")
        step = Step("Test Step", "Test Description")
        action = NavigateAction(url="http://example.com")

        step.add_action(action)
        journey.add_step(step)

        self.assertEqual(len(journey.steps), 1)
        self.assertEqual(len(journey.steps[0].actions), 1)
        self.assertEqual(journey.steps[0].actions[0], action)

    def test_journey_with_authentication(self):
        """Test that journeys can use authentication."""
        auth = BasicAuth(username="user", password="pass")
        journey = Journey("Auth Journey", "Journey with auth", authentication=auth)

        self.assertTrue(journey.requires_authentication())
        self.assertEqual(journey.authentication, auth)

    def test_ttp_action_integration(self):
        """Test that TTPs can be used as actions in journeys."""
        ttp = MockTTP("Test TTP", "TTP for journey")
        ttp_action = TTPAction(ttp=ttp)

        self.assertEqual(ttp_action.ttp, ttp)
        self.assertIn("TTP", ttp_action.name)


class TestFeature4Orchestrators(unittest.TestCase):
    """Test Feature 4: Orchestrators for scale testing."""

    def test_scale_orchestrator_creation(self):
        """Test that ScaleOrchestrator can be created."""
        orchestrator = ScaleOrchestrator(
            name="Test Scale Orchestrator",
            max_workers=5
        )
        self.assertEqual(orchestrator.name, "Test Scale Orchestrator")
        self.assertEqual(orchestrator.max_workers, 5)

    def test_distributed_orchestrator_creation(self):
        """Test that DistributedOrchestrator can be created."""
        proxies = [
            NetworkProxy(name="Proxy1", proxy_url="proxy1.com:8080"),
            NetworkProxy(name="Proxy2", proxy_url="proxy2.com:8080")
        ]
        credentials = [
            CredentialSet("cred1", "user1", "pass1"),
            CredentialSet("cred2", "user2", "pass2")
        ]

        orchestrator = DistributedOrchestrator(
            name="Test Distributed Orchestrator",
            proxies=proxies,
            credentials=credentials
        )

        self.assertEqual(orchestrator.name, "Test Distributed Orchestrator")
        self.assertEqual(len(orchestrator.proxies), 2)
        self.assertEqual(len(orchestrator.credentials), 2)

    def test_batch_orchestrator_creation(self):
        """Test that BatchOrchestrator can be created."""
        batch_config = BatchConfiguration(
            batch_size=5,
            max_concurrent_batches=2
        )
        orchestrator = BatchOrchestrator(
            name="Test Batch Orchestrator",
            batch_config=batch_config
        )

        self.assertEqual(orchestrator.name, "Test Batch Orchestrator")
        self.assertEqual(orchestrator.batch_config.batch_size, 5)

    def test_network_proxy_configuration(self):
        """Test NetworkProxy configuration."""
        proxy = NetworkProxy(
            name="Test Proxy",
            proxy_url="proxy.example.com:8080",
            location="US-East"
        )

        self.assertEqual(proxy.name, "Test Proxy")
        self.assertEqual(proxy.proxy_url, "proxy.example.com:8080")
        self.assertEqual(proxy.location, "US-East")

    def test_credential_set_configuration(self):
        """Test CredentialSet configuration."""
        creds = CredentialSet("test_creds", "testuser", "testpass")

        self.assertEqual(creds.name, "test_creds")
        self.assertEqual(creds.username, "testuser")
        self.assertEqual(creds.password, "testpass")


class TestFeatureIntegration(unittest.TestCase):
    """Test integration of all features together."""

    def test_ttp_with_all_features(self):
        """Test TTP with authentication and expected results."""
        auth = BasicAuth(username="user", password="pass")
        ttp = MockTTP(
            name="Integrated TTP",
            description="TTP with all features",
            expected_result=False,  # Expect security to work
            should_succeed=False,   # Security will work
            authentication=auth
        )

        self.assertTrue(ttp.requires_authentication())
        self.assertFalse(ttp.expected_result)
        self.assertEqual(ttp.authentication, auth)

    def test_journey_with_ttp_and_auth(self):
        """Test journey containing TTP with authentication."""
        auth = BasicAuth(username="user", password="pass")
        ttp = MockTTP("Security TTP", "Security test", authentication=auth)

        journey = Journey("Security Journey", "Journey with security tests")
        step = Step("Security Step", "Run security tests")
        ttp_action = TTPAction(ttp=ttp)

        step.add_action(ttp_action)
        journey.add_step(step)

        self.assertEqual(len(journey.steps), 1)
        self.assertEqual(len(journey.steps[0].actions), 1)
        # Type assertion to help type checker understand this is a TTPAction
        ttp_action_instance = journey.steps[0].actions[0]
        assert isinstance(ttp_action_instance, TTPAction)
        self.assertTrue(ttp_action_instance.ttp.requires_authentication())

    def test_orchestrator_with_journey_and_auth(self):
        """Test orchestrator running journey with authentication."""
        auth = BasicAuth(username="user", password="pass")
        journey = Journey("Test Journey", "Journey for orchestration", authentication=auth)
        orchestrator = ScaleOrchestrator(name="Test Orchestrator")

        self.assertTrue(journey.requires_authentication())
        self.assertEqual(orchestrator.name, "Test Orchestrator")

    def test_behaviors_with_new_features(self):
        """Test that behaviors work with new features."""
        behavior = MachineBehavior()
        auth = BasicAuth(username="user", password="pass")
        ttp = MockTTP("Behavior TTP", "TTP with behavior",
                     expected_result=False, authentication=auth)

        self.assertEqual(behavior.name, "Machine Behavior")
        self.assertTrue(ttp.requires_authentication())
        self.assertFalse(ttp.expected_result)


class TestBackwardCompatibility(unittest.TestCase):
    """Test that existing functionality still works."""

    def test_ttp_without_new_features(self):
        """Test that old-style TTPs still work."""
        ttp = MockTTP("Legacy TTP", "Old style TTP")

        # Should have default values
        self.assertTrue(ttp.expected_result)  # Default to True
        self.assertFalse(ttp.requires_authentication())  # No auth by default

    def test_behaviors_still_work(self):
        """Test that existing behavior system works."""
        human_behavior = HumanBehavior()
        machine_behavior = MachineBehavior()
        stealth_behavior = StealthBehavior()

        self.assertIn("Human", human_behavior.name)
        self.assertIn("Machine", machine_behavior.name)
        self.assertIn("Stealth", stealth_behavior.name)


if __name__ == '__main__':
    unittest.main()
