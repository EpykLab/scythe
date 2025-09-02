# Scythe TTP Executor Framework

The TTP Executor is the core engine that orchestrates the execution of TTPs (Tactics, Techniques, and Procedures) within the Scythe framework. This document provides comprehensive coverage of the executor's functionality, configuration options, and advanced usage patterns.

## Overview

The `TTPExecutor` class serves as the main interface between your TTPs and the browser automation layer. It handles:

- WebDriver lifecycle management
- TTP execution orchestration
- Result collection and reporting
- Error handling and recovery
- Integration with the behavior system
- Logging and monitoring

## Basic Usage

### Simple Execution

```python
from scythe.core.executor import TTPExecutor
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.payloads.generators import StaticPayloadGenerator

# Create payload generator
payload_generator = StaticPayloadGenerator(["password", "admin", "123456"])

# Create TTP
login_ttp = LoginBruteforceTTP(
    payload_generator=payload_generator,
    username="admin",
    username_selector="#username",
    password_selector="#password",
    submit_selector="#submit"
)

# Create and run executor
executor = TTPExecutor(
    ttp=login_ttp,
    target_url="http://example.com/login"
)

executor.run()
```

### Execution with Behaviors

```python
from scythe.behaviors import HumanBehavior

# Create behavior for realistic execution
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

## Constructor Parameters

### Required Parameters

#### `ttp: TTP`
The TTP instance to execute.

```python
from scythe.ttps.web.sql_injection import URLManipulation

sql_ttp = URLManipulation(
    payload_generator=sql_payloads,
    target_url="http://example.com"
)

executor = TTPExecutor(ttp=sql_ttp, target_url="http://example.com")
```

#### `target_url: str`
The target URL where the TTP will be executed.

```python
executor = TTPExecutor(
    ttp=my_ttp,
    target_url="https://target-application.com/login"
)
```

### Optional Parameters

#### `headless: bool = True`
Controls whether the browser runs in headless mode.

```python
# Headless execution (default)
executor = TTPExecutor(ttp=my_ttp, target_url="http://example.com", headless=True)

# Visible browser for debugging
executor = TTPExecutor(ttp=my_ttp, target_url="http://example.com", headless=False)
```

**Use Cases:**
- `headless=True`: Production runs, CI/CD, automated testing
- `headless=False`: Development, debugging, demonstrations

#### `delay: int = 1`
Default delay between TTP steps (in seconds). Only used when no behavior is specified.

```python
# Fast execution
executor = TTPExecutor(ttp=my_ttp, target_url="http://example.com", delay=0.5)

# Conservative execution
executor = TTPExecutor(ttp=my_ttp, target_url="http://example.com", delay=5)
```

#### `behavior: Optional[Behavior] = None`
Behavior instance to control execution patterns.

```python
from scythe.behaviors import StealthBehavior

stealth_behavior = StealthBehavior(
    min_delay=5.0,
    max_delay=15.0,
    session_cooldown=300.0
)

executor = TTPExecutor(
    ttp=my_ttp,
    target_url="http://example.com",
    behavior=stealth_behavior
)
```

## Execution Lifecycle

### 1. Initialization Phase

```python
executor = TTPExecutor(ttp=my_ttp, target_url="http://example.com")
# - Validates parameters
# - Sets up Chrome options
# - Initializes logging
# - Prepares result collection
```

### 2. WebDriver Setup

```python
executor.run()  # Calls _setup_driver()
# - Creates Chrome WebDriver instance
# - Applies browser options
# - Logs initialization status
```

### 3. Pre-Execution Phase

```python
# If behavior is specified:
behavior.pre_execution(driver, target_url)
# - Behavior-specific setup
# - Browser configuration
# - Initial page preparation
```

### 4. Payload Execution Loop

For each payload from the TTP:

```python
# 1. Continuation check
if behavior and not behavior.should_continue(step_number, consecutive_failures):
    break

# 2. Pre-step behavior
if behavior:
    behavior.pre_step(driver, payload, step_number)

# 3. TTP execution
driver.get(target_url)
ttp.execute_step(driver, payload)

# 4. Delay
sleep(behavior.get_step_delay(step_number) if behavior else delay)

# 5. Result verification
success = ttp.verify_result(driver)

# 6. Post-step behavior
if behavior:
    behavior.post_step(driver, payload, step_number, success)

# 7. Error handling
except Exception as e:
    if behavior:
        continue_execution = behavior.on_error(e, step_number)
```

### 5. Post-Execution Phase

```python
# If behavior is specified:
behavior.post_execution(driver, results)
# - Cleanup operations
# - Final reporting
# - Resource disposal
```

### 6. Cleanup Phase

```python
executor._cleanup()
# - Closes WebDriver
# - Prints execution summary
# - Logs final results
```

## Configuration Options

### Chrome Browser Options

The executor automatically configures Chrome with security and performance options:

```python
# Default Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # If headless=True
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
```

### Custom Chrome Configuration

For advanced use cases, you can extend the executor:

```python
class CustomTTPExecutor(TTPExecutor):
    def _setup_driver(self):
        """Override to add custom Chrome options."""
        # Add custom options
        self.chrome_options.add_argument("--disable-images")
        self.chrome_options.add_argument("--disable-javascript")
        self.chrome_options.add_argument("--user-agent=Custom-Agent/1.0")
        
        # Call parent setup
        super()._setup_driver()

# Usage
executor = CustomTTPExecutor(ttp=my_ttp, target_url="http://example.com")
```

### Logging Configuration

The executor uses Python's logging framework:

```python
# Default logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ttp_test.log'),
        logging.StreamHandler()
    ]
)
```

### Custom Logging

```python
import logging

# Configure custom logging
logging.basicConfig(
    level=logging.DEBUG,  # More verbose
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('custom_ttp.log'),
        logging.StreamHandler()
    ]
)

# Run executor with custom logging
executor = TTPExecutor(ttp=my_ttp, target_url="http://example.com")
executor.run()
```

## Advanced Usage Patterns

### 1. Multiple TTP Execution

```python
class MultiTTPExecutor:
    def __init__(self, ttps: List[TTP], target_url: str, behavior=None):
        self.ttps = ttps
        self.target_url = target_url
        self.behavior = behavior
        self.all_results = {}
    
    def run_all(self):
        """Execute multiple TTPs sequentially."""
        for ttp in self.ttps:
            print(f"\n=== Executing {ttp.name} ===")
            
            executor = TTPExecutor(
                ttp=ttp,
                target_url=self.target_url,
                behavior=self.behavior
            )
            
            executor.run()
            self.all_results[ttp.name] = executor.results
        
        self._print_summary()
    
    def _print_summary(self):
        """Print summary of all TTP executions."""
        print("\n" + "="*60)
        print("MULTI-TTP EXECUTION SUMMARY")
        print("="*60)
        
        for ttp_name, results in self.all_results.items():
            print(f"{ttp_name}: {len(results)} vulnerabilities found")

# Usage
ttps = [login_ttp, sql_ttp, xss_ttp]
multi_executor = MultiTTPExecutor(ttps, "http://example.com")
multi_executor.run_all()
```

### 2. Parallel TTP Execution

```python
import concurrent.futures
import threading

class ParallelTTPExecutor:
    def __init__(self, ttps: List[TTP], target_url: str, max_workers=3):
        self.ttps = ttps
        self.target_url = target_url
        self.max_workers = max_workers
        self.results_lock = threading.Lock()
        self.all_results = {}
    
    def run_parallel(self):
        """Execute multiple TTPs in parallel."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all TTP executions
            future_to_ttp = {
                executor.submit(self._execute_ttp, ttp): ttp 
                for ttp in self.ttps
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_ttp):
                ttp = future_to_ttp[future]
                try:
                    results = future.result()
                    with self.results_lock:
                        self.all_results[ttp.name] = results
                except Exception as e:
                    print(f"TTP {ttp.name} failed: {e}")
    
    def _execute_ttp(self, ttp: TTP):
        """Execute a single TTP and return results."""
        executor = TTPExecutor(
            ttp=ttp,
            target_url=self.target_url,
            headless=True  # Always headless for parallel execution
        )
        executor.run()
        return executor.results

# Usage
parallel_executor = ParallelTTPExecutor(ttps, "http://example.com", max_workers=2)
parallel_executor.run_parallel()
```

### 3. Conditional Execution

```python
class ConditionalTTPExecutor(TTPExecutor):
    def __init__(self, ttp: TTP, target_url: str, conditions: Dict[str, callable], **kwargs):
        super().__init__(ttp, target_url, **kwargs)
        self.conditions = conditions
    
    def run(self):
        """Run TTP only if all conditions are met."""
        # Check pre-execution conditions
        for condition_name, condition_func in self.conditions.items():
            if not condition_func():
                self.logger.info(f"Condition '{condition_name}' not met. Skipping execution.")
                return
        
        # All conditions met, proceed with execution
        super().run()

# Define conditions
def check_target_online():
    import requests
    try:
        response = requests.get("http://example.com", timeout=5)
        return response.status_code == 200
    except:
        return False

def check_time_window():
    import datetime
    current_hour = datetime.datetime.now().hour
    return 9 <= current_hour <= 17  # Only run during business hours

conditions = {
    "target_online": check_target_online,
    "business_hours": check_time_window
}

# Usage
conditional_executor = ConditionalTTPExecutor(
    ttp=my_ttp,
    target_url="http://example.com",
    conditions=conditions
)
conditional_executor.run()
```

### 4. Result Processing and Analysis

```python
class AnalyticsTTPExecutor(TTPExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.analytics = {
            'total_attempts': 0,
            'successful_attempts': 0,
            'error_count': 0,
            'execution_time': 0,
            'payload_stats': {}
        }
    
    def run(self):
        """Run TTP with analytics collection."""
        import time
        start_time = time.time()
        
        # Override the payload execution loop for analytics
        self._setup_driver()
        
        try:
            if self.behavior and self.driver:
                self.behavior.pre_execution(self.driver, self.target_url)
            
            consecutive_failures = 0
            
            for i, payload in enumerate(self.ttp.get_payloads(), 1):
                self.analytics['total_attempts'] += 1
                
                # Track payload characteristics
                self._track_payload(payload)
                
                if self.behavior and not self.behavior.should_continue(i, consecutive_failures):
                    break
                
                try:
                    if self.behavior and self.driver:
                        self.behavior.pre_step(self.driver, payload, i)
                    
                    if self.driver:
                        self.driver.get(self.target_url)
                        self.ttp.execute_step(self.driver, payload)
                    
                    step_delay = self.behavior.get_step_delay(i) if self.behavior else self.delay
                    time.sleep(step_delay)
                    
                    success = self.ttp.verify_result(self.driver) if self.driver else False
                    
                    if success:
                        self.analytics['successful_attempts'] += 1
                        consecutive_failures = 0
                        current_url = self.driver.current_url if self.driver else "unknown"
                        self.results.append({'payload': payload, 'url': current_url})
                    else:
                        consecutive_failures += 1
                    
                    if self.behavior and self.driver:
                        self.behavior.post_step(self.driver, payload, i, success)
                
                except Exception as e:
                    self.analytics['error_count'] += 1
                    consecutive_failures += 1
                    
                    if self.behavior and not self.behavior.on_error(e, i):
                        break
            
            if self.behavior and self.driver:
                self.behavior.post_execution(self.driver, self.results)
        
        finally:
            self.analytics['execution_time'] = time.time() - start_time
            self._cleanup()
            self._print_analytics()
    
    def _track_payload(self, payload):
        """Track payload characteristics for analytics."""
        payload_length = len(str(payload))
        
        if payload_length not in self.analytics['payload_stats']:
            self.analytics['payload_stats'][payload_length] = 0
        self.analytics['payload_stats'][payload_length] += 1
    
    def _print_analytics(self):
        """Print detailed analytics."""
        print("\n" + "="*50)
        print("EXECUTION ANALYTICS")
        print("="*50)
        print(f"Total Attempts: {self.analytics['total_attempts']}")
        print(f"Successful Attempts: {self.analytics['successful_attempts']}")
        print(f"Success Rate: {self.analytics['successful_attempts']/self.analytics['total_attempts']*100:.2f}%")
        print(f"Error Count: {self.analytics['error_count']}")
        print(f"Execution Time: {self.analytics['execution_time']:.2f} seconds")
        print(f"Attempts per Second: {self.analytics['total_attempts']/self.analytics['execution_time']:.2f}")
        
        if self.analytics['payload_stats']:
            print("\nPayload Length Distribution:")
            for length, count in sorted(self.analytics['payload_stats'].items()):
                print(f"  Length {length}: {count} payloads")

# Usage
analytics_executor = AnalyticsTTPExecutor(ttp=my_ttp, target_url="http://example.com")
analytics_executor.run()
```

## Error Handling and Recovery

### Built-in Error Handling

The executor includes robust error handling:

```python
# WebDriver initialization errors
try:
    self.driver = webdriver.Chrome(options=self.chrome_options)
except Exception as e:
    self.logger.error(f"Failed to initialize WebDriver: {e}")
    raise

# Step execution errors
try:
    self.ttp.execute_step(self.driver, payload)
except Exception as step_error:
    self.logger.error(f"Error during step {i}: {step_error}")
    # Continue execution or delegate to behavior
```

### Custom Error Handling

```python
class RobustTTPExecutor(TTPExecutor):
    def __init__(self, *args, max_retries=3, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_retries = max_retries
    
    def _execute_with_retry(self, payload, step_number):
        """Execute step with retry logic."""
        for attempt in range(self.max_retries):
            try:
                if self.driver:
                    self.driver.get(self.target_url)
                    self.ttp.execute_step(self.driver, payload)
                return True
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.error(f"All {self.max_retries} attempts failed for payload: {payload}")
        return False

# Usage
robust_executor = RobustTTPExecutor(
    ttp=my_ttp,
    target_url="http://example.com",
    max_retries=3
)
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Security TTP Testing

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  security-test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        sudo apt-get update
        sudo apt-get install -y chromium-browser
    
    - name: Run TTP Tests
      run: |
        python -m pytest tests/test_ttps.py -v
      env:
        HEADLESS: true
        TARGET_URL: ${{ secrets.TEST_TARGET_URL }}
    
    - name: Upload Results
      uses: actions/upload-artifact@v2
      with:
        name: ttp-results
        path: ttp_test.log
```

### CI/CD Test Script

```python
#!/usr/bin/env python3
"""
CI/CD TTP test runner
"""
import os
import sys
from scythe.core.executor import TTPExecutor
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.payloads.generators import StaticPayloadGenerator
from scythe.behaviors import MachineBehavior

def run_security_tests():
    target_url = os.getenv('TARGET_URL', 'http://localhost:8080')
    headless = os.getenv('HEADLESS', 'true').lower() == 'true'
    
    # Create machine behavior for consistent CI/CD runs
    machine_behavior = MachineBehavior(
        delay=0.5,
        max_retries=3,
        fail_fast=True
    )
    
    # Define test payloads
    test_payloads = StaticPayloadGenerator([
        "admin", "password", "123456", "test"
    ])
    
    # Create TTP
    login_ttp = LoginBruteforceTTP(
        payload_generator=test_payloads,
        username="admin",
        username_selector="#username",
        password_selector="#password",
        submit_selector="#submit"
    )
    
    # Execute TTP
    executor = TTPExecutor(
        ttp=login_ttp,
        target_url=f"{target_url}/login",
        headless=headless,
        behavior=machine_behavior
    )
    
    try:
        executor.run()
        
        # Check results
        if executor.results:
            print("❌ SECURITY ISSUE: Vulnerabilities found!")
            for result in executor.results:
                print(f"  - Vulnerable payload: {result['payload']}")
            sys.exit(1)  # Fail CI/CD
        else:
            print("✅ No vulnerabilities detected")
            sys.exit(0)  # Pass CI/CD
    
    except Exception as e:
        print(f"❌ TEST EXECUTION FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_security_tests()
```

## Performance Optimization

### Resource Management

```python
class OptimizedTTPExecutor(TTPExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_load_strategy = "eager"  # Don't wait for all resources
    
    def _setup_driver(self):
        """Setup driver with performance optimizations."""
        # Add performance options
        self.chrome_options.add_argument("--disable-images")
        self.chrome_options.add_argument("--disable-javascript")
        self.chrome_options.add_argument("--disable-plugins")
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_experimental_option("pageLoadStrategy", self.page_load_strategy)
        
        super()._setup_driver()
```

### Memory Optimization

```python
class MemoryEfficientExecutor(TTPExecutor):
    def __init__(self, *args, batch_size=100, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch_size = batch_size
    
    def run(self):
        """Process payloads in batches to manage memory."""
        self._setup_driver()
        
        try:
            payload_iterator = self.ttp.get_payloads()
            batch = []
            
            for payload in payload_iterator:
                batch.append(payload)
                
                if len(batch) >= self.batch_size:
                    self._process_batch(batch)
                    batch = []  # Clear batch
            
            # Process remaining payloads
            if batch:
                self._process_batch(batch)
        
        finally:
            self._cleanup()
    
    def _process_batch(self, batch):
        """Process a batch of payloads."""
        for payload in batch:
            # Execute payload
            # ... normal execution logic
            pass
```

## Monitoring and Alerting

### Real-time Monitoring

```python
import time
import threading

class MonitoredTTPExecutor(TTPExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = None
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()
    
    def run(self):
        """Run TTP with real-time monitoring."""
        self.start_time = time.time()
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitor_execution)
        self.monitoring_thread.start()
        
        try:
            super().run()
        finally:
            self.stop_monitoring.set()
            if self.monitoring_thread:
                self.monitoring_thread.join()
    
    def _monitor_execution(self):
        """Monitor execution progress in separate thread."""
        while not self.stop_monitoring.wait(10):  # Check every 10 seconds
            elapsed = time.time() - self.start_time
            print(f"Execution running for {elapsed:.1f}s. Results so far: {len(self.results)}")

# Usage
monitored_executor = MonitoredTTPExecutor(ttp=my_ttp, target_url="http://example.com")
monitored_executor.run()
```

## Best Practices

### 1. Resource Management

```python
# Always use try-finally for cleanup
try:
    executor.run()
finally:
    # Ensure cleanup happens
    if hasattr(executor, 'driver') and executor.driver:
        executor.driver.quit()
```

### 2. Error Recovery

```python
# Implement graceful degradation
class GracefulTTPExecutor(TTPExecutor):
    def run(self):
        try:
            super().run()
        except KeyboardInterrupt:
            self.logger.info("Execution interrupted by user")
            self._safe_cleanup()
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            self._safe_cleanup()
            raise
    
    def _safe_cleanup(self):
        """Cleanup that won't throw exceptions."""
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass  # Ignore cleanup errors
```

### 3. Configuration Management

```python
# Use configuration files for complex setups
import json

class ConfigurableTTPExecutor(TTPExecutor):
    @classmethod
    def from_config(cls, config_path: str):
        """Create executor from configuration file."""
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Create TTP from config
        ttp_class = getattr(ttps, config['ttp']['class'])
        ttp = ttp_class(**config['ttp']['params'])
        
        # Create behavior from config
        behavior = None
        if 'behavior' in config:
            behavior_class = getattr(behaviors, config['behavior']['class'])
            behavior = behavior_class(**config['behavior']['params'])
        
        return cls(
            ttp=ttp,
            target_url=config['target_url'],
            behavior=behavior,
            **config.get('executor_params', {})
        )

# Usage with config file
executor = ConfigurableTTPExecutor.from_config('ttp_config.json')
executor.run()
```

## Troubleshooting

### Common Issues

1. **WebDriver Failures**
   - Ensure ChromeDriver is in PATH
   - Check Chrome browser version compatibility
   - Verify system permissions

2. **Memory Issues**
   - Use headless mode for better performance
   - Implement batch processing for large payload sets
   - Monitor memory usage during execution

3. **Network Timeouts**
   - Increase step delays
   - Implement retry logic
   - Check target application responsiveness

### Debug Mode

```python
# Enable verbose logging
import logging
logging.getLogger().setLevel(logging.DEBUG)

# Use visible browser
executor = TTPExecutor(ttp=my_ttp, target_url="http://example.com", headless=False)

# Add custom debug logging
executor.logger.setLevel(logging.DEBUG)
```

### Performance Profiling

```python
import cProfile
import pstats

def profile_execution():
    """Profile TTP execution performance."""
    executor = TTPExecutor(ttp=my_ttp, target_url="http://example.com")
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    executor.run()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

profile_execution()
```

The TTP Executor is the backbone of the Scythe framework, providing robust and flexible execution capabilities. By understanding its features and configuration options, you can effectively orchestrate security testing campaigns that meet your specific requirements.

For more examples and advanced patterns, see the `examples/` directory and the behavior system documentation.


## JourneyExecutor API Mode (REST without a Browser)

Scythe Journeys can now run directly against REST APIs without launching a browser. This is useful for fast smoke checks, backend validations, and environments where a headless browser is unavailable.

Key points
- Opt-in via JourneyExecutor(..., mode="API"). Default remains UI for backward compatibility.
- A requests.Session is created and stored in the journey context under requests_session.
- If your Journey specifies authentication that implements get_auth_headers(), those headers are merged into the session and available under auth_headers in context.
- Use ApiRequestAction in your steps to perform HTTP calls.
- Header extraction leverages a hybrid strategy: first a direct HTTP request (banner grab), then Selenium logs if a driver exists.

Minimal example

```python
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import ApiRequestAction
from scythe.journeys.executor import JourneyExecutor

step = Step(
    name="API Health",
    description="GET /api/health returns 200",
    actions=[ApiRequestAction(method="GET", url="/api/health", expected_status=200)],
)
journey = Journey(name="API Smoke", description="Simple API smoke test", steps=[step])
executor = JourneyExecutor(journey=journey, target_url="http://localhost:8080", mode="API")
results = executor.run()
print(results["overall_success"])  # True if step passed
```

Context keys in API mode
- mode: 'API'
- requests_session: The shared requests.Session for all ApiRequestAction invocations.
- auth_headers: Dict of authentication headers merged into the session.
- last_response_headers: Headers from the most recent ApiRequestAction.
- last_response_url: URL from the most recent ApiRequestAction.

Authentication
- Any Authentication that exposes get_auth_headers() can supply headers for API runs.
- BearerTokenAuth(token="...") is supported out-of-the-box and will add an Authorization header.

Notes
- No Chrome/ChromeDriver required for API mode.
- You can maintain separate Journeys for UI and API scenarios, or keep UI Journeys unchanged.
- When mode='UI', behavior remains unchanged and is fully backward-compatible.
