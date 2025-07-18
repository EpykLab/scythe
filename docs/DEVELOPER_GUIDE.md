# Scythe Developer Guide

This guide provides comprehensive instructions for developers who want to contribute to the Scythe framework or extend it with custom components for adverse conditions testing.

Scythe is designed as a comprehensive testing framework for evaluating applications under challenging conditions - whether through security-focused adversarial testing, high-demand load scenarios, complex multi-step workflows, or distributed testing across global networks.

## Table of Contents

- [Core Concepts](#core-concepts)
- [Creating Custom TTPs](#creating-custom-ttps)
- [Authentication Systems](#authentication-systems)
- [Journey Actions and Steps](#journey-actions-and-steps)
- [Custom Orchestrators](#custom-orchestrators)
- [Behavior Patterns](#behavior-patterns)
- [Payload Generators](#payload-generators)
- [Testing Guidelines](#testing-guidelines)
- [Coding Standards](#coding-standards)
- [Contributing](#contributing)

## Core Concepts

The Scythe framework is built around several key abstractions designed for comprehensive adverse conditions testing:

### TTPs (Tactics, Techniques, and Procedures)
A TTP represents a single test procedure that can be used for various adverse conditions testing scenarios. While originally designed for security testing that emulates attacker behavior, TTPs are flexible and can test:

**Security Scenarios:**
- Attack pattern simulation and vulnerability detection
- Security control validation and bypass testing
- Authentication and authorization edge cases

**Performance & Load Scenarios:**
- High-volume request testing and system stress
- Resource exhaustion and capacity validation
- Concurrent user simulation

**Business Logic Scenarios:**
- Edge case testing and boundary condition validation
- Error handling and recovery testing
- Data integrity under adverse conditions

Each TTP:
- Generates test inputs/payloads for various scenarios
- Executes test actions using Selenium WebDriver
- Verifies whether the test succeeded or failed
- Supports expected results (pass/fail expectations like unit testing)
- Can require authentication before execution
- Can be combined with others for complex testing scenarios

### Journeys
Journeys represent complex, multi-step test scenarios that go beyond individual TTPs. They enable testing of complete workflows under adverse conditions, including:

**Functional Testing Scenarios:**
- Complete user workflows (registration, checkout, file upload)
- Multi-page application flows and state transitions
- Cross-feature integration testing

**Security Testing Scenarios:**
- Multi-step attack chains and advanced persistent threats
- Authentication bypass workflows
- Privilege escalation sequences

**Performance Testing Scenarios:**
- End-to-end user journey performance
- Complex workflow load testing
- Resource utilization across multiple steps

Journeys are composed of:
- **Steps**: Logical groupings of actions that accomplish specific goals
- **Actions**: Individual operations like navigation, form filling, TTP execution, or assertions
- **Context**: Shared data between steps and actions for state management
- **Error Handling**: Configurable behavior for step failures

### Orchestrators
Orchestrators manage execution of TTPs and Journeys at scale, enabling comprehensive adverse conditions testing across various dimensions:

**Scale Orchestration:**
- Concurrent execution for load testing and capacity validation
- Ramp-up strategies for gradual stress application
- Resource management and throttling controls

**Distributed Orchestration:**
- Geographic distribution across multiple network locations
- Multi-user simulation with different credential sets
- Proxy rotation and network condition simulation

**Batch Orchestration:**
- Large test runs divided into manageable batches
- Retry logic for failed executions
- Progress tracking and incremental reporting

**Specialized Orchestration:**
- Time-based scheduling for sustained testing
- Adaptive orchestration based on system response
- Custom distribution strategies for specific scenarios

### Authentication
Authentication systems provide comprehensive pre-execution authentication for realistic testing scenarios:

**Web Application Authentication:**
- **BasicAuth**: Username/password form authentication with intelligent field detection
- **Multi-factor**: Support for 2FA and complex authentication flows
- **Session Management**: Automatic session handling and renewal

**API Authentication:**
- **BearerTokenAuth**: API token authentication with automatic refresh
- **OAuth flows**: Support for various OAuth 2.0 patterns
- **Custom headers**: Flexible header-based authentication

**Advanced Authentication:**
- **Role-based testing**: Different authentication levels for permission testing
- **Session hijacking simulation**: Security-focused authentication testing
- **Cross-domain authentication**: Complex SSO and federated authentication scenarios

### Behaviors
Behaviors control execution patterns to simulate realistic adverse conditions:

**Realistic User Simulation:**
- **HumanBehavior**: Variable timing, realistic patterns, occasional errors
- **PowerUserBehavior**: Fast but still human-like patterns for experienced users
- **NewUserBehavior**: Slower, more exploratory patterns with higher error rates

**Automated Testing Patterns:**
- **MachineBehavior**: Consistent, fast execution for systematic testing
- **StressTestBehavior**: Aggressive timing for maximum system stress
- **EnduranceBehavior**: Sustained long-term testing patterns

**Evasive and Advanced Patterns:**
- **StealthBehavior**: Evasive patterns with randomization to avoid detection
- **AdversarialBehavior**: Patterns designed to trigger edge cases and errors
- **AdaptiveBehavior**: Dynamic adjustment based on system response

**Custom Behaviors**: Application-specific behaviors for specialized testing scenarios

## Creating Custom TTPs

### Basic TTP Structure

Every TTP must inherit from the `TTP` base class and implement three methods:

```python
from scythe.core.ttp import TTP
from selenium.webdriver.remote.webdriver import WebDriver
from typing import Generator, Any

class CustomTTP(TTP):
    def __init__(self, custom_param: str, expected_result: bool = True):
        super().__init__(
            name="Custom Security Test",
            description="Description of what this TTP tests",
            expected_result=expected_result
        )
        self.custom_param = custom_param
    
    def get_payloads(self) -> Generator[Any, None, None]:
        """Generate payloads for testing."""
        # Yield test payloads
        yield "payload1"
        yield "payload2"
    
    def execute_step(self, driver: WebDriver, payload: Any) -> None:
        """Execute a single test step with the given payload."""
        # Perform the test action using Selenium
        driver.get(f"http://target.com/search?q={payload}")
    
    def verify_result(self, driver: WebDriver) -> bool:
        """Verify if the test succeeded."""
        # Check for indicators of success/vulnerability
        return "error" in driver.page_source.lower()
```

### Advanced TTP Example: SQL Injection

```python
from scythe.core.ttp import TTP
from scythe.payloads.generators import StaticPayloadGenerator
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

class SQLInjectionTTP(TTP):
    def __init__(self, 
                 target_parameter: str,
                 injection_payloads: list = None,
                 expected_result: bool = False,
                 authentication=None):
        super().__init__(
            name="SQL Injection Test",
            description=f"Tests for SQL injection in parameter: {target_parameter}",
            expected_result=expected_result,
            authentication=authentication
        )
        
        self.target_parameter = target_parameter
        
        # Default SQL injection payloads
        default_payloads = [
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR 1=1 --",
            "'; DROP TABLE users; --",
            "' UNION SELECT 1,2,3 --",
            "admin'/*"
        ]
        
        self.payload_generator = StaticPayloadGenerator(
            injection_payloads or default_payloads
        )
    
    def get_payloads(self):
        yield from self.payload_generator()
    
    def execute_step(self, driver: WebDriver, payload: str) -> None:
        try:
            # Find input field and inject payload
            input_field = driver.find_element(By.NAME, self.target_parameter)
            input_field.clear()
            input_field.send_keys(payload)
            
            # Submit form
            submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
            submit_button.click()
            
        except NoSuchElementException as e:
            # Log the error but don't fail the test
            import logging
            logger = logging.getLogger(self.name)
            logger.warning(f"Element not found: {e}")
    
    def verify_result(self, driver: WebDriver) -> bool:
        """Check for SQL injection indicators."""
        page_content = driver.page_source.lower()
        
        # SQL error indicators
        sql_errors = [
            "sql syntax",
            "mysql_fetch",
            "ora-01756",
            "microsoft access driver",
            "sqlite_error",
            "postgresql error",
            "warning: mysql",
            "valid mysql result",
            "sqlstate",
            "error in your sql syntax"
        ]
        
        # Check for SQL errors (indicates potential vulnerability)
        for error in sql_errors:
            if error in page_content:
                return True
        
        # Check for unusual responses that might indicate injection
        unusual_indicators = [
            "union select",
            "information_schema",
            "sysdatabases",
            "mysql.user"
        ]
        
        for indicator in unusual_indicators:
            if indicator in page_content:
                return True
        
        return False
```

### TTP with Authentication

```python
from scythe.auth.basic import BasicAuth

class AuthenticatedTTP(TTP):
    def __init__(self, username: str, password: str):
        # Create authentication
        auth = BasicAuth(
            username=username,
            password=password,
            login_url="http://target.com/login"
        )
        
        super().__init__(
            name="Authenticated Security Test",
            description="Security test requiring authentication",
            authentication=auth
        )
    
    def get_payloads(self):
        yield "authenticated_payload"
    
    def execute_step(self, driver, payload):
        # This will execute after authentication succeeds
        driver.get(f"http://target.com/admin?test={payload}")
    
    def verify_result(self, driver):
        return "admin panel" in driver.page_source.lower()
```

## Authentication Systems

### Creating Custom Authentication

```python
from scythe.auth.base import Authentication, AuthenticationError
from selenium.webdriver.remote.webdriver import WebDriver

class CustomAuth(Authentication):
    def __init__(self, api_key: str, secret: str):
        super().__init__(
            name="Custom API Authentication",
            description="Custom authentication mechanism"
        )
        self.api_key = api_key
        self.secret = secret
    
    def authenticate(self, driver: WebDriver, target_url: str) -> bool:
        """Implement custom authentication logic."""
        try:
            # Example: Set authentication headers via JavaScript
            driver.execute_script(f"""
                localStorage.setItem('api_key', '{self.api_key}');
                localStorage.setItem('secret', '{self.secret}');
            """)
            
            # Navigate to authentication endpoint
            driver.get(f"{target_url}/auth/verify")
            
            # Check if authentication succeeded
            if self.is_authenticated(driver):
                self.authenticated = True
                return True
            else:
                raise AuthenticationError("Custom authentication failed")
                
        except Exception as e:
            raise AuthenticationError(f"Authentication error: {str(e)}")
    
    def is_authenticated(self, driver: WebDriver) -> bool:
        """Check if the session is authenticated."""
        try:
            # Check for authentication indicators
            page_source = driver.page_source.lower()
            return "authenticated" in page_source and "logout" in page_source
        except Exception:
            return False
    
    def get_auth_headers(self) -> dict:
        """Return headers for API requests."""
        return {
            "X-API-Key": self.api_key,
            "X-Secret": self.secret
        }
```

### OAuth 2.0 Authentication Example

```python
class OAuth2Auth(Authentication):
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(
            name="OAuth 2.0 Authentication",
            description="OAuth 2.0 flow authentication"
        )
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
    
    def authenticate(self, driver: WebDriver, target_url: str) -> bool:
        try:
            # Step 1: Navigate to OAuth authorization URL
            auth_url = f"{target_url}/oauth/authorize?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code"
            driver.get(auth_url)
            
            # Step 2: Handle OAuth consent (implementation depends on provider)
            # This would typically involve clicking consent buttons
            
            # Step 3: Extract authorization code from redirect
            # Implementation depends on OAuth flow
            
            # Step 4: Exchange code for access token
            # This would typically be done via HTTP request
            
            return True
        except Exception as e:
            raise AuthenticationError(f"OAuth authentication failed: {str(e)}")
```

## Journey Actions and Steps

### Creating Custom Actions

```python
from scythe.journeys.base import Action
from selenium.webdriver.remote.webdriver import WebDriver
from typing import Dict, Any

class CustomDatabaseAction(Action):
    def __init__(self, sql_query: str, expected_result: bool = True):
        super().__init__(
            name="Database Query Action",
            description=f"Execute database query: {sql_query}",
            expected_result=expected_result
        )
        self.sql_query = sql_query
    
    def execute(self, driver: WebDriver, context: Dict[str, Any]) -> bool:
        try:
            # Example: Execute database query via web interface
            driver.get("http://target.com/admin/database")
            
            # Find query input
            query_input = driver.find_element(By.ID, "sql-query")
            query_input.clear()
            query_input.send_keys(self.sql_query)
            
            # Execute query
            execute_button = driver.find_element(By.ID, "execute-query")
            execute_button.click()
            
            # Wait for results
            time.sleep(2)
            
            # Check if query executed successfully
            results = driver.find_element(By.ID, "query-results")
            
            # Store results in context for other actions
            context['last_query_results'] = results.text
            
            return "error" not in results.text.lower()
            
        except Exception as e:
            self.store_result('error', str(e))
            return False

class APITestAction(Action):
    def __init__(self, endpoint: str, method: str = "GET", payload: dict = None):
        super().__init__(
            name=f"API {method} Test",
            description=f"Test {method} request to {endpoint}"
        )
        self.endpoint = endpoint
        self.method = method
        self.payload = payload or {}
    
    def execute(self, driver: WebDriver, context: Dict[str, Any]) -> bool:
        try:
            # Use JavaScript to make API call from browser context
            script = f"""
                var xhr = new XMLHttpRequest();
                xhr.open('{self.method}', '{self.endpoint}', false);
                xhr.setRequestHeader('Content-Type', 'application/json');
                
                // Add auth headers if available in context
                if (localStorage.getItem('auth_token')) {{
                    xhr.setRequestHeader('Authorization', 'Bearer ' + localStorage.getItem('auth_token'));
                }}
                
                try {{
                    xhr.send('{json.dumps(self.payload)}');
                    return {{
                        status: xhr.status,
                        response: xhr.responseText
                    }};
                }} catch(e) {{
                    return {{
                        status: 0,
                        error: e.message
                    }};
                }}
            """
            
            result = driver.execute_script(script)
            
            # Store API response in context
            context[f'api_response_{self.endpoint}'] = result
            
            # Consider 2xx status codes as success
            return 200 <= result.get('status', 0) < 300
            
        except Exception as e:
            self.store_result('error', str(e))
            return False
```

### Complex Journey Example

```python
from scythe.journeys.base import Journey, Step

def create_ecommerce_security_journey():
    """Create a comprehensive e-commerce security testing journey."""
    
    journey = Journey(
        name="E-commerce Security Assessment",
        description="Complete security testing for online store"
    )
    
    # Step 1: Registration and Authentication
    auth_step = Step(
        name="User Registration & Authentication",
        description="Test user registration and login security"
    )
    
    auth_step.add_action(NavigateAction("http://target.com/register"))
    auth_step.add_action(FillFormAction({
        "#username": "security_test_user",
        "#email": "test@security.com",
        "#password": "TestPassword123!"
    }))
    auth_step.add_action(ClickAction("#register-button"))
    auth_step.add_action(AssertAction("url_contains", "welcome"))
    
    # Step 2: Product Security Testing
    product_step = Step(
        name="Product Security Testing",
        description="Test product browsing and manipulation"
    )
    
    product_step.add_action(NavigateAction("http://target.com/products"))
    product_step.add_action(ClickAction(".product-item:first-child"))
    
    # Test price manipulation (should fail)
    price_manipulation_ttp = PriceManipulationTTP(expected_result=False)
    product_step.add_action(TTPAction(ttp=price_manipulation_ttp))
    
    # Step 3: Payment Security
    payment_step = Step(
        name="Payment Security Testing",
        description="Test payment processing security"
    )
    
    payment_step.add_action(NavigateAction("http://target.com/checkout"))
    payment_step.add_action(FillFormAction({
        "#card-number": "4111111111111111",
        "#expiry": "12/25",
        "#cvv": "123"
    }))
    
    # Test payment injection (should fail)
    payment_injection_ttp = PaymentInjectionTTP(expected_result=False)
    payment_step.add_action(TTPAction(ttp=payment_injection_ttp))
    
    journey.add_step(auth_step)
    journey.add_step(product_step)
    journey.add_step(payment_step)
    
    return journey
```

## Custom Orchestrators

### Creating Custom Orchestration Strategies

```python
from scythe.orchestrators.base import Orchestrator, OrchestrationResult, OrchestrationStrategy
import time
import threading

class TimeBasedOrchestrator(Orchestrator):
    """Orchestrator that runs tests at specific time intervals."""
    
    def __init__(self, name: str, interval_seconds: int = 60):
        super().__init__(
            name=name,
            description=f"Executes tests every {interval_seconds} seconds",
            strategy=OrchestrationStrategy.SEQUENTIAL
        )
        self.interval_seconds = interval_seconds
        self.running = False
    
    def orchestrate_ttp(self, ttp, target_url, replications=1, **kwargs):
        """Orchestrate TTP execution at time intervals."""
        
        self._log_orchestration_start(ttp.name, "TTP", replications, target_url)
        
        start_time = time.time()
        results = []
        errors = []
        
        try:
            self.running = True
            
            for i in range(replications):
                if not self.running:
                    break
                    
                self.logger.info(f"Starting scheduled execution {i+1}/{replications}")
                
                # Execute TTP
                from scythe.core.executor import TTPExecutor
                executor = TTPExecutor(ttp=ttp, target_url=target_url, **kwargs)
                
                # Run in separate thread to avoid blocking
                execution_thread = threading.Thread(target=executor.run)
                execution_thread.start()
                execution_thread.join()
                
                # Collect results (simplified)
                results.append({
                    'execution_id': f"scheduled_{i+1}",
                    'success': True,  # Simplified
                    'timestamp': time.time()
                })
                
                # Wait for next interval (except on last execution)
                if i < replications - 1:
                    self.logger.info(f"Waiting {self.interval_seconds}s until next execution")
                    time.sleep(self.interval_seconds)
                    
        except Exception as e:
            self.logger.error(f"Error in time-based orchestration: {e}")
            errors.append(str(e))
        
        end_time = time.time()
        
        # Create result
        result = OrchestrationResult(
            orchestrator_name=self.name,
            strategy=self.strategy,
            total_executions=len(results),
            successful_executions=sum(1 for r in results if r.get('success')),
            failed_executions=len(results) - sum(1 for r in results if r.get('success')),
            start_time=start_time,
            end_time=end_time,
            execution_time=end_time - start_time,
            results=results,
            errors=errors,
            metadata={'interval_seconds': self.interval_seconds}
        )
        
        self._log_orchestration_end(result)
        return result
    
    def orchestrate_journey(self, journey, target_url, replications=1, **kwargs):
        """Similar implementation for journeys."""
        # Implementation similar to orchestrate_ttp
        pass
    
    def stop(self):
        """Stop the orchestrator."""
        self.running = False
```

### Cloud-Based Distributed Orchestrator

```python
class CloudOrchestrator(Orchestrator):
    """Orchestrator that distributes tests across cloud instances."""
    
    def __init__(self, name: str, cloud_instances: list):
        super().__init__(
            name=name,
            description="Distributes tests across cloud instances"
        )
        self.cloud_instances = cloud_instances
    
    def orchestrate_ttp(self, ttp, target_url, replications=1, **kwargs):
        """Distribute TTP execution across cloud instances."""
        
        start_time = time.time()
        results = []
        errors = []
        
        try:
            # Divide replications across instances
            replications_per_instance = replications // len(self.cloud_instances)
            remaining_replications = replications % len(self.cloud_instances)
            
            # Use ThreadPoolExecutor for parallel execution
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            with ThreadPoolExecutor(max_workers=len(self.cloud_instances)) as executor:
                futures = []
                
                for i, instance in enumerate(self.cloud_instances):
                    instance_replications = replications_per_instance
                    if i < remaining_replications:
                        instance_replications += 1
                    
                    if instance_replications > 0:
                        future = executor.submit(
                            self._execute_on_instance,
                            instance, ttp, target_url, instance_replications, **kwargs
                        )
                        futures.append(future)
                
                # Collect results
                for future in as_completed(futures):
                    try:
                        instance_results, instance_errors = future.result()
                        results.extend(instance_results)
                        errors.extend(instance_errors)
                    except Exception as e:
                        errors.append(f"Cloud instance execution failed: {str(e)}")
        
        except Exception as e:
            errors.append(f"Cloud orchestration failed: {str(e)}")
        
        end_time = time.time()
        
        return OrchestrationResult(
            orchestrator_name=self.name,
            strategy=OrchestrationStrategy.PARALLEL,
            total_executions=len(results),
            successful_executions=sum(1 for r in results if r.get('success')),
            failed_executions=len(results) - sum(1 for r in results if r.get('success')),
            start_time=start_time,
            end_time=end_time,
            execution_time=end_time - start_time,
            results=results,
            errors=errors,
            metadata={'cloud_instances': len(self.cloud_instances)}
        )
    
    def _execute_on_instance(self, instance, ttp, target_url, replications, **kwargs):
        """Execute TTP on a specific cloud instance."""
        # Implementation would use cloud APIs or remote execution
        # This is a simplified example
        results = []
        errors = []
        
        try:
            # Simulate cloud execution
            for i in range(replications):
                # In reality, this would trigger execution on the cloud instance
                results.append({
                    'execution_id': f"{instance['id']}_{i}",
                    'success': True,
                    'instance': instance['id'],
                    'region': instance.get('region', 'unknown')
                })
        except Exception as e:
            errors.append(f"Instance {instance['id']} failed: {str(e)}")
        
        return results, errors
```

## Behavior Patterns

### Creating Custom Behaviors

```python
from scythe.behaviors.base import Behavior
import random
import time

class AdaptiveBehavior(Behavior):
    """Behavior that adapts based on success/failure rates."""
    
    def __init__(self, initial_delay: float = 1.0):
        super().__init__(
            name="Adaptive Behavior",
            description="Adapts timing based on success rates"
        )
        self.initial_delay = initial_delay
        self.current_delay = initial_delay
        self.success_count = 0
        self.failure_count = 0
    
    def get_step_delay(self, step_number: int) -> float:
        """Adaptive delay based on success rate."""
        if step_number == 1:
            return self.initial_delay
        
        # Calculate success rate
        total_attempts = self.success_count + self.failure_count
        if total_attempts > 0:
            success_rate = self.success_count / total_attempts
            
            # Adapt delay based on success rate
            if success_rate > 0.8:
                # High success rate, speed up
                self.current_delay = max(0.1, self.current_delay * 0.9)
            elif success_rate < 0.3:
                # Low success rate, slow down
                self.current_delay = min(10.0, self.current_delay * 1.2)
        
        return self.current_delay + random.uniform(-0.2, 0.2)
    
    def should_continue(self, step_number: int, consecutive_failures: int) -> bool:
        """Continue unless too many consecutive failures."""
        return consecutive_failures < 5
    
    def post_step(self, driver, payload, step_number: int, success: bool):
        """Update success/failure counters."""
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
    
    def on_error(self, error: Exception, step_number: int) -> bool:
        """Handle errors with adaptive logic."""
        self.failure_count += 1
        
        # Increase delay after errors
        self.current_delay = min(10.0, self.current_delay * 1.5)
        
        return True  # Continue execution

class GeographicBehavior(Behavior):
    """Behavior that simulates different geographic locations."""
    
    def __init__(self, regions: list):
        super().__init__(
            name="Geographic Behavior",
            description="Simulates requests from different geographic regions"
        )
        self.regions = regions
        self.current_region_index = 0
    
    def pre_execution(self, driver, target_url: str):
        """Set up geographic simulation."""
        current_region = self.regions[self.current_region_index]
        
        # Simulate different time zones and network characteristics
        if current_region == "Asia":
            self.base_delay = 2.0  # Higher latency
        elif current_region == "Europe":
            self.base_delay = 1.0  # Medium latency
        else:  # US
            self.base_delay = 0.5  # Lower latency
    
    def get_step_delay(self, step_number: int) -> float:
        """Geographic-based delay."""
        return self.base_delay + random.uniform(0, 0.5)
    
    def pre_step(self, driver, payload, step_number: int):
        """Rotate through regions."""
        if step_number % 5 == 0:  # Change region every 5 steps
            self.current_region_index = (self.current_region_index + 1) % len(self.regions)
            current_region = self.regions[self.current_region_index]
            
            # You could also set different user agents, languages, etc.
            driver.execute_script(f"console.log('Simulating request from {current_region}');")
```

## Payload Generators

### Creating Custom Payload Generators

```python
from scythe.payloads.base import PayloadGenerator
import itertools
import random

class FuzzingPayloadGenerator(PayloadGenerator):
    """Generator for fuzzing payloads."""
    
    def __init__(self, base_strings: list, fuzz_chars: str = "<>\"'&"):
        self.base_strings = base_strings
        self.fuzz_chars = fuzz_chars
    
    def __iter__(self):
        """Generate fuzzing payloads."""
        # Original strings
        for base in self.base_strings:
            yield base
        
        # Fuzzed versions
        for base in self.base_strings:
            for char in self.fuzz_chars:
                yield f"{base}{char}"
                yield f"{char}{base}"
                yield f"{base}{char * 5}"
        
        # Combined fuzzing
        for base in self.base_strings:
            for combo in itertools.combinations(self.fuzz_chars, 2):
                yield f"{''.join(combo)}{base}{''.join(combo)}"

class AIGeneratedPayloadGenerator(PayloadGenerator):
    """Generator that uses AI/ML to create payloads."""
    
    def __init__(self, target_type: str, model_path: str = None):
        self.target_type = target_type
        self.model_path = model_path
        self.generated_payloads = []
    
    def _generate_payloads(self):
        """Generate payloads using AI model."""
        if self.target_type == "sql_injection":
            # In reality, this would use an ML model
            base_payloads = [
                "' OR 1=1 --",
                "'; DROP TABLE users; --",
                "' UNION SELECT * FROM information_schema.tables --"
            ]
            
            # Simulate AI variations
            for base in base_payloads:
                # Add variations
                yield base
                yield base.replace("1=1", "2=2")
                yield base.replace("users", "accounts")
                yield base.upper()
                yield base.replace(" ", "/**/")
    
    def __iter__(self):
        if not self.generated_payloads:
            self.generated_payloads = list(self._generate_payloads())
        
        return iter(self.generated_payloads)

class ContextAwarePayloadGenerator(PayloadGenerator):
    """Generator that adapts based on context."""
    
    def __init__(self, context_analyzer):
        self.context_analyzer = context_analyzer
        self.analyzed_context = None
    
    def analyze_target(self, driver):
        """Analyze target to generate context-aware payloads."""
        self.analyzed_context = self.context_analyzer.analyze(driver)
    
    def __iter__(self):
        if not self.analyzed_context:
            # Default payloads if no context
            yield "default_payload"
            return
        
        # Generate payloads based on analyzed context
        if self.analyzed_context.get("framework") == "wordpress":
            yield "wp-admin"
            yield "../wp-config.php"
        elif self.analyzed_context.get("framework") == "django":
            yield "admin/"
            yield "debug"
        
        # Technology-specific payloads
        if "mysql" in self.analyzed_context.get("database", ""):
            yield "' OR 1=1 # mysql comment"
        elif "postgresql" in self.analyzed_context.get("database", ""):
            yield "' OR 1=1 -- postgresql comment"
```

## Testing Guidelines

### Unit Testing TTPs

```python
import unittest
from unittest.mock import Mock, MagicMock
from scythe.core.executor import TTPExecutor

class TestCustomTTP(unittest.TestCase):
    
    def setUp(self):
        self.mock_driver = Mock()
        self.ttp = CustomTTP("test_param")
    
    def test_payload_generation(self):
        """Test that payloads are generated correctly."""
        payloads = list(self.ttp.get_payloads())
        self.assertGreater(len(payloads), 0)
        self.assertIn("expected_payload", payloads)
    
    def test_execute_step(self):
        """Test step execution."""
        # Setup mock driver
        self.mock_driver.get = Mock()
        
        # Execute step
        self.ttp.execute_step(self.mock_driver, "test_payload")
        
        # Verify interactions
        self.mock_driver.get.assert_called_once()
    
    def test_verify_result_positive(self):
        """Test positive result verification."""
        # Setup mock response
        self.mock_driver.page_source = "error: sql syntax"
        
        result = self.ttp.verify_result(self.mock_driver)
        self.assertTrue(result)
    
    def test_verify_result_negative(self):
        """Test negative result verification."""
        # Setup mock response
        self.mock_driver.page_source = "normal page content"
        
        result = self.ttp.verify_result(self.mock_driver)
        self.assertFalse(result)
    
    def test_ttp_with_executor(self):
        """Test TTP integration with executor."""
        # Mock the WebDriver creation
        with patch('scythe.core.executor.webdriver.Chrome') as mock_chrome:
            mock_driver = Mock()
            mock_chrome.return_value = mock_driver
            mock_driver.page_source = "test content"
            
            executor = TTPExecutor(
                ttp=self.ttp,
                target_url="http://test.