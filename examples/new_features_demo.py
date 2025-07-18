#!/usr/bin/env python3
"""
Comprehensive demonstration of Scythe's new features.

This example showcases all four major new features:
1. ExpectPass/ExpectFail functionality
2. TTP Authentication mode
3. Journeys system
4. Orchestrators for scale testing

Run this example to see how these features work together to create
powerful, realistic testing scenarios.
"""

import time
import sys
import os

# Add the scythe package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.core.executor import TTPExecutor
from scythe.core.ttp import TTP
from scythe.auth.basic import BasicAuth
from scythe.auth.bearer import BearerTokenAuth
from scythe.payloads.generators import StaticPayloadGenerator
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import (
    NavigateAction, ClickAction, FillFormAction, 
    WaitAction, TTPAction, AssertAction
)
from scythe.journeys.executor import JourneyExecutor
from scythe.orchestrators.scale import ScaleOrchestrator
from scythe.orchestrators.distributed import DistributedOrchestrator, NetworkProxy, CredentialSet
from scythe.orchestrators.batch import BatchOrchestrator, BatchConfiguration
from scythe.orchestrators.base import OrchestrationStrategy
# Behaviors import removed as not used in this demo


class DemoLoginBruteforce(TTP):
    """Demo TTP for login bruteforce with authentication support."""
    
    def __init__(self, username: str, password_list: list, expected_result: bool = False, authentication=None):
        super().__init__(
            name="Demo Login Bruteforce",
            description="Demonstrates login bruteforce with expect fail functionality",
            expected_result=expected_result,  # We expect this to FAIL (security working)
            authentication=authentication
        )
        self.username = username
        self.payload_generator = StaticPayloadGenerator(password_list)
    
    def get_payloads(self):
        yield from self.payload_generator()
    
    def execute_step(self, driver, payload):
        # Simulate login attempt
        print(f"    Attempting login: {self.username} / {payload}")
        time.sleep(0.1)  # Simulate network delay
    
    def verify_result(self, driver):
        # Simulate failed login (security controls working)
        # In a real scenario, this would check for login success indicators
        return False  # Always fail - good security!


class DemoSQLInjection(TTP):
    """Demo TTP for SQL injection testing."""
    
    def __init__(self, payloads: list, expected_result: bool = False, authentication=None):
        super().__init__(
            name="Demo SQL Injection",
            description="Demonstrates SQL injection testing with expect fail",
            expected_result=expected_result,  # We expect this to FAIL (security working)
            authentication=authentication
        )
        self.payload_generator = StaticPayloadGenerator(payloads)
    
    def get_payloads(self):
        yield from self.payload_generator()
    
    def execute_step(self, driver, payload):
        print(f"    Testing SQL payload: {payload}")
        time.sleep(0.1)
    
    def verify_result(self, driver):
        # Simulate no SQL injection vulnerability found
        return False  # Security controls working!


def demo_expect_pass_fail():
    """Demonstrate ExpectPass/ExpectFail functionality."""
    print("\n" + "="*60)
    print("DEMO 1: ExpectPass/ExpectFail Functionality")
    print("="*60)
    
    print("\n1.1 Testing TTP Expected to FAIL (Security Controls Working)")
    print("-" * 50)
    
    # Create a TTP that we expect to fail (good security)
    bruteforce_ttp = DemoLoginBruteforce(
        username="admin",
        password_list=["password", "123456", "admin"],
        expected_result=False  # We EXPECT this to fail
    )
    
    executor = TTPExecutor(
        ttp=bruteforce_ttp,
        target_url="http://demo-app.com/login",
        headless=True
    )
    
    print("Expected Result: FAIL (security should prevent bruteforce)")
    print("Running TTP...")
    executor.run()
    
    print("\n1.2 Testing TTP Expected to PASS (Vulnerability Found)")
    print("-" * 50)
    
    # Create a TTP that we expect to pass (vulnerability found)
    class VulnerableTTP(TTP):
        def __init__(self):
            super().__init__(
                name="Vulnerable Demo TTP",
                description="TTP that finds a vulnerability",
                expected_result=True  # We EXPECT this to succeed
            )
        
        def get_payloads(self):
            yield "exploit_payload"
        
        def execute_step(self, driver, payload):
            print(f"    Testing payload: {payload}")
        
        def verify_result(self, driver):
            return True  # Vulnerability found!
    
    vuln_ttp = VulnerableTTP()
    executor2 = TTPExecutor(
        ttp=vuln_ttp,
        target_url="http://vulnerable-app.com",
        headless=True
    )
    
    print("Expected Result: PASS (vulnerability should be found)")
    print("Running TTP...")
    executor2.run()


def demo_authentication():
    """Demonstrate TTP Authentication functionality."""
    print("\n" + "="*60)
    print("DEMO 2: TTP Authentication Mode")
    print("="*60)
    
    print("\n2.1 Basic Authentication (Username/Password)")
    print("-" * 50)
    
    # Create basic authentication
    basic_auth = BasicAuth(
        username="test_user",
        password="test_password",
        login_url="http://demo-app.com/login"
    )
    
    # Create TTP with authentication
    authenticated_ttp = DemoSQLInjection(
        payloads=["' OR 1=1--", "'; DROP TABLE users;--"],
        expected_result=False,  # Security should prevent this
        authentication=basic_auth
    )
    
    executor = TTPExecutor(
        ttp=authenticated_ttp,
        target_url="http://demo-app.com/admin",
        headless=True
    )
    
    print("Authentication: Basic Auth (username/password)")
    print("Running authenticated TTP...")
    executor.run()
    
    print("\n2.2 Bearer Token Authentication")
    print("-" * 50)
    
    # Create bearer token authentication
    bearer_auth = BearerTokenAuth(
        token="demo_api_token_12345",
        auth_header_prefix="Bearer"
    )
    
    # Create API-focused TTP with token auth
    api_ttp = DemoSQLInjection(
        payloads=["admin'--", "1' UNION SELECT password FROM users--"],
        expected_result=False,
        authentication=bearer_auth
    )
    
    executor2 = TTPExecutor(
        ttp=api_ttp,
        target_url="http://api.demo-app.com/users",
        headless=True
    )
    
    print("Authentication: Bearer Token")
    print("Running API TTP with token authentication...")
    executor2.run()


def demo_journeys():
    """Demonstrate Journey functionality."""
    print("\n" + "="*60)
    print("DEMO 3: Journeys System")
    print("="*60)
    
    print("\n3.1 File Upload Journey")
    print("-" * 50)
    
    # Create a journey for testing file upload functionality
    journey = Journey(
        name="File Upload Test Journey",
        description="Test complete file upload workflow",
        expected_result=True
    )
    
    # Step 1: Navigate to application
    navigation_step = Step(
        name="Navigate to App",
        description="Navigate to the application homepage"
    )
    navigation_step.add_action(NavigateAction(
        url="http://demo-app.com",
        name="Load Homepage"
    ))
    navigation_step.add_action(WaitAction(
        wait_type="time",
        duration=1.0,
        name="Wait for page load"
    ))
    journey.add_step(navigation_step)
    
    # Step 2: Login
    login_step = Step(
        name="User Login",
        description="Authenticate with the application"
    )
    login_step.add_action(NavigateAction(
        url="http://demo-app.com/login",
        name="Go to login page"
    ))
    login_step.add_action(FillFormAction(
        field_data={
            "#username": "testuser",
            "#password": "testpass"
        },
        name="Fill login form"
    ))
    login_step.add_action(ClickAction(
        selector="#login-button",
        name="Click login button"
    ))
    login_step.add_action(AssertAction(
        assertion_type="url_contains",
        expected_value="dashboard",
        name="Verify login success"
    ))
    journey.add_step(login_step)
    
    # Step 3: Navigate to upload
    upload_nav_step = Step(
        name="Navigate to Upload",
        description="Go to file upload section"
    )
    upload_nav_step.add_action(ClickAction(
        selector="#upload-tab",
        name="Click upload tab"
    ))
    upload_nav_step.add_action(WaitAction(
        wait_type="element",
        selector="#file-input",
        condition="presence",
        duration=5.0,
        name="Wait for upload form"
    ))
    journey.add_step(upload_nav_step)
    
    # Step 4: Test upload with TTP
    security_test_step = Step(
        name="Security Testing",
        description="Test upload security with malicious files",
        continue_on_failure=True  # Continue even if security tests fail
    )
    
    # Create a TTP for testing malicious file uploads
    malicious_upload_ttp = DemoSQLInjection(
        payloads=["../../../etc/passwd", "malicious.php", "script.js"],
        expected_result=False  # Security should block these
    )
    
    security_test_step.add_action(TTPAction(
        ttp=malicious_upload_ttp,
        name="Test malicious file uploads",
        expected_result=False  # We expect security to block this
    ))
    journey.add_step(security_test_step)
    
    # Step 5: Test legitimate upload
    legitimate_test_step = Step(
        name="Legitimate Upload Test",
        description="Test uploading legitimate files"
    )
    legitimate_test_step.add_action(FillFormAction(
        field_data={
            "#file-input": "test_document.pdf"
        },
        name="Select legitimate file"
    ))
    legitimate_test_step.add_action(ClickAction(
        selector="#upload-button",
        name="Upload file"
    ))
    legitimate_test_step.add_action(AssertAction(
        assertion_type="page_contains",
        expected_value="Upload successful",
        name="Verify upload success"
    ))
    journey.add_step(legitimate_test_step)
    
    # Execute the journey
    executor = JourneyExecutor(
        journey=journey,
        target_url="http://demo-app.com",
        headless=True
    )
    
    print("Executing File Upload Journey...")
    print("Steps: Navigation → Login → Upload Navigation → Security Testing → Legitimate Upload")
    results = executor.run()
    
    print("\nJourney Results:")
    print(f"  Overall Success: {results['overall_success']}")
    print(f"  Steps Completed: {results['steps_succeeded']}/{results['steps_executed']}")
    print(f"  Actions Completed: {results['actions_succeeded']}/{results['actions_executed']}")


def demo_orchestrators():
    """Demonstrate Orchestrator functionality."""
    print("\n" + "="*60)
    print("DEMO 4: Orchestrators for Scale Testing")
    print("="*60)
    
    # Create a simple TTP for orchestration
    demo_ttp = DemoLoginBruteforce(
        username="testuser",
        password_list=["pass1", "pass2", "pass3"],
        expected_result=False
    )
    
    print("\n4.1 Scale Orchestrator (Load Testing)")
    print("-" * 50)
    
    # Scale orchestrator for load testing
    scale_orchestrator = ScaleOrchestrator(
        name="Load Test Orchestrator",
        strategy=OrchestrationStrategy.PARALLEL,
        max_workers=3,
        ramp_up_delay=0.5,
        cool_down_delay=0.2
    )
    
    print("Running 5 parallel instances to simulate load...")
    scale_result = scale_orchestrator.orchestrate_ttp(
        ttp=demo_ttp,
        target_url="http://demo-app.com/login",
        replications=5
    )
    
    print("Scale Test Results:")
    print(f"  Total Executions: {scale_result.total_executions}")
    print(f"  Success Rate: {scale_result.success_rate:.1f}%")
    print(f"  Execution Time: {scale_result.execution_time:.2f}s")
    
    print("\n4.2 Distributed Orchestrator (Geographic Distribution)")
    print("-" * 50)
    
    # Create network proxies for distribution
    proxies = [
        NetworkProxy("US-East", "proxy-us-east.example.com:8080", location="US East"),
        NetworkProxy("EU-West", "proxy-eu-west.example.com:8080", location="EU West"),
        NetworkProxy("Asia-Pacific", "proxy-ap.example.com:8080", location="Asia Pacific")
    ]
    
    # Create different credential sets
    credentials = [
        CredentialSet("User1", "user1", "pass1"),
        CredentialSet("User2", "user2", "pass2"),
        CredentialSet("User3", "user3", "pass3")
    ]
    
    distributed_orchestrator = DistributedOrchestrator(
        name="Geographic Distribution Test",
        strategy=OrchestrationStrategy.PARALLEL,
        max_workers=3,
        proxies=proxies,
        credentials=credentials,
        proxy_rotation_strategy="round_robin",
        credential_rotation_strategy="round_robin"
    )
    
    print("Running distributed test across 3 geographic locations...")
    print("Proxies: US East, EU West, Asia Pacific")
    print("Credentials: 3 different user accounts")
    
    distributed_result = distributed_orchestrator.orchestrate_ttp(
        ttp=demo_ttp,
        target_url="http://global-app.com/login",
        replications=6  # 2 tests per location
    )
    
    print("Distributed Test Results:")
    print(f"  Total Executions: {distributed_result.total_executions}")
    print(f"  Success Rate: {distributed_result.success_rate:.1f}%")
    print(f"  Locations Used: {distributed_result.metadata.get('distribution_stats', {}).get('locations_used', 0)}")
    
    print("\n4.3 Batch Orchestrator (Resource-Limited Testing)")
    print("-" * 50)
    
    # Batch orchestrator for limited resources
    batch_config = BatchConfiguration(
        batch_size=3,  # Process 3 at a time
        batch_delay=1.0,  # 1 second between batches
        max_concurrent_batches=1,
        retry_failed_batches=True
    )
    
    batch_orchestrator = BatchOrchestrator(
        name="Resource-Limited Test",
        batch_config=batch_config,
        max_workers=2  # Limited workers
    )
    
    print("Running batch test with limited resources...")
    print("Batch Size: 3, Max Workers: 2, Batch Delay: 1s")
    
    batch_result = batch_orchestrator.orchestrate_ttp(
        ttp=demo_ttp,
        target_url="http://demo-app.com/login",
        replications=8  # Will be processed in batches
    )
    
    print("Batch Test Results:")
    print(f"  Total Executions: {batch_result.total_executions}")
    print(f"  Success Rate: {batch_result.success_rate:.1f}%")
    print(f"  Batches Completed: {batch_result.metadata.get('completed_batches', 0)}")
    print(f"  Total Batches: {batch_result.metadata.get('total_batches', 0)}")


def demo_combined_features():
    """Demonstrate all features working together."""
    print("\n" + "="*60)
    print("DEMO 5: Combined Features - Realistic Testing Scenario")
    print("="*60)
    
    print("\nScenario: Load testing an authenticated web application")
    print("- Multiple users from different locations")
    print("- Authentication required")
    print("- Complex user journeys")
    print("- Scale testing with resource constraints")
    
    # Create authentication
    auth = BasicAuth("loadtest_user", "loadtest_pass")
    
    # Create an authenticated journey
    journey = Journey(
        name="Authenticated User Journey",
        description="Complete user workflow with authentication",
        authentication=auth,
        expected_result=True
    )
    
    # Login step
    login_step = Step("Login", "Authenticate user")
    login_step.add_action(NavigateAction("http://app.com/login"))
    login_step.add_action(FillFormAction({
        "#username": "loadtest_user",
        "#password": "loadtest_pass"
    }))
    login_step.add_action(ClickAction("#login-btn"))
    journey.add_step(login_step)
    
    # Main workflow step
    workflow_step = Step("Main Workflow", "Execute main user workflow")
    workflow_step.add_action(NavigateAction("http://app.com/dashboard"))
    workflow_step.add_action(ClickAction("#reports-tab"))
    workflow_step.add_action(WaitAction("time", duration=2.0))
    workflow_step.add_action(AssertAction("page_contains", "Reports"))
    journey.add_step(workflow_step)
    
    # Create distributed orchestrator with authentication
    proxies = [
        NetworkProxy("LoadTest-1", "proxy1.example.com:8080", location="Region 1"),
        NetworkProxy("LoadTest-2", "proxy2.example.com:8080", location="Region 2")
    ]
    
    credentials = [
        CredentialSet("LoadUser1", "user1", "pass1"),
        CredentialSet("LoadUser2", "user2", "pass2"),
        CredentialSet("LoadUser3", "user3", "pass3")
    ]
    
    orchestrator = DistributedOrchestrator(
        name="Combined Features Demo",
        strategy=OrchestrationStrategy.PARALLEL,
        proxies=proxies,
        credentials=credentials,
        max_workers=2
    )
    
    print("\nRunning combined demo:")
    print("- Authenticated journeys")
    print("- Distributed across 2 proxy locations")
    print("- 3 different user credential sets")
    print("- Expect all journeys to succeed")
    
    result = orchestrator.orchestrate_journey(
        journey=journey,
        target_url="http://app.com",
        replications=4
    )
    
    print("\nCombined Demo Results:")
    print(f"  Journeys Executed: {result.total_executions}")
    print(f"  Success Rate: {result.success_rate:.1f}%")
    print(f"  Execution Time: {result.execution_time:.2f}s")
    print(f"  Locations Used: {len(result.metadata.get('distribution_stats', {}).get('location_usage', {}))}")
    
    # Show summary of all capabilities
    print("\n✓ ExpectPass/ExpectFail: Journeys expected to succeed")
    print("✓ Authentication: Basic auth integrated into journeys")
    print("✓ Journeys: Multi-step workflows with actions")
    print("✓ Orchestrators: Distributed execution across networks")


def main():
    """Run all feature demonstrations."""
    print("Scythe Framework - New Features Demonstration")
    print("This demo shows all four major new features in action")
    print("\nNote: This is a simulation - no actual web requests are made")
    
    try:
        # Run individual feature demos
        demo_expect_pass_fail()
        demo_authentication()
        demo_journeys()
        demo_orchestrators()
        demo_combined_features()
        
        print("\n" + "="*60)
        print("DEMONSTRATION COMPLETE")
        print("="*60)
        print("All new features have been demonstrated:")
        print("1. ✓ ExpectPass/ExpectFail - Unit test style result validation")
        print("2. ✓ Authentication - Bearer token and basic auth support")
        print("3. ✓ Journeys - Multi-step workflows with granular actions")
        print("4. ✓ Orchestrators - Scale, distributed, and batch testing")
        print("\nFor production use:")
        print("- Replace demo URLs with real target applications")
        print("- Configure actual proxy servers and credentials")
        print("- Adjust timing and concurrency for your infrastructure")
        print("- Review security controls with expect fail scenarios")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nDemo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()