<h1 align="center">Scythe</h1>

<h2 align="center">
  <img src="./assets/scythe.png" alt="scythe" width="200px">
  <br>
</h2>

<h4 align="center">A comprehensive framework for adverse conditions testing</h4>

## Overview

Scythe is a powerful Python-based framework designed for testing applications under adverse conditions. Whether you're conducting security assessments, load testing, functional validation, or simulating real-world stress scenarios, Scythe provides the tools to comprehensively evaluate how your systems perform when faced with challenging conditions.

While security testing through Tactics, Techniques, and Procedures (TTPs) is a core capability, Scythe's scope extends far beyond traditional security assessments. It's built to handle any scenario where you need to test system resilience, validate expected behaviors under stress, or simulate complex user interactions at scale.

## Core Philosophy

Scythe operates on the principle that robust systems must be tested under adverse conditions to ensure they perform reliably in production. These conditions can include:

- **Security-focused adversarial testing**: Simulating attack patterns and malicious behavior
- **High-demand load testing**: Overwhelming systems with legitimate but intensive usage
- **Complex user workflow validation**: Multi-step processes under various conditions
- **Distributed testing scenarios**: Simulating global user bases and network conditions
- **Edge case exploration**: Testing boundary conditions and unusual usage patterns
- **Failure scenario simulation**: Understanding system behavior when components fail

## Key Capabilities

### 🎯 **Comprehensive Testing Framework**
* **TTPs (Tactics, Techniques, Procedures)**: Security-focused testing with adversarial patterns
* **Journeys**: Multi-step workflow testing for complex user scenarios
* **Expected Results System**: Unit-testing-style validation with clear pass/fail criteria
* **Behavior Patterns**: Human, machine, and stealth execution patterns
* **Extensible Architecture**: Easy to add custom testing scenarios

### 🔐 **Authentication & Session Management**
* **Multiple Authentication Methods**: Basic auth, bearer tokens, custom mechanisms
* **Pre-execution Authentication**: Automatic login before test execution
* **Session State Management**: Maintain authentication across complex workflows
* **Multi-user Simulation**: Different credentials for distributed testing

### 🚀 **Scale & Distribution**
* **Concurrent Execution**: Run thousands of tests simultaneously
* **Geographic Distribution**: Execute tests from multiple network locations
* **Batch Processing**: Divide large test runs with intelligent retry logic
* **Resource Management**: Efficient distribution of credentials and network resources
* **Multiple Execution Strategies**: Sequential, parallel, and distributed patterns

### 📊 **Professional Reporting**
* **Clear Result Indicators**: ✓ Expected outcomes, ✗ Unexpected results
* **Comprehensive Logging**: Detailed execution tracking and analysis
* **Version Detection**: Automatic extraction of X-SCYTHE-TARGET-VERSION headers
* **Performance Metrics**: Timing, success rates, and resource utilization
* **Execution Statistics**: Detailed reporting across all test types

## Use Cases

### Security Testing
Validate security controls and detection capabilities:
```python
# Test that brute force protection works
login_protection_test = LoginBruteforceTTP(
    passwords=["password", "123456", "admin"],
    expected_result=False,  # Security should prevent this
    authentication=admin_auth
)
```

### Load Testing
Assess system performance under high demand:
```python
# Simulate 1000 concurrent user registrations
registration_load_test = ScaleOrchestrator(
    name="User Registration Load Test",
    max_workers=50
)
result = registration_load_test.orchestrate_journey(
    journey=user_registration_journey,
    replications=1000
)
```

### Functional Validation
Test complex multi-step workflows:
```python
# Complete e-commerce purchase workflow
purchase_journey = Journey("E-commerce Purchase Flow")
purchase_journey.add_step(user_login_step)
purchase_journey.add_step(product_selection_step)
purchase_journey.add_step(checkout_process_step)
purchase_journey.add_step(payment_validation_step)
```

### Distributed Testing
Simulate global user base scenarios:
```python
# Test from multiple geographic locations
global_test = DistributedOrchestrator(
    name="Global User Simulation",
    proxies=worldwide_proxy_list,
    credentials=regional_user_accounts
)
```

### Edge Case Testing
Explore boundary conditions and unusual scenarios:
```python
# Test file upload limits and edge cases
file_upload_ttp = FileUploadTTP(
    files=["large_file.zip", "empty.txt", "special_chars_名前.pdf"],
    expected_result=True,  # Should handle various file types
    size_limits_test=True
)
```

## Getting Started

### Prerequisites
- Python 3.8+
- Google Chrome browser
- Network access for target testing

### Installation

#### If you would like to use as a library:

setup the virtual environment
```bash
python3 -m venv venv

# source the venv
# bash,zsh: source venv/bin/activate
# fish: source venv/bin/activate.fish
```

install the package
```bash
# in an activated venv

pip3 install scythe-ttp
```

#### If you would like like to contribute:

1. Clone the repository:
   ```bash
   git clone https://github.com/EpykLab/scythe.git
   cd scythe
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Verify installation:
   ```bash
   python -c "from scythe.core.ttp import TTP; print('✅ Scythe installed successfully')"
   ```

## Quick Start Examples

### 1. Basic Security Testing

Test authentication controls with expected failure:

```python
from scythe.core.executor import TTPExecutor
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP

# Create a security test expecting controls to work
security_test = LoginBruteforceTTP(
    username="admin",
    passwords=["password", "123456", "admin"],
    username_selector="#username",
    password_selector="#password",
    submit_selector="#submit",
    expected_result=False  # We EXPECT security to prevent this
)

executor = TTPExecutor(ttp=security_test, target_url="http://app.com/login")
executor.run()
```

### 2. Multi-Step Workflow Testing

Test complex user journeys:

```python
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import NavigateAction, FillFormAction, ClickAction, AssertAction
from scythe.journeys.executor import JourneyExecutor

# Create comprehensive workflow test
workflow_test = Journey(
    name="User Onboarding Flow",
    description="Complete new user registration and setup process"
)

# Step 1: Registration
registration_step = Step("User Registration", "Create new account")
registration_step.add_action(NavigateAction(url="http://app.com/register"))
registration_step.add_action(FillFormAction(field_data={
    "#email": "test.user@example.com",
    "#password": "SecurePassword123!",
    "#confirm_password": "SecurePassword123!"
}))
registration_step.add_action(ClickAction(selector="#register-button"))
registration_step.add_action(AssertAction(
    assertion_type="url_contains",
    expected_value="verification"
))

# Step 2: Email Verification (simulated)
verification_step = Step("Email Verification", "Verify email address")
verification_step.add_action(NavigateAction(url="http://app.com/verify?token=test_token"))
verification_step.add_action(AssertAction(
    assertion_type="page_contains",
    expected_value="Email verified successfully"
))

# Step 3: Profile Setup
profile_step = Step("Profile Setup", "Complete user profile")
profile_step.add_action(NavigateAction(url="http://app.com/profile/setup"))
profile_step.add_action(FillFormAction(field_data={
    "#first_name": "Test",
    "#last_name": "User",
    "#company": "Example Corp"
}))
profile_step.add_action(ClickAction(selector="#save-profile"))

workflow_test.add_step(registration_step)
workflow_test.add_step(verification_step)
workflow_test.add_step(profile_step)

# Execute the workflow
executor = JourneyExecutor(journey=workflow_test, target_url="http://app.com")
result = executor.run()
```

### 3. Load Testing at Scale

Stress test with concurrent users:

```python
from scythe.orchestrators.scale import ScaleOrchestrator
from scythe.orchestrators.base import OrchestrationStrategy

# Create high-concurrency load test
load_test = ScaleOrchestrator(
    name="Application Load Test",
    strategy=OrchestrationStrategy.PARALLEL,
    max_workers=20,
    ramp_up_delay=0.1  # Gradual ramp-up
)

# Simulate 500 concurrent users going through checkout process
result = load_test.orchestrate_journey(
    journey=checkout_workflow,
    target_url="http://app.com",
    replications=500
)

print(f"Load Test Results:")
print(f"  Total Users Simulated: {result.total_executions}")
print(f"  Successful Completions: {result.successful_executions}")
print(f"  Success Rate: {result.success_rate:.1f}%")
print(f"  Average Response Time: {result.average_execution_time:.2f}s")
```

### 4. Global Distributed Testing

Test from multiple geographic locations:

```python
from scythe.orchestrators.distributed import DistributedOrchestrator, NetworkProxy, CredentialSet

# Define global testing infrastructure
global_proxies = [
    NetworkProxy("US-West", proxy_url="proxy-us-west.example.com:8080", location="US-West"),
    NetworkProxy("US-East", proxy_url="proxy-us-east.example.com:8080", location="US-East"),
    NetworkProxy("EU-West", proxy_url="proxy-eu-west.example.com:8080", location="EU-West"),
    NetworkProxy("Asia-Pacific", proxy_url="proxy-ap.example.com:8080", location="Asia-Pacific"),
    NetworkProxy("South-America", proxy_url="proxy-sa.example.com:8080", location="South-America")
]

# Different user profiles for realistic testing
user_profiles = [
    CredentialSet("premium_user", "premium@example.com", "PremiumPass123"),
    CredentialSet("basic_user", "basic@example.com", "BasicPass123"),
    CredentialSet("enterprise_user", "enterprise@example.com", "EnterprisePass123"),
    CredentialSet("trial_user", "trial@example.com", "TrialPass123")
]

# Create distributed test orchestrator
global_test = DistributedOrchestrator(
    name="Global Performance Assessment",
    proxies=global_proxies,
    credentials=user_profiles,
    proxy_rotation_strategy="round_robin",
    credential_rotation_strategy="random"
)

# Execute globally distributed test
result = global_test.orchestrate_journey(
    journey=core_application_journey,
    target_url="http://app.com",
    replications=100  # Will be distributed across all locations and user types
)

print(f"Global Test Results:")
print(f"  Locations Tested: {len(global_proxies)}")
print(f"  User Profiles: {len(user_profiles)}")
print(f"  Total Executions: {result.total_executions}")
print(f"  Geographic Distribution: {result.metadata.get('distribution_stats', {})}")
```

### 5. Authenticated Complex Testing

Test workflows requiring authentication:

```python
from scythe.auth.basic import BasicAuth
from scythe.auth.bearer import BearerTokenAuth

# Basic web application authentication
web_auth = BasicAuth(
    username="test_admin",
    password="admin_password",
    login_url="http://app.com/admin/login"
)

# API authentication for backend testing
api_auth = BearerTokenAuth(
    token_url="http://api.app.com/auth/token",
    username="api_user",
    password="api_secret"
)

# Create authenticated security test
admin_security_test = PrivilegeEscalationTTP(
    target_paths=["/admin/users", "/admin/settings", "/admin/logs"],
    expected_result=False,  # Should be prevented by access controls
    authentication=web_auth
)

# Create authenticated API stress test
api_stress_test = APIEndpointTTP(
    endpoints=["/api/users", "/api/reports", "/api/analytics"],
    request_rate=100,  # 100 requests per second
    expected_result=True,  # Should handle the load
    authentication=api_auth
)
```

## Advanced Features

### Expected Results System

Scythe uses a unit-testing-style approach to define expected outcomes:

```python
# Security test - expecting controls to work (test should "fail")
security_ttp = SecurityTestTTP(
    attack_vectors=["xss", "sqli", "csrf"],
    expected_result=False  # We EXPECT security to prevent these
)

# Performance test - expecting system to handle load (test should "pass")
performance_ttp = LoadTestTTP(
    concurrent_users=1000,
    expected_result=True  # We EXPECT the system to handle this load
)
```

**Output Examples:**
- ✓ **Expected Success**: System handled load as expected
- ✗ **Unexpected Success**: Security vulnerability found (should have been blocked)
- ✓ **Expected Failure**: Security controls working properly
- ✗ **Unexpected Failure**: System failed under expected normal load

### Behavior Patterns

Control how tests execute with realistic behavior patterns:

```python
from scythe.behaviors import HumanBehavior, MachineBehavior, StealthBehavior

# Human-like testing (realistic user simulation)
human_behavior = HumanBehavior(
    base_delay=2.0,           # Natural pause between actions
    delay_variance=1.0,       # Variation in timing
    typing_delay=0.1,         # Realistic typing speed
    error_probability=0.02    # Occasional user mistakes
)

# Machine testing (consistent, fast execution)
machine_behavior = MachineBehavior(
    delay=0.3,               # Fast, consistent timing
    max_retries=5,           # Systematic retry logic
    fail_fast=True           # Stop on critical errors
)

# Stealth testing (avoid detection/rate limiting)
stealth_behavior = StealthBehavior(
    min_delay=5.0,                    # Longer delays
    max_delay=15.0,                   # High variance
    session_cooldown=60.0,            # Breaks between sessions
    max_requests_per_session=20       # Limit requests per session
)

# Apply behavior to any test
executor = TTPExecutor(
    ttp=my_test,
    target_url="http://app.com",
    behavior=human_behavior  # Use human-like timing
)
```

### Version Detection

Scythe automatically captures the `X-SCYTHE-TARGET-VERSION` header from HTTP responses to track which version of your web application is being tested:

```python
from scythe.core.ttp import TTP
from scythe.core.executor import TTPExecutor

# Your web application should set this header:
# X-SCYTHE-TARGET-VERSION: 1.3.2

class MyTTP(TTP):
    def get_payloads(self):
        yield "test_payload"

    def execute_step(self, driver, payload):
        driver.get("http://your-app.com/login")
        # ... test logic ...

    def verify_result(self, driver):
        return "welcome" in driver.page_source

# Run the test
ttp = MyTTP("Version Test", "Test with version detection")
executor = TTPExecutor(ttp=ttp, target_url="http://your-app.com")
executor.run()
```

**Output includes version information:**
```
✓ EXPECTED SUCCESS: 'test_payload' | Version: 1.3.2
Target Version Summary:
  Results with version info: 1/1
  Version 1.3.2: 1 result(s)
```

**Server-side implementation examples:**
```python
# Python/Flask
@app.after_request
def add_version_header(response):
    response.headers['X-SCYTHE-TARGET-VERSION'] = '1.3.2'
    return response

# Node.js/Express
app.use((req, res, next) => {
    res.set('X-SCYTHE-TARGET-VERSION', '1.3.2');
    next();
});

# Java/Spring Boot
@Component
public class VersionHeaderFilter implements Filter {
    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain) {
        HttpServletResponse httpResponse = (HttpServletResponse) response;
        httpResponse.setHeader("X-SCYTHE-TARGET-VERSION", "1.3.2");
        chain.doFilter(request, response);
    }
}
```

This feature helps you:
- **Track test results** by application version
- **Verify deployment status** during testing
- **Correlate issues** with specific software versions
- **Ensure consistency** across test environments

### Custom Test Creation

Extend Scythe for specific testing needs:

```python
from scythe.core.ttp import TTP
from scythe.journeys.base import Action
from typing import Generator, Any

class CustomBusinessLogicTTP(TTP):
    """Test specific business logic under adverse conditions."""

    def __init__(self, business_scenarios: list, expected_result: bool = True):
        super().__init__(
            name="Business Logic Test",
            description="Test business logic edge cases",
            expected_result=expected_result
        )
        self.scenarios = business_scenarios

    def get_payloads(self) -> Generator[Any, None, None]:
        for scenario in self.scenarios:
            yield scenario

    def execute_step(self, driver, payload):
        # Implement your specific business logic testing
        # This could involve API calls, database interactions, etc.
        pass

    def verify_result(self, driver) -> bool:
        # Verify the business logic behaved correctly
        return self.check_business_rules(driver)

class CustomWorkflowAction(Action):
    """Custom action for specific workflow steps."""

    def __init__(self, workflow_step: str, parameters: dict):
        super().__init__(f"Custom {workflow_step}", f"Execute {workflow_step}")
        self.workflow_step = workflow_step
        self.parameters = parameters

    def execute(self, driver, context):
        # Implement custom workflow logic
        return self.perform_workflow_step(driver, context)
```

## Testing Scenarios

### E-commerce Platform Testing

```python
# Complete e-commerce stress test
ecommerce_suite = [
    # Security testing
    payment_security_test,      # Test payment form security
    user_data_protection_test,  # Test PII protection
    session_management_test,    # Test session security

    # Load testing
    product_catalog_load_test,  # High-traffic product browsing
    checkout_process_load_test, # Concurrent checkout processes
    search_functionality_test,  # Search under load

    # Workflow testing
    complete_purchase_journey,  # End-to-end purchase flow
    return_process_journey,     # Product return workflow
    account_management_journey  # User account operations
]

# Execute comprehensive test suite
orchestrator = ScaleOrchestrator(name="E-commerce Comprehensive Test")
for test in ecommerce_suite:
    result = orchestrator.orchestrate_journey(test, target_url="http://shop.com")
    print(f"{test.name}: {result.success_rate:.1f}% success rate")
```

### Financial Application Testing

```python
# High-security financial application testing
financial_test_suite = Journey("Financial Application Security Assessment")

# Multi-factor authentication testing
mfa_step = Step("MFA Security Test")
mfa_step.add_action(TTPAction(ttp=MFABypassTTP(expected_result=False)))

# Transaction integrity testing
transaction_step = Step("Transaction Integrity Test")
transaction_step.add_action(TTPAction(ttp=TransactionTamperingTTP(expected_result=False)))

# High-volume transaction testing
volume_step = Step("Transaction Volume Test")
volume_step.add_action(TTPAction(ttp=HighVolumeTransactionTTP(
    transactions_per_second=1000,
    expected_result=True  # Should handle high volume
)))

financial_test_suite.add_step(mfa_step)
financial_test_suite.add_step(transaction_step)
financial_test_suite.add_step(volume_step)
```

### Healthcare System Testing

```python
# HIPAA-compliant healthcare system testing
healthcare_journey = Journey("Healthcare System Compliance Test")

# Patient data protection
data_protection_step = Step("Patient Data Protection")
data_protection_step.add_action(TTPAction(ttp=PatientDataAccessTTP(
    expected_result=False  # Unauthorized access should be blocked
)))

# System availability under load
availability_step = Step("System Availability Test")
availability_step.add_action(TTPAction(ttp=EmergencyLoadTTP(
    concurrent_emergency_cases=500,
    expected_result=True  # System must remain available
)))

healthcare_journey.add_step(data_protection_step)
healthcare_journey.add_step(availability_step)
```

## Reporting and Analysis

### Comprehensive Result Analysis

```python
# Analyze test results
def analyze_test_results(orchestration_result):
    print("="*60)
    print("COMPREHENSIVE TEST ANALYSIS")
    print("="*60)

    print(f"Total Executions: {orchestration_result.total_executions}")
    print(f"Success Rate: {orchestration_result.success_rate:.1f}%")
    print(f"Average Execution Time: {orchestration_result.average_execution_time:.2f}s")

    # Performance metrics
    if orchestration_result.metadata.get('performance_stats'):
        stats = orchestration_result.metadata['performance_stats']
        print(f"Peak Response Time: {stats.get('peak_response_time', 'N/A')}")
        print(f"95th Percentile: {stats.get('p95_response_time', 'N/A')}")

    # Geographic distribution (if applicable)
    if orchestration_result.metadata.get('distribution_stats'):
        dist = orchestration_result.metadata['distribution_stats']
        print("Geographic Distribution:")
        for location, count in dist.get('location_usage', {}).items():
            print(f"  {location}: {count} executions")

    # Error analysis
    if orchestration_result.errors:
        print(f"\nErrors Encountered: {len(orchestration_result.errors)}")
        for i, error in enumerate(orchestration_result.errors[:5], 1):
            print(f"  {i}. {error}")

    print("="*60)

# Use with any orchestration result
result = orchestrator.orchestrate_journey(test_journey, "http://app.com", replications=100)
analyze_test_results(result)
```

## Best Practices

### 1. Test Design Principles

- **Start with expected outcomes**: Define what success and failure look like
- **Use realistic data**: Test with data that represents real usage patterns
- **Consider edge cases**: Test boundary conditions and unusual scenarios
- **Plan for scale**: Design tests that can scale from single instances to thousands

### 2. Security Testing Guidelines

- **Test security controls**: Verify that protection mechanisms work as expected
- **Use safe environments**: Never test against production without explicit authorization
- **Document findings**: Clearly report both expected and unexpected results
- **Follow responsible disclosure**: Report vulnerabilities through proper channels

### 3. Load Testing Best Practices

- **Gradual ramp-up**: Increase load gradually to identify breaking points
- **Monitor resources**: Track CPU, memory, and network usage during tests
- **Test realistic scenarios**: Use actual user workflows, not just simple requests
- **Plan for cleanup**: Ensure test data doesn't impact production systems

### 4. Distributed Testing Considerations

- **Network latency**: Account for geographic differences in network performance
- **Time zones**: Consider when testing across global user bases
- **Legal compliance**: Ensure testing complies with local laws and regulations
- **Resource limits**: Respect proxy and network provider usage limits

## Contributing

We welcome contributions to Scythe! Whether you're adding new test types, improving orchestration capabilities, or enhancing documentation, your contributions help make Scythe better for everyone.

### How to Contribute

1. **Fork the repository** and create a feature branch
2. **Write tests** for new functionality
3. **Follow coding standards** and include documentation
4. **Submit a pull request** with a clear description of changes

### Areas for Contribution

- **New TTP implementations** for specific security tests
- **Additional Journey actions** for workflow testing
- **Custom orchestration strategies** for specialized scenarios
- **Enhanced reporting** and analysis capabilities
- **Integration adapters** for popular testing tools
- **Documentation improvements** and examples

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Architecture

Scythe's modular architecture enables flexible testing scenarios:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     TTPs        │    │    Journeys     │    │  Orchestrators  │
│                 │    │                 │    │                 │
│ • Security Tests│    │ • Multi-step    │    │ • Scale Testing │
│ • Logic Tests   │    │ • Workflows     │    │ • Distribution  │
│ • Edge Cases    │    │ • User Stories  │    │ • Batch Runs    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Core Engine   │
                    │                 │
                    │ • Execution     │
                    │ • Authentication│
                    │ • Behaviors     │
                    │ • Reporting     │
                    └─────────────────┘
```

### Core Components

- **Core Engine**: Execution framework, authentication, and behavior management
- **TTPs**: Individual test procedures for specific scenarios
- **Journeys**: Multi-step workflows combining multiple actions
- **Orchestrators**: Scale and distribution management for large test runs
- **Behaviors**: Execution timing and pattern control
- **Authentication**: Session management and user simulation
- **Reporting**: Comprehensive result analysis and metrics

This architecture supports testing scenarios from simple security checks to complex, distributed, multi-user workflow validation at massive scale.

---

**Scythe**: Comprehensive adverse conditions testing for robust, reliable systems.



## Scythe CLI (embedded)

Scythe now ships with a lightweight CLI that helps you bootstrap and manage your local Scythe testing workspace. After installing the package (pipx recommended), a `scythe` command is available.

Note: The CLI is implemented with Typer, so `scythe --help` and per-command help (e.g., `scythe run --help`) are available. Command names and options remain the same as before.

- Install with pipx:
  - pipx install scythe-ttp
- Or install locally in editable mode for development:
  - pip install -e .

### Commands

- scythe init [--path PATH]
  - Initializes a Scythe project at PATH (default: current directory).
  - Creates:
    - ./.scythe/scythe.db (SQLite DB with tests and runs tables)
    - ./.scythe/scythe_tests/ (where your test scripts live)

- scythe new <name>
  - Creates a new test template at ./.scythe/scythe_tests/<name>.py and registers it in the DB (tests table).

- scythe run <name or name.py>
  - Runs the specified test from ./.scythe/scythe_tests and records the run into the DB (runs table). Exit code reflects success (0) or failure (non-zero).

- scythe db dump
  - Prints a JSON dump of the tests and runs tables from ./.scythe/scythe.db.

- scythe db sync-compat <name>
  - Reads COMPATIBLE_VERSIONS from ./.scythe/scythe_tests/<name>.py (if present) and updates the `tests.compatible_versions` field in the DB. If the variable is missing, the DB entry is set to empty and the command exits successfully.

### Test template

Created tests use a minimal template so you can start quickly:

```python
#!/usr/bin/env python3

# scythe test initial template

import argparse
import os
import sys
import time
from typing import List, Tuple

# Scythe framework imports
from scythe.core.executor import TTPExecutor
from scythe.behaviors import HumanBehavior


def scythe_test_definition(args):
    # TODO: implement your test using Scythe primitives.
    return True


def main():
    parser = argparse.ArgumentParser(description="Scythe test script")
    parser.add_argument('--url', help='Target URL (overridden by localhost unless FORCE_USE_CLI_URL=1)')
    args = parser.parse_args()

    ok = scythe_test_definition(args)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
```

Notes:
- The CLI looks for tests in ./.scythe/scythe_tests.
- Each `run` creates a record in the `runs` table with datetime, name_of_test, x_scythe_target_version (best-effort parsed from output), result, raw_output.
- Each `new` creates a record in the `tests` table with name, path, created_date, compatible_versions.
