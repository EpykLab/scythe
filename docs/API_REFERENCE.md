# Scythe API Reference

This document provides a comprehensive reference for all classes, methods, and functions in the Scythe framework.

## Table of Contents

1. [Core Classes](#core-classes)
2. [TTP Classes](#ttp-classes)
3. [Payload Generators](#payload-generators)
4. [Behavior Classes](#behavior-classes)
5. [Utility Functions](#utility-functions)
6. [Examples](#examples)

## Core Classes

### TTP (Abstract Base Class)

**Location:** `scythe.core.ttp`

Abstract base class for all TTP implementations.

```python
class TTP(ABC):
    def __init__(self, name: str, description: str)
```

#### Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Human-readable name for the TTP |
| `description` | `str` | Description of what the TTP does |

#### Abstract Methods

##### `get_payloads()`

```python
@abstractmethod
def get_payloads(self) -> Generator[Any, None, None]:
    """Yields payloads for the test execution."""
```

**Returns:** Generator that yields payloads one at a time

##### `execute_step()`

```python
@abstractmethod
def execute_step(self, driver: WebDriver, payload: Any) -> None:
    """Executes a single test action using the provided payload."""
```

**Parameters:**
- `driver` (`WebDriver`): Selenium WebDriver instance
- `payload` (`Any`): Current payload to test with

##### `verify_result()`

```python
@abstractmethod
def verify_result(self, driver: WebDriver) -> bool:
    """Verifies the outcome of the executed step."""
```

**Parameters:**
- `driver` (`WebDriver`): Selenium WebDriver instance

**Returns:** `True` if test indicates success/vulnerability, `False` otherwise

#### Properties

- `name` (`str`): TTP name
- `description` (`str`): TTP description

### TTPExecutor

**Location:** `scythe.core.executor`

Main engine for running TTP tests.

```python
class TTPExecutor:
    def __init__(self, 
                 ttp: TTP, 
                 target_url: str, 
                 headless: bool = True, 
                 delay: int = 1, 
                 behavior: Optional[Behavior] = None)
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ttp` | `TTP` | Required | TTP instance to execute |
| `target_url` | `str` | Required | Target URL for testing |
| `headless` | `bool` | `True` | Run browser in headless mode |
| `delay` | `int` | `1` | Default delay between steps (seconds) |
| `behavior` | `Optional[Behavior]` | `None` | Behavior to control execution |

#### Methods

##### `run()`

```python
def run(self) -> None:
    """Executes the full TTP test flow."""
```

Orchestrates the complete TTP execution including:
- WebDriver setup
- Behavior initialization
- Payload processing
- Result collection
- Cleanup

#### Properties

- `ttp` (`TTP`): The TTP being executed
- `target_url` (`str`): Target URL
- `delay` (`int`): Default delay between steps
- `behavior` (`Optional[Behavior]`): Execution behavior
- `results` (`List[Dict]`): List of successful results
- `logger` (`Logger`): Logger instance for this TTP
- `driver` (`Optional[WebDriver]`): Selenium WebDriver instance

#### Private Methods

##### `_setup_driver()`

```python
def _setup_driver(self) -> None:
    """Initializes the WebDriver."""
```

##### `_cleanup()`

```python
def _cleanup(self) -> None:
    """Closes the WebDriver and prints a summary."""
```

## TTP Classes

### LoginBruteforceTTP

**Location:** `scythe.ttps.web.login_bruteforce`

TTP for testing login forms with brute force attacks.

```python
class LoginBruteforceTTP(TTP):
    def __init__(self,
                 payload_generator: PayloadGenerator,
                 username: str,
                 username_selector: str,
                 password_selector: str,
                 submit_selector: str)
```

#### Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `payload_generator` | `PayloadGenerator` | Generator for password payloads |
| `username` | `str` | Username to test with |
| `username_selector` | `str` | CSS selector for username field |
| `password_selector` | `str` | CSS selector for password field |
| `submit_selector` | `str` | CSS selector for submit button |

#### Success Criteria

- URL no longer contains "login" (case-insensitive)

#### Example

```python
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.payloads.generators import StaticPayloadGenerator

passwords = StaticPayloadGenerator(["password", "admin", "123456"])
login_ttp = LoginBruteforceTTP(
    payload_generator=passwords,
    username="admin",
    username_selector="#username",
    password_selector="#password",
    submit_selector="#submit"
)
```

### InputFieldInjector

**Location:** `scythe.ttps.web.sql_injection`

TTP for testing SQL injection through form input fields.

```python
class InputFieldInjector(TTP):
    def __init__(self,
                 target_url: str,
                 field_selector: str,
                 submit_selector: str,
                 payload_generator: PayloadGenerator)
```

#### Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `target_url` | `str` | Target URL for testing |
| `field_selector` | `str` | CSS selector for input field |
| `submit_selector` | `str` | CSS selector for submit button |
| `payload_generator` | `PayloadGenerator` | Generator for SQL injection payloads |

#### Success Criteria

- Page source contains "sql" or "source" (case-insensitive)

### URLManipulation

**Location:** `scythe.ttps.web.sql_injection`

TTP for testing SQL injection through URL parameter manipulation.

```python
class URLManipulation(TTP):
    def __init__(self,
                 payload_generator: PayloadGenerator,
                 target_url: str)
```

#### Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `payload_generator` | `PayloadGenerator` | Generator for SQL injection payloads |
| `target_url` | `str` | Base URL to append payloads to |

#### Success Criteria

- Page source contains "sql" or "source" (case-insensitive)

### GuessUUIDInURL

**Location:** `scythe.ttps.web.uuid_guessing`

TTP for testing predictable or guessable UUIDs in URL paths.

```python
class GuessUUIDInURL(TTP):
    def __init__(self,
                 target_url: str,
                 uri_root_path: str,
                 payload_generator: PayloadGenerator)
```

#### Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `target_url` | `str` | Base URL |
| `uri_root_path` | `str` | Path prefix where UUIDs are tested |
| `payload_generator` | `PayloadGenerator` | Generator for UUID payloads |

#### Success Criteria

- HTTP response is not 404, 401, or 403

## Payload Generators

### PayloadGenerator (Base Class)

**Location:** `scythe.payloads.generators`

Abstract base class for all payload generators.

```python
class PayloadGenerator:
    def __iter__(self) -> Generator[Any, None, None]:
        raise NotImplementedError
    
    def __call__(self) -> Generator[Any, None, None]:
        return self.__iter__()
```

#### Abstract Methods

##### `__iter__()`

```python
def __iter__(self) -> Generator[Any, None, None]:
    """Returns generator that yields payloads."""
```

### StaticPayloadGenerator

**Location:** `scythe.payloads.generators`

Generates payloads from a static list in memory.

```python
class StaticPayloadGenerator(PayloadGenerator):
    def __init__(self, payload_list: List[Any])
```

#### Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `payload_list` | `List[Any]` | List of payloads to yield |

#### Example

```python
from scythe.payloads.generators import StaticPayloadGenerator

# String payloads
passwords = StaticPayloadGenerator(["password", "admin", "123456"])

# Mixed types
mixed = StaticPayloadGenerator(["string", 123, {"key": "value"}])
```

### WordlistPayloadGenerator

**Location:** `scythe.payloads.generators`

Generates payloads from a file, one per line.

```python
class WordlistPayloadGenerator(PayloadGenerator):
    def __init__(self, filepath: str)
```

#### Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `filepath` | `str` | Path to wordlist file |

#### File Format

```
password
123456
admin
qwerty
letmein
```

#### Example

```python
from scythe.payloads.generators import WordlistPayloadGenerator

# Load from file
wordlist = WordlistPayloadGenerator("wordlists/rockyou.txt")

# Use with TTP
for payload in wordlist:
    print(payload)  # Outputs each line from file
```

## Behavior Classes

### Behavior (Base Class)

**Location:** `scythe.behaviors.base`

Abstract base class for all behaviors.

```python
class Behavior(ABC):
    def __init__(self, name: str, description: str)
```

#### Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Human-readable name for the behavior |
| `description` | `str` | Description of the behavior |

#### Methods

##### `configure()`

```python
def configure(self, config: Dict[str, Any]) -> None:
    """Configure behavior with custom parameters."""
```

##### `pre_execution()`

```python
def pre_execution(self, driver: WebDriver, target_url: str) -> None:
    """Called before TTP execution begins."""
```

##### `post_execution()`

```python
def post_execution(self, driver: WebDriver, results: List[Dict]) -> None:
    """Called after TTP execution completes."""
```

##### `pre_step()`

```python
def pre_step(self, driver: WebDriver, payload: Any, step_number: int) -> None:
    """Called before each TTP step."""
```

##### `post_step()`

```python
def post_step(self, driver: WebDriver, payload: Any, step_number: int, success: bool) -> None:
    """Called after each TTP step."""
```

##### `get_step_delay()`

```python
def get_step_delay(self, step_number: int) -> float:
    """Return delay before next step in seconds."""
```

##### `should_continue()`

```python
def should_continue(self, step_number: int, consecutive_failures: int) -> bool:
    """Decide whether to continue execution."""
```

##### `on_error()`

```python
def on_error(self, error: Exception, step_number: int) -> bool:
    """Handle errors during execution. Return True to continue, False to stop."""
```

#### Properties

- `name` (`str`): Behavior name
- `description` (`str`): Behavior description

### DefaultBehavior

**Location:** `scythe.behaviors`

Maintains original TTPExecutor functionality for backward compatibility.

```python
class DefaultBehavior(Behavior):
    def __init__(self, delay: float = 1.0)
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `delay` | `float` | `1.0` | Fixed delay between actions |

### HumanBehavior

**Location:** `scythe.behaviors`

Emulates human-like interaction patterns.

```python
class HumanBehavior(Behavior):
    def __init__(self,
                 base_delay: float = 3.0,
                 delay_variance: float = 1.5,
                 typing_delay: float = 0.1,
                 mouse_movement: bool = True,
                 max_consecutive_failures: int = 3)
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_delay` | `float` | `3.0` | Base delay between actions |
| `delay_variance` | `float` | `1.5` | Random variance in timing |
| `typing_delay` | `float` | `0.1` | Delay between keystrokes |
| `mouse_movement` | `bool` | `True` | Enable random mouse movements |
| `max_consecutive_failures` | `int` | `3` | Give up after failures |

#### Characteristics

- Variable delays with realistic timing patterns
- Random mouse movements and page scanning
- Human-like typing with keystroke delays
- Gradual acceleration as "user gets comfortable"
- Natural pauses to "read" results
- Conservative failure handling

### MachineBehavior

**Location:** `scythe.behaviors`

Provides consistent, predictable timing for automated testing.

```python
class MachineBehavior(Behavior):
    def __init__(self,
                 delay: float = 0.5,
                 max_retries: int = 5,
                 retry_delay: float = 1.0,
                 fail_fast: bool = True)
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `delay` | `float` | `0.5` | Fixed delay between actions |
| `max_retries` | `int` | `5` | Maximum retries on failure |
| `retry_delay` | `float` | `1.0` | Fixed delay between retries |
| `fail_fast` | `bool` | `True` | Stop on critical errors |

#### Characteristics

- Consistent, predictable timing
- No unnecessary movements or delays
- Systematic error handling with retries
- Fail-fast on critical errors
- Optimal browser settings for performance

### StealthBehavior

**Location:** `scythe.behaviors`

Focuses on evading detection through randomization and anti-fingerprinting.

```python
class StealthBehavior(Behavior):
    def __init__(self,
                 min_delay: float = 5.0,
                 max_delay: float = 15.0,
                 burst_probability: float = 0.1,
                 long_pause_probability: float = 0.15,
                 long_pause_duration: float = 30.0,
                 max_requests_per_session: int = 20,
                 session_cooldown: float = 300.0)
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_delay` | `float` | `5.0` | Minimum delay between actions |
| `max_delay` | `float` | `15.0` | Maximum delay between actions |
| `burst_probability` | `float` | `0.1` | Chance of burst actions |
| `long_pause_probability` | `float` | `0.15` | Chance of long pauses |
| `long_pause_duration` | `float` | `30.0` | Duration of long pauses |
| `max_requests_per_session` | `int` | `20` | Requests before session reset |
| `session_cooldown` | `float` | `300.0` | Cooldown between sessions |

#### Characteristics

- Highly variable timing to avoid pattern detection
- User agent rotation and session management
- Reconnaissance and cleanup activities
- Burst and pause patterns
- Conservative failure handling
- Anti-fingerprinting techniques

## Utility Functions

### Helper Functions

#### `_random_delay()`

```python
def _random_delay(min_val: float, max_val: float) -> float:
    """Generate random delay between min and max values."""
```

**Parameters:**
- `min_val` (`float`): Minimum delay value
- `max_val` (`float`): Maximum delay value

**Returns:** Random float between min_val and max_val

## Examples

### Basic TTP Execution

```python
from scythe.core.executor import TTPExecutor
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.payloads.generators import StaticPayloadGenerator

# Create payload generator
passwords = StaticPayloadGenerator(["password", "admin", "123456"])

# Create TTP
login_ttp = LoginBruteforceTTP(
    payload_generator=passwords,
    username="admin",
    username_selector="#username",
    password_selector="#password",
    submit_selector="#submit"
)

# Execute TTP
executor = TTPExecutor(
    ttp=login_ttp,
    target_url="http://example.com/login"
)
executor.run()
```

### TTP with Behavior

```python
from scythe.behaviors import HumanBehavior

# Create human behavior
human_behavior = HumanBehavior(
    base_delay=2.0,
    delay_variance=1.0,
    mouse_movement=True
)

# Execute with behavior
executor = TTPExecutor(
    ttp=login_ttp,
    target_url="http://example.com/login",
    behavior=human_behavior
)
executor.run()
```

### Custom TTP Implementation

```python
from scythe.core.ttp import TTP
from selenium.webdriver.common.by import By

class CustomTTP(TTP):
    def __init__(self, payloads):
        super().__init__(
            name="Custom TTP",
            description="Custom TTP implementation"
        )
        self.payloads = payloads
    
    def get_payloads(self):
        yield from self.payloads
    
    def execute_step(self, driver, payload):
        # Custom execution logic
        element = driver.find_element(By.ID, "test")
        element.send_keys(payload)
    
    def verify_result(self, driver):
        # Custom verification logic
        return "success" in driver.page_source.lower()
```

### Custom Payload Generator

```python
from scythe.payloads.generators import PayloadGenerator
import random

class RandomStringGenerator(PayloadGenerator):
    def __init__(self, count=100, length=8):
        self.count = count
        self.length = length
    
    def __iter__(self):
        import string
        for _ in range(self.count):
            yield ''.join(random.choices(
                string.ascii_letters + string.digits, 
                k=self.length
            ))
```

### Custom Behavior

```python
from scythe.behaviors.base import Behavior
import time
import random

class CustomBehavior(Behavior):
    def __init__(self):
        super().__init__(
            name="Custom Behavior",
            description="Custom behavior implementation"
        )
    
    def get_step_delay(self, step_number):
        # Custom delay logic
        return random.uniform(1.0, 3.0)
    
    def should_continue(self, step_number, consecutive_failures):
        # Custom continuation logic
        return consecutive_failures < 5
    
    def pre_step(self, driver, payload, step_number):
        # Custom pre-step logic
        print(f"About to execute step {step_number}")
    
    def on_error(self, error, step_number):
        # Custom error handling
        print(f"Error in step {step_number}: {error}")
        return True  # Continue execution
```

## Error Handling

### Common Exceptions

#### `NoSuchElementException`

Raised when Selenium cannot find an element.

```python
from selenium.common.exceptions import NoSuchElementException

try:
    element = driver.find_element(By.ID, "nonexistent")
except NoSuchElementException:
    print("Element not found")
```

#### `TimeoutException`

Raised when Selenium operations timeout.

```python
from selenium.common.exceptions import TimeoutException

try:
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "element"))
    )
except TimeoutException:
    print("Element did not appear in time")
```

### Best Practices

1. **Always handle exceptions in custom TTPs**
2. **Use explicit waits instead of fixed delays**
3. **Implement proper cleanup in custom behaviors**
4. **Validate inputs in constructor methods**
5. **Log errors appropriately for debugging**

## Type Hints

The Scythe framework uses Python type hints throughout. Key types:

```python
from typing import Generator, Any, Optional, List, Dict
from selenium.webdriver.remote.webdriver import WebDriver

# Common type aliases
PayloadType = Any
ResultType = Dict[str, Any]
ConfigType = Dict[str, Any]
```

## Version Compatibility

- **Python:** 3.8+
- **Selenium:** 4.0+
- **Chrome:** Latest stable version recommended

## Constants

### Default Values

```python
# TTPExecutor defaults
DEFAULT_DELAY = 1
DEFAULT_HEADLESS = True

# Behavior defaults
DEFAULT_BASE_DELAY = 3.0
DEFAULT_DELAY_VARIANCE = 1.5
DEFAULT_TYPING_DELAY = 0.1
DEFAULT_MAX_FAILURES = 3

# Chrome options
DEFAULT_CHROME_OPTIONS = [
    "--no-sandbox",
    "--disable-dev-shm-usage"
]
```

This API reference provides the complete interface for the Scythe framework. For usage examples and patterns, see the other documentation files and the `examples/` directory.