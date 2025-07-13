# Scythe Behaviors Framework

The Scythe Behaviors framework allows TTP authors to define execution behaviors that control how TTPs are executed, making them more realistic and harder to detect.

## Overview

Behaviors control various aspects of TTP execution including:
- Timing between actions
- Mouse movements and interaction patterns  
- Error handling and retry logic
- Session management
- Anti-detection techniques

## Quick Start

### Basic Usage

```python
from scythe.core.executor import TTPExecutor
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.payloads.generators import StaticPayloadGenerator
from scythe.behaviors import HumanBehavior

# Create your TTP as usual
payload_generator = StaticPayloadGenerator(["password123", "admin", "test"])
login_ttp = LoginBruteforceTTP(
    payload_generator=payload_generator,
    username="admin",
    username_selector="#username",
    password_selector="#password", 
    submit_selector="#submit"
)

# Create a behavior
human_behavior = HumanBehavior(
    base_delay=2.0,
    delay_variance=1.0,
    mouse_movement=True
)

# Use behavior with executor
executor = TTPExecutor(
    ttp=login_ttp,
    target_url="http://example.com/login",
    behavior=human_behavior  # Optional parameter
)

executor.run()
```

### Backward Compatibility

The behaviors feature is completely optional. Existing code continues to work unchanged:

```python
# This still works exactly as before
executor = TTPExecutor(
    ttp=login_ttp,
    target_url="http://example.com/login"
)
executor.run()
```

## Built-in Behaviors

### DefaultBehavior

Maintains the original TTPExecutor functionality for backward compatibility.

```python
from scythe.behaviors import DefaultBehavior

behavior = DefaultBehavior(delay=1.0)
```

**Characteristics:**
- Fixed delay between actions
- No special interaction patterns
- Identical to original TTPExecutor behavior

### HumanBehavior

Emulates human-like interaction patterns to make TTPs appear more realistic.

```python
from scythe.behaviors import HumanBehavior

behavior = HumanBehavior(
    base_delay=3.0,              # Base delay between actions
    delay_variance=1.5,          # Random variance in timing
    typing_delay=0.1,            # Delay between keystrokes
    mouse_movement=True,         # Enable random mouse movements
    max_consecutive_failures=3   # Give up after failures
)
```

**Characteristics:**
- Variable delays with realistic timing patterns
- Random mouse movements and page scanning
- Human-like typing with keystroke delays
- Gradual acceleration as "user gets comfortable"
- Natural pauses to "read" results
- Conservative failure handling

**Use Cases:**
- Social engineering simulations
- Testing human-based detection systems
- Realistic phishing simulations
- User behavior analysis

### MachineBehavior

Provides consistent, predictable timing suitable for automated testing scenarios.

```python
from scythe.behaviors import MachineBehavior

behavior = MachineBehavior(
    delay=0.5,           # Fixed delay between actions
    max_retries=5,       # Maximum retries on failure
    retry_delay=1.0,     # Fixed delay between retries
    fail_fast=True       # Stop on critical errors
)
```

**Characteristics:**
- Consistent, predictable timing
- No unnecessary movements or delays
- Systematic error handling with retries
- Fail-fast on critical errors
- Optimal browser settings for performance

**Use Cases:**
- Automated security testing
- Performance benchmarking
- CI/CD integration
- High-speed vulnerability scanning

### StealthBehavior

Focuses on evading detection through randomization and anti-fingerprinting techniques.

```python
from scythe.behaviors import StealthBehavior

behavior = StealthBehavior(
    min_delay=5.0,                    # Minimum delay between actions
    max_delay=15.0,                   # Maximum delay between actions
    burst_probability=0.1,            # Chance of burst actions
    long_pause_probability=0.15,      # Chance of long pauses
    long_pause_duration=30.0,         # Duration of long pauses
    max_requests_per_session=20,      # Requests before session reset
    session_cooldown=300.0            # Cooldown between sessions
)
```

**Characteristics:**
- Highly variable timing to avoid pattern detection
- User agent rotation and session management
- Reconnaissance and cleanup activities
- Burst and pause patterns
- Conservative failure handling
- Anti-fingerprinting techniques

**Use Cases:**
- Red team operations
- Advanced persistent threat simulation
- Evasion testing
- Steganographic attacks

## Creating Custom Behaviors

### Basic Custom Behavior

```python
from scythe.behaviors.base import Behavior
from selenium.webdriver.remote.webdriver import WebDriver
import time
import random

class CustomBehavior(Behavior):
    def __init__(self, custom_param: str = "default"):
        super().__init__(
            name="Custom Behavior",
            description="My custom behavior implementation"
        )
        self.custom_param = custom_param
    
    def pre_execution(self, driver: WebDriver, target_url: str) -> None:
        """Called before TTP execution begins"""
        print(f"Starting custom behavior on {target_url}")
        # Custom setup logic here
    
    def pre_step(self, driver: WebDriver, payload: Any, step_number: int) -> None:
        """Called before each TTP step"""
        print(f"About to execute step {step_number}")
        # Custom pre-step logic here
    
    def post_step(self, driver: WebDriver, payload: Any, step_number: int, success: bool) -> None:
        """Called after each TTP step"""
        status = "SUCCESS" if success else "FAILED"
        print(f"Step {step_number} result: {status}")
        # Custom post-step logic here
    
    def post_execution(self, driver: WebDriver, results: list) -> None:
        """Called after TTP execution completes"""
        print(f"Execution complete. {len(results)} successes found")
        # Custom cleanup logic here
    
    def get_step_delay(self, step_number: int) -> float:
        """Return delay before next step"""
        return random.uniform(1.0, 3.0)
    
    def should_continue(self, step_number: int, consecutive_failures: int) -> bool:
        """Decide whether to continue execution"""
        return consecutive_failures < 5
    
    def on_error(self, error: Exception, step_number: int) -> bool:
        """Handle errors during execution"""
        print(f"Error in step {step_number}: {error}")
        return True  # Continue execution
```

### Advanced Custom Behavior

```python
class AdvancedCustomBehavior(Behavior):
    def __init__(self):
        super().__init__(
            name="Advanced Custom Behavior", 
            description="Advanced behavior with configuration"
        )
        self.request_count = 0
        self.success_count = 0
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure behavior with custom parameters"""
        super().configure(config)
        self.max_requests = config.get('max_requests', 100)
        self.success_threshold = config.get('success_threshold', 5)
    
    def pre_execution(self, driver: WebDriver, target_url: str) -> None:
        # Set custom browser options
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def get_step_delay(self, step_number: int) -> float:
        # Adaptive timing based on success rate
        if self.request_count > 0:
            success_rate = self.success_count / self.request_count
            if success_rate > 0.5:
                return self._random_delay(0.5, 1.0)  # Speed up if successful
            else:
                return self._random_delay(2.0, 5.0)  # Slow down if failing
        return 2.0
    
    def should_continue(self, step_number: int, consecutive_failures: int) -> bool:
        # Stop if we've found enough successes
        if self.success_count >= self.success_threshold:
            return False
        # Stop if we've made too many requests
        if self.request_count >= self.max_requests:
            return False
        return consecutive_failures < 10
    
    def post_step(self, driver: WebDriver, payload: Any, step_number: int, success: bool) -> None:
        self.request_count += 1
        if success:
            self.success_count += 1
            # Take screenshot on success
            driver.save_screenshot(f"success_{step_number}.png")
```

## Behavior Lifecycle

The behavior lifecycle follows this sequence:

1. **pre_execution()** - Called once before TTP execution begins
2. For each payload:
   - **should_continue()** - Check if execution should continue
   - **pre_step()** - Called before each step
   - TTP executes (get URL, execute_step, verify_result)
   - **get_step_delay()** - Get delay for next step
   - **post_step()** - Called after each step
   - **on_error()** - Called if an error occurs
3. **post_execution()** - Called once after execution completes

## Configuration

Behaviors can be configured using the `configure()` method:

```python
behavior = CustomBehavior()
behavior.configure({
    'max_requests': 50,
    'timeout': 30,
    'custom_setting': 'value'
})
```

## Error Handling

Behaviors can control error handling through the `on_error()` method:

```python
def on_error(self, error: Exception, step_number: int) -> bool:
    if "TimeoutException" in str(type(error)):
        # Take a longer pause on timeout
        time.sleep(10)
        return True  # Continue execution
    elif "NoSuchElementException" in str(type(error)):
        # Give up on element not found
        return False  # Stop execution
    else:
        return True  # Continue for other errors
```

## Best Practices

### 1. Behavior Selection

- **HumanBehavior**: Use for realistic simulations and social engineering tests
- **MachineBehavior**: Use for automated testing and CI/CD pipelines  
- **StealthBehavior**: Use for red team operations and evasion testing
- **Custom**: Create for specific requirements or attack patterns

### 2. Performance Considerations

- Behaviors add overhead - consider this for high-speed testing
- StealthBehavior can significantly slow execution
- MachineBehavior provides best performance for automated testing

### 3. Detection Evasion

- Use StealthBehavior for maximum evasion
- Randomize timing patterns to avoid detection
- Consider implementing user agent rotation
- Add reconnaissance and cleanup phases

### 4. Logging and Monitoring

```python
class LoggingBehavior(Behavior):
    def __init__(self):
        super().__init__("Logging Behavior", "Logs all behavior events")
        self.logger = logging.getLogger("behavior")
    
    def pre_step(self, driver, payload, step_number):
        self.logger.info(f"Executing step {step_number} with payload: {payload}")
    
    def post_step(self, driver, payload, step_number, success):
        self.logger.info(f"Step {step_number} completed: {'SUCCESS' if success else 'FAILED'}")
```

## Integration with Existing TTPs

All existing TTPs work with behaviors without modification. The behavior system is designed to be completely optional and backward compatible.

## Examples

See `examples/behavior_demo.py` for comprehensive examples of all behavior types and usage patterns.

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're importing from the correct behavior module
2. **Selenium Errors**: Some behaviors modify browser settings - check compatibility
3. **Performance Issues**: Adjust timing parameters if behaviors are too slow/fast

### Debug Mode

Enable debug logging to see behavior events:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Behavior Testing

Test custom behaviors with simple TTPs first:

```python
# Simple test TTP for behavior testing
class TestTTP(TTP):
    def get_payloads(self):
        yield from ["test1", "test2", "test3"]
    
    def execute_step(self, driver, payload):
        print(f"Testing with: {payload}")
    
    def verify_result(self, driver):
        return False  # Always fail for testing
```
