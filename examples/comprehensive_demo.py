#!/usr/bin/env python3
"""
Comprehensive Scythe Demo

This example demonstrates all major features of Scythe working together:
1. ExpectPass/ExpectFail functionality
2. TTP Authentication mode
3. Journeys system
4. Orchestrators for scale testing

This demo uses mock implementations to show the concepts without requiring
actual web applications to test against.
"""

import time
import sys
import os
from typing import Generator

# Add the scythe package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scythe.core.executor import TTPExecutor
from scythe.core.ttp import TTP
from scythe.auth.basic import BasicAuth
from scythe.auth.bearer import BearerTokenAuth
from scythe.payloads.generators import StaticPayloadGenerator
from scythe.journeys.base import Journey, Step, Action

from scythe.journeys.executor import JourneyExecutor
from scythe.orchestrators.scale import ScaleOrchestrator
from scythe.orchestrators.distributed import DistributedOrchestrator, NetworkProxy, CredentialSet
from scythe.orchestrators.batch import BatchOrchestrator, BatchConfiguration
from scythe.orchestrators.base import OrchestrationStrategy
from scythe.behaviors import HumanBehavior, MachineBehavior


# =============================================================================
# Mock TTPs for Demonstration
# =============================================================================

class MockLoginBruteForceTTP(TTP):
    """Mock TTP that simulates login brute force testing."""
    
    def __init__(self, username: str, passwords: list, expected_result: bool = False, authentication=None):
        super().__init__(
            name="Mock Login Brute Force",
            description="Simulates login brute force attacks to test security controls",
            expected_result=expected_result,
            authentication=authentication
        )
        self.username = username
        self.payload_generator = StaticPayloadGenerator(passwords)
        
    def get_payloads(self) -> Generator[str, None, None]:
        yield from self.payload_generator()
        
    def execute_step(self, driver, payload: str) -> None:
        print(f"      → Attempting login: {self.username} / {payload}")
        time.sleep(0.1)  # Simulate network delay
        
    def verify_result(self, driver) -> bool:
        # Simulate strong security - login attempts fail (which is good!)
        # Only succeed 10% of the time to show mixed results
        import random
        return random.random() < 0.1


class MockSQLInjectionTTP(TTP):
    """Mock TTP that simulates SQL injection testing."""
    
    def __init__(self, payloads: list, expected_result: bool = False, authentication=None):
        super().__init__(
            name="Mock SQL Injection",
            description="Simulates SQL injection attacks to test input validation",
            expected_result=expected_result,
            authentication=authentication
        )
        self.payload_generator = StaticPayloadGenerator(payloads)
        
    def get_payloads(self) -> Generator[str, None, None]:
        yield from self.payload_generator()
        
    def execute_step(self, driver, payload: str) -> None:
        print(f"      → Testing SQL payload: {payload}")
        time.sleep(0.1)
        
    def verify_result(self, driver) -> bool:
        # Simulate good security - SQL injection attempts fail
        return False


class MockVulnerableTTP(TTP):
    """Mock TTP that simulates finding a vulnerability."""
    
    def __init__(self):
        super().__init__(
            name="Mock Vulnerable System Test",
            description="Simulates finding an actual vulnerability",
            expected_result=True  # We expect this to find vulnerabilities
        )
        
    def get_payloads(self) -> Generator[str, None, None]:
        yield "vulnerability_trigger"
        
    def execute_step(self, driver, payload: str) -> None:
        print(f"      → Testing for known vulnerability: {payload}")
        time.sleep(0.1)
        
    def verify_result(self, driver) -> bool:
        # Simulate finding a vulnerability
        return True


# =============================================================================
# Mock Actions for Journey Demonstration
# =============================================================================

class MockAction(Action):
    """Mock action that simulates web interactions."""
    
    def __init__(self, name: str, description: str, success_rate: float = 0.9, expected_result: bool = True):
        super().__init__(name, description, expected_result)
        self.success_rate = success_rate
        
    def execute(self, driver, context) -> bool:
        print(f"        → Executing: {self.description}")
        time.sleep(0.05)  # Simulate action time
        
        # Simulate success based on success rate
        import random
        success = random.random() < self.success_rate
        
        if success:
            # Store some mock data in context
            context[f'{self.name}_completed'] = True
            
        return success


# =============================================================================
# Demo Functions
# =============================================================================

def demo_expected_results():
    """Demonstrate the ExpectPass/ExpectFail functionality."""
    print("\n" + "="*80)
    print("DEMO 1: Expected Results System (ExpectPass/ExpectFail)")
    print("="*80)
    
    print("\n1.1 Testing TTP Expected to FAIL (Security Controls Working)")
    print("-" * 60)
    
    # Create a TTP that we expect to fail (good security)
    secure_ttp = MockLoginBruteForceTTP(
        username="admin",
        passwords=["password", "123456", "admin", "letmein"],
        expected_result=False  # We EXPECT this to fail (security working)
    )
    
    print("Expected Result: FAIL (security should prevent brute force)")
    print("This demonstrates security controls working properly.\n")
    
    executor = TTPExecutor(
        ttp=secure_ttp,
        target_url="https://secure-demo-app.com/login",
        headless=True
    )
    executor.run()
    
    print("\n1.2 Testing TTP Expected to PASS (Vulnerability Found)")
    print("-" * 60)
    
    # Create a TTP that expects to find vulnerabilities
    vuln_ttp = MockVulnerableTTP()
    
    print("Expected Result: PASS (vulnerability should be found)")
    print("This demonstrates finding an actual security issue.\n")
    
    executor2 = TTPExecutor(
        ttp=vuln_ttp,
        target_url="https://vulnerable-demo-app.com",
        headless=True
    )
    executor2.run()


def demo_authentication():
    """Demonstrate TTP authentication capabilities."""
    print("\n" + "="*80)
    print("DEMO 2: TTP Authentication System")
    print("="*80)
    
    print("\n2.1 Basic Authentication (Username/Password Forms)")
    print("-" * 60)
    
    # Create basic authentication for web forms
    basic_auth = BasicAuth(
        username="security_tester",
        password="secure_password123",
        login_url="https://demo-app.com/login",
        success_indicators=["dashboard", "welcome", "logout"]
    )
    
    # Create TTP that requires authentication
    authenticated_ttp = MockSQLInjectionTTP(
        payloads=["' OR 1=1--", "'; DROP TABLE users;--", "admin'/*"],
        expected_result=False,  # Security should prevent this
        authentication=basic_auth
    )
    
    print("Authentication Type: Basic Auth (web forms)")
    print("Target: Admin panel requiring authentication")
    print("Expected: Authentication succeeds, SQL injection fails\n")
    
    executor = TTPExecutor(
        ttp=authenticated_ttp,
        target_url="https://demo-app.com/admin/users",
        headless=True
    )
    executor.run()
    
    print("\n2.2 Bearer Token Authentication (APIs)")
    print("-" * 60)
    
    # Create bearer token authentication for APIs
    bearer_auth = BearerTokenAuth(
        token="demo_api_token_abc123xyz789",
        auth_header_prefix="Bearer"
    )
    
    # Create API-focused TTP with token auth
    api_ttp = MockSQLInjectionTTP(
        payloads=["1' UNION SELECT password FROM users--", "admin'; --"],
        expected_result=False,  # API should have input validation
        authentication=bearer_auth
    )
    
    print("Authentication Type: Bearer Token (API)")
    print("Target: REST API endpoints")
    print("Expected: Token auth succeeds, SQL injection fails\n")
    
    executor2 = TTPExecutor(
        ttp=api_ttp,
        target_url="https://api.demo-app.com/v1/users",
        headless=True
    )
    executor2.run()


def demo_journeys():
    """Demonstrate the Journeys system for complex workflows."""
    print("\n" + "="*80)
    print("DEMO 3: Journeys System - Complex Multi-Step Testing")
    print("="*80)
    
    print("\n3.1 E-commerce Security Testing Journey")
    print("-" * 60)
    
    # Create a comprehensive journey for e-commerce security testing
    ecommerce_journey = Journey(
        name="E-commerce Security Assessment",
        description="Complete security testing workflow for online store",
        expected_result=True
    )
    
    # Step 1: User Registration and Authentication
    registration_step = Step(
        name="User Registration & Login",
        description="Test user registration and authentication flow"
    )
    
    registration_step.add_action(MockAction(
        "Navigate to Registration",
        "Navigate to user registration page",
        success_rate=0.95
    ))
    
    registration_step.add_action(MockAction(
        "Fill Registration Form",
        "Complete user registration with test data",
        success_rate=0.9
    ))
    
    registration_step.add_action(MockAction(
        "Verify Account Creation",
        "Confirm account was created successfully",
        success_rate=0.9
    ))
    
    # Step 2: Product Browsing and Cart Testing
    shopping_step = Step(
        name="Shopping Cart Security",
        description="Test shopping cart functionality and security",
        continue_on_failure=True  # Continue even if some actions fail
    )
    
    shopping_step.add_action(MockAction(
        "Browse Products",
        "Navigate through product catalog",
        success_rate=0.95
    ))
    
    shopping_step.add_action(MockAction(
        "Add Items to Cart",
        "Add various items to shopping cart",
        success_rate=0.9
    ))
    
    shopping_step.add_action(MockAction(
        "Test Price Manipulation",
        "Attempt to manipulate product prices",
        success_rate=0.1,  # Should mostly fail (good security)
        expected_result=False  # We expect this to fail
    ))
    
    # Step 3: Checkout Security Testing
    checkout_step = Step(
        name="Payment Security Testing",
        description="Test payment processing security"
    )
    
    checkout_step.add_action(MockAction(
        "Navigate to Checkout",
        "Proceed to checkout process",
        success_rate=0.95
    ))
    
    checkout_step.add_action(MockAction(
        "Test Payment Validation",
        "Test payment form validation and security",
        success_rate=0.8
    ))
    
    checkout_step.add_action(MockAction(
        "Test SQL Injection in Payment",
        "Attempt SQL injection in payment fields",
        success_rate=0.05,  # Should fail (good security)
        expected_result=False
    ))
    
    # Add steps to journey
    ecommerce_journey.add_step(registration_step)
    ecommerce_journey.add_step(shopping_step)
    ecommerce_journey.add_step(checkout_step)
    
    print("Journey: E-commerce Security Assessment")
    print("Steps: Registration → Shopping Cart → Payment Security")
    print("Expected: Most security tests should fail (indicating good security)\n")
    
    # Execute the journey
    journey_executor = JourneyExecutor(
        journey=ecommerce_journey,
        target_url="https://demo-ecommerce.com",
        headless=True
    )
    
    journey_executor.run()
    
    print("\n3.2 File Upload Security Journey")
    print("-" * 60)
    
    # Create a journey specifically for file upload security testing
    upload_journey = Journey(
        name="File Upload Security Test",
        description="Test file upload security controls"
    )
    
    # Authentication step
    auth_step = Step("User Authentication", "Login as test user")
    auth_step.add_action(MockAction("Login", "Authenticate with test credentials"))
    
    # File upload testing step
    upload_step = Step(
        name="Malicious File Upload Tests",
        description="Test file upload security with various malicious files",
        expected_result=False  # Security should block malicious uploads
    )
    
    upload_step.add_action(MockAction(
        "Test Executable Upload",
        "Attempt to upload executable file",
        success_rate=0.05,  # Should fail
        expected_result=False
    ))
    
    upload_step.add_action(MockAction(
        "Test Script Upload",
        "Attempt to upload script files",
        success_rate=0.1,  # Should mostly fail
        expected_result=False
    ))
    
    upload_step.add_action(MockAction(
        "Test Path Traversal",
        "Attempt path traversal in filename",
        success_rate=0.02,  # Should fail
        expected_result=False
    ))
    
    upload_journey.add_step(auth_step)
    upload_journey.add_step(upload_step)
    
    print("Journey: File Upload Security Testing")
    print("Expected: Upload security controls should block malicious files\n")
    
    upload_executor = JourneyExecutor(
        journey=upload_journey,
        target_url="https://demo-app.com/upload",
        headless=True
    )
    
    upload_executor.run()


def demo_orchestrators():
    """Demonstrate orchestrators for scale and distributed testing."""
    print("\n" + "="*80)
    print("DEMO 4: Orchestrators - Scale and Distributed Testing")
    print("="*80)
    
    print("\n4.1 Scale Testing - Load Testing User Registration")
    print("-" * 60)
    
    # Create a simple registration journey for load testing
    registration_journey = Journey(
        name="User Registration Load Test",
        description="Test user registration under load"
    )
    
    reg_step = Step("Register User", "Complete user registration process")
    reg_step.add_action(MockAction(
        "Registration Process",
        "Complete registration form and submit",
        success_rate=0.85  # Some failures expected under load
    ))
    
    registration_journey.add_step(reg_step)
    
    # Create scale orchestrator for load testing
    scale_orchestrator = ScaleOrchestrator(
        name="Registration Load Test",
        strategy=OrchestrationStrategy.PARALLEL,
        max_workers=5,  # Reduced for demo
        ramp_up_delay=0.1,
        cool_down_delay=0.1
    )
    
    print("Test: Simulating 20 concurrent user registrations")
    print("Strategy: Parallel execution with 5 workers")
    print("Expected: Some failures under load are normal\n")
    
    # Run scale test
    scale_result = scale_orchestrator.orchestrate_journey(
        journey=registration_journey,
        target_url="https://demo-app.com/register",
        replications=20
    )
    
    print("\nScale Test Results:")
    print(f"  Total Executions: {scale_result.total_executions}")
    print(f"  Successful: {scale_result.successful_executions}")
    print(f"  Success Rate: {scale_result.success_rate:.1f}%")
    print(f"  Total Time: {scale_result.execution_time:.2f}s")
    
    print("\n4.2 Batch Processing - Large Scale TTP Testing")
    print("-" * 60)
    
    # Create batch configuration
    batch_config = BatchConfiguration(
        batch_size=5,
        batch_delay=0.2,
        max_concurrent_batches=2,
        retry_failed_batches=True,
        max_retries=1
    )
    
    # Create batch orchestrator
    batch_orchestrator = BatchOrchestrator(
        name="Security Testing Batches",
        batch_config=batch_config
    )
    
    # Create a TTP for batch testing
    security_ttp = MockLoginBruteForceTTP(
        username="admin",
        passwords=["password", "123456"],
        expected_result=False
    )
    
    print("Test: Running security tests in batches")
    print("Configuration: 15 tests in batches of 5, with retry logic")
    print("Expected: Most should fail (good security)\n")
    
    # Run batch test
    batch_result = batch_orchestrator.orchestrate_ttp(
        ttp=security_ttp,
        target_url="https://demo-app.com/login",
        replications=15
    )
    
    print("\nBatch Test Results:")
    print(f"  Total Executions: {batch_result.total_executions}")
    print(f"  Successful: {batch_result.successful_executions}")
    print(f"  Batches Completed: {batch_result.metadata.get('completed_batches', 0)}")
    print(f"  Batches Failed: {batch_result.metadata.get('failed_batches', 0)}")
    
    print("\n4.3 Distributed Testing - Geographic Load Testing")
    print("-" * 60)
    
    # Create network proxies for different geographic locations
    proxies = [
        NetworkProxy(
            name="US-East-Proxy",
            proxy_url="proxy-us-east.example.com:8080",
            location="US-East-1"
        ),
        NetworkProxy(
            name="EU-West-Proxy", 
            proxy_url="proxy-eu-west.example.com:8080",
            location="EU-West-1"
        ),
        NetworkProxy(
            name="Asia-Pacific-Proxy",
            proxy_url="proxy-ap.example.com:8080", 
            location="Asia-Pacific"
        )
    ]
    
    # Create credential sets for different user types
    credentials = [
        CredentialSet(
            name="standard-user-1",
            username="user1",
            password="password1"
        ),
        CredentialSet(
            name="standard-user-2",
            username="user2", 
            password="password2"
        ),
        CredentialSet(
            name="premium-user-1",
            username="premium1",
            password="premium_pass1"
        )
    ]
    
    # Create distributed orchestrator
    distributed_orchestrator = DistributedOrchestrator(
        name="Global Load Test",
        proxies=proxies,
        credentials=credentials
    )
    
    print("Test: Distributed testing from multiple geographic locations")
    print("Locations: US-East, EU-West, Asia-Pacific")
    print("Users: Multiple credential sets with different access levels")
    print("Expected: Tests distributed across locations and users\n")
    
    # Run distributed test
    distributed_result = distributed_orchestrator.orchestrate_journey(
        journey=registration_journey,
        target_url="https://global-demo-app.com",
        replications=12  # Will be distributed across proxies and credentials
    )
    
    print("\nDistributed Test Results:")
    print(f"  Total Executions: {distributed_result.total_executions}")
    print(f"  Successful: {distributed_result.successful_executions}")
    print(f"  Success Rate: {distributed_result.success_rate:.1f}%")
    print(f"  Geographic Distribution: {len(proxies)} locations")
    print(f"  User Types: {len(credentials)} credential sets")


def demo_behaviors():
    """Demonstrate different behavior patterns."""
    print("\n" + "="*80)
    print("DEMO 5: Behavior Patterns - Human vs Machine vs Stealth")
    print("="*80)
    
    # Create a simple TTP for behavior demonstration
    demo_ttp = MockLoginBruteForceTTP(
        username="testuser",
        passwords=["password", "123456", "admin"],
        expected_result=False
    )
    
    print("\n5.1 Human Behavior - Variable Timing, Human-like Patterns")
    print("-" * 60)
    
    human_behavior = HumanBehavior(
        base_delay=1.0,
        delay_variance=0.5,
        typing_delay=0.05,
        mouse_movement=True,
        max_consecutive_failures=2
    )
    
    print("Behavior: Human-like with variable timing and realistic delays")
    
    human_executor = TTPExecutor(
        ttp=demo_ttp,
        target_url="https://demo-app.com/login",
        behavior=human_behavior,
        headless=True
    )
    human_executor.run()
    
    print("\n5.2 Machine Behavior - Fast, Consistent, Systematic")
    print("-" * 60)
    
    machine_behavior = MachineBehavior(
        delay=0.2,
        max_retries=5,
        fail_fast=False
    )
    
    print("Behavior: Machine-like with consistent timing and systematic approach")
    
    machine_executor = TTPExecutor(
        ttp=demo_ttp,
        target_url="https://demo-app.com/login",
        behavior=machine_behavior,
        headless=True
    )
    machine_executor.run()


def demo_integration():
    """Demonstrate all features working together."""
    print("\n" + "="*80)
    print("DEMO 6: Complete Integration - All Features Together")
    print("="*80)
    
    print("\n6.1 Comprehensive Security Assessment")
    print("-" * 60)
    
    # Create authentication for the assessment
    auth = BasicAuth(
        username="security_auditor",
        password="audit_password_2024",
        login_url="https://target-app.com/login"
    )
    
    # Create multiple TTPs with different expectations
    ttps = [
        MockSQLInjectionTTP(
            payloads=["' OR 1=1--", "'; DROP TABLE users;--"],
            expected_result=False,  # Should fail (good security)
            authentication=auth
        ),
        MockLoginBruteForceTTP(
            username="admin",
            passwords=["password", "123456", "admin"],
            expected_result=False,  # Should fail (good security)
            authentication=auth
        ),
        MockVulnerableTTP()  # Should succeed (find vulnerability)
    ]
    
    # Create a comprehensive journey
    assessment_journey = Journey(
        name="Complete Security Assessment",
        description="Full security assessment with authentication",
        authentication=auth
    )
    
    # Add assessment steps
    recon_step = Step("Reconnaissance", "Information gathering phase")
    recon_step.add_action(MockAction("Port Scanning", "Scan for open ports"))
    recon_step.add_action(MockAction("Service Detection", "Identify running services"))
    
    vuln_step = Step("Vulnerability Testing", "Test for security vulnerabilities")
    vuln_step.add_action(MockAction("SQL Injection Test", "Test for SQL injection", success_rate=0.1, expected_result=False))
    vuln_step.add_action(MockAction("XSS Testing", "Test for cross-site scripting", success_rate=0.15, expected_result=False))
    vuln_step.add_action(MockAction("CSRF Testing", "Test for CSRF vulnerabilities", success_rate=0.05, expected_result=False))
    
    assessment_journey.add_step(recon_step)
    assessment_journey.add_step(vuln_step)
    
    # Create orchestrator with human-like behavior
    orchestrator = ScaleOrchestrator(
        name="Security Assessment Orchestra",
        max_workers=3,
        ramp_up_delay=1.0
    )
    
    # Create human behavior for realistic assessment
    assessment_behavior = HumanBehavior(
        base_delay=2.0,
        delay_variance=1.0,
        max_consecutive_failures=3
    )
    
    print("Assessment: Complete security testing with authentication")
    print("Components: TTPs + Journeys + Orchestration + Human Behavior")
    print("Expected: Mixed results showing both good security and vulnerabilities\n")
    
    # Run individual TTPs
    print("Running Individual Security Tests:")
    for i, ttp in enumerate(ttps, 1):
        print(f"\n  Test {i}: {ttp.name}")
        executor = TTPExecutor(
            ttp=ttp,
            target_url="https://target-app.com",
            behavior=assessment_behavior,
            headless=True
        )
        executor.run()
    
    # Run the comprehensive journey
    print("\nRunning Comprehensive Security Journey:")
    journey_executor = JourneyExecutor(
        journey=assessment_journey,
        target_url="https://target-app.com",
        behavior=assessment_behavior,
        headless=True
    )
    journey_executor.run()
    
    # Run orchestrated assessment
    print("\nRunning Orchestrated Assessment (Multiple Parallel Assessments):")
    result = orchestrator.orchestrate_journey(
        journey=assessment_journey,
        target_url="https://target-app.com",
        replications=5,
        behavior=assessment_behavior
    )
    
    print("\nFinal Assessment Results:")
    print(f"  Total Security Assessments: {result.total_executions}")
    print(f"  Successful Assessments: {result.successful_executions}")
    print(f"  Assessment Success Rate: {result.success_rate:.1f}%")
    print(f"  Total Assessment Time: {result.execution_time:.2f}s")
    print(f"  Average Time per Assessment: {result.average_execution_time:.2f}s")


def main():
    """Run all demonstrations."""
    print("🔒 SCYTHE COMPREHENSIVE DEMONSTRATION")
    print("=" * 80)
    print("This demo showcases all major Scythe features:")
    print("• Expected Results (ExpectPass/ExpectFail)")
    print("• Authentication (Basic Auth, Bearer Tokens)")
    print("• Journeys (Multi-step workflows)")
    print("• Orchestrators (Scale, Batch, Distributed testing)")
    print("• Behaviors (Human, Machine patterns)")
    print("• Complete Integration")
    print("\nNote: This demo uses mock implementations for demonstration.")
    print("In real usage, these would interact with actual web applications.")
    
    try:
        # Run all demonstrations
        demo_expected_results()
        demo_authentication()
        demo_journeys()
        demo_orchestrators()
        demo_behaviors()
        demo_integration()
        
        print("\n" + "="*80)
        print("🎉 DEMONSTRATION COMPLETE!")
        print("="*80)
        print("All Scythe features demonstrated successfully!")
        print("\nKey Takeaways:")
        print("• Expected Results help distinguish between good security and vulnerabilities")
        print("• Authentication enables testing of protected areas")
        print("• Journeys allow complex, realistic test scenarios")
        print("• Orchestrators enable testing at scale across networks")
        print("• Behaviors make testing more realistic and harder to detect")
        print("• All components work together seamlessly")
        
        print("\nNext Steps:")
        print("• Create your own TTPs for specific security tests")
        print("• Build journeys that match your application workflows")
        print("• Use orchestrators for load and stress testing")
        print("• Implement authentication for your specific systems")
        print("• Customize behaviors for your testing requirements")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n\nDemo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()