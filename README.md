<h1 align="center">Scythe</h1>


<h2 align="center">
  <img src="./assets/scythe.png" alt="scythe" width="200px">
  <br>
</h2>

<h4 align="center">An extensible framework for emulating attacker TTPs with Selenium.</h4>


## Overview

Scythe is a Python-based framework that allows you to test the security of your
web applications by emulating Tactics, Techniques, and Procedures (TTPs) of
attackers. It uses Selenium to automate browser interactions and simulate
attacks like SQL injection, cross-site scripting (XSS), and brute-forcing. This
allows you to validate that your web application protects against these attacks
and helps you test your detection capabilities.

## Features

  * **Extensible TTP Framework**: Easily create new TTPs by extending the abstract base class.
  * **Behavior System**: Control TTP execution patterns with built-in behaviors (Human, Machine, Stealth) or create custom behaviors.
  * **Payload Generators**: Generate payloads from wordlists or static lists.
  * **Selenium-based**: Utilizes the power of Selenium for realistic browser automation.
  * **Configurable**: Easily configure TTPs with different selectors and payloads.
  * **Logging**: Detailed logging for each TTP execution.

## Getting Started

### Prerequisites

  * Python 3.8+
  * Google Chrome

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/EpykLab/scythe.git
    cd scythe
    ```
2.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Usage

1.  **Configure a TTP**: In your test script, import the desired TTP and create
    an instance with the necessary parameters. For example, to use the `LoginBruteforceTTP`:

    ```python
    from scythe.core.executor import TTPExecutor
    from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
    from scythe.payloads.generators import WordlistPayloadGenerator
    from scythe.behaviors import HumanBehavior

    # Create a payload generator
    payload_generator = WordlistPayloadGenerator("path/to/your/password_list.txt")

    # Create a TTP instance
    login_bruteforce_ttp = LoginBruteforceTTP(
        payload_generator=payload_generator,
        username="testuser",
        username_selector="#username",
        password_selector="#password",
        submit_selector="#submit"
    )

    # Create a behavior (optional)
    human_behavior = HumanBehavior(
        base_delay=2.0,
        delay_variance=1.0,
        mouse_movement=True
    )

    # Create a TTP executor
    executor = TTPExecutor(
        ttp=login_bruteforce_ttp,
        target_url="http://localhost:5000/login",
        behavior=human_behavior  # Optional parameter
    )

    # Run the TTP
    executor.run()
    ```

2.  **Run the Test**: Execute the Python script to run the TTP.

    ```bash
    python your_test_script.py
    ```

3.  **View the Results**: The results of the TTP execution will be logged to
    the console and to a file named `ttp_test.log`.

## Behaviors

Scythe includes a powerful behavior system that allows you to control how TTPs are executed to make them more realistic and harder to detect. Behaviors control timing, interaction patterns, error handling, and anti-detection techniques.

### Available Behaviors

* **HumanBehavior**: Emulates human-like interaction patterns with variable timing and mouse movements
* **MachineBehavior**: Provides consistent, predictable timing for automated testing
* **StealthBehavior**: Uses randomized timing and anti-detection techniques for evasion
* **DefaultBehavior**: Maintains original TTPExecutor functionality for backward compatibility

### Human Behavior Example

```python
from scythe.behaviors import HumanBehavior

# Create human-like behavior
human_behavior = HumanBehavior(
    base_delay=3.0,              # Slower, more human-like timing
    delay_variance=1.5,          # High variance for realism
    typing_delay=0.1,            # Human-like typing speed
    mouse_movement=True,         # Enable mouse movements
    max_consecutive_failures=3   # Give up after 3 failures like a human
)

executor = TTPExecutor(
    ttp=your_ttp,
    target_url="http://target.com",
    behavior=human_behavior
)
```

### Machine Behavior Example

```python
from scythe.behaviors import MachineBehavior

# Create machine-like behavior for fast, automated testing
machine_behavior = MachineBehavior(
    delay=0.5,           # Fast, consistent timing
    max_retries=5,       # Systematic retry logic
    fail_fast=True       # Stop immediately on critical errors
)

executor = TTPExecutor(
    ttp=your_ttp,
    target_url="http://target.com", 
    behavior=machine_behavior
)
```

### Stealth Behavior Example

```python
from scythe.behaviors import StealthBehavior

# Create stealth behavior for evasion
stealth_behavior = StealthBehavior(
    min_delay=5.0,                    # Longer delays to avoid detection
    max_delay=15.0,                   # High variance in timing
    burst_probability=0.05,           # Occasional burst activity
    long_pause_probability=0.2,       # Random long pauses
    max_requests_per_session=10,      # Limit requests per session
    session_cooldown=120.0            # Cooldown between sessions
)

executor = TTPExecutor(
    ttp=your_ttp,
    target_url="http://target.com",
    behavior=stealth_behavior
)
```

### Creating Custom Behaviors

```python
from scythe.behaviors.base import Behavior

class CustomBehavior(Behavior):
    def __init__(self):
        super().__init__(
            name="Custom Behavior",
            description="My custom behavior implementation"
        )
    
    def get_step_delay(self, step_number: int) -> float:
        # Custom delay logic
        return 2.0 if step_number % 2 == 0 else 1.0
    
    def should_continue(self, step_number: int, consecutive_failures: int) -> bool:
        # Custom continuation logic
        return consecutive_failures < 5
    
    def pre_step(self, driver, payload, step_number):
        print(f"About to execute step {step_number}")
    
    # Implement other methods as needed...

# Use your custom behavior
custom_behavior = CustomBehavior()
executor = TTPExecutor(ttp=your_ttp, target_url="http://target.com", behavior=custom_behavior)
```

### Backward Compatibility

The behavior system is completely optional. Existing code continues to work unchanged:

```python
# This still works exactly as before - no behavior needed
executor = TTPExecutor(ttp=your_ttp, target_url="http://target.com")
executor.run()
```

For detailed information about behaviors, examples, and advanced usage, see `docs/BEHAVIORS.md` and `examples/behavior_demo.py`.

## Contributing

Contributions are welcome\! Please see the `DEVELOPER_GUIDE.md` for more
information on how to contribute to the project.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more
details.

# DEVELOPER GUIDE

This guide provides instructions for developers who want to contribute to the
Scythe framework by creating new TTPs.

## Core Concepts

The Scythe framework is built around a few core concepts:

  * **TTP (Tactic, Technique, and Procedure)**: A TTP is a single test that
  emulates a specific attacker behavior. Each TTP is a Python class that
  inherits from the `TTP` abstract base class.
  * **Payload Generator**: A payload generator is a class that generates
  payloads for a TTP. The framework provides two types of payload generators:
  `WordlistPayloadGenerator` and `StaticPayloadGenerator`.
  * **TTP Executor**: The `TTPExecutor` is the main engine for running TTP
  tests. It takes a TTP instance and a target URL as input and executes the TTP
  against the target.

## Creating a New TTP

To create a new TTP, you need to create a new Python class that inherits from
the `TTP` abstract base class and implements the following methods:

  * `get_payloads(self)`: This method should yield payloads for the test execution.
  * `execute_step(self, driver: WebDriver, payload: Any)`: This method executes
  a single test action using the provided payload. This method should perform
  the action (e.g., fill form, click button).
  * `verify_result(self, driver: WebDriver) -> bool`: This method verifies the
  outcome of the executed step. It should return `True` if the test indicates a
  potential success/vulnerability, and `False` otherwise.

### Example TTP: SQL Injection

Here is an example of a simple SQL injection TTP:

```python
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from scythe.core.ttp import TTP
from scythe.payloads.generators import StaticPayloadGenerator

class SQLInjectionTTP(TTP):
    def __init__(self, target_url: str):
        super().__init__(
            name="SQL Injection",
            description="Tests for basic SQL injection vulnerabilities."
        )
        self.target_url = target_url
        self.payload_generator = StaticPayloadGenerator([
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR 1=1 --",
        ])

    def get_payloads(self):
        yield from self.payload_generator()

    def execute_step(self, driver: WebDriver, payload: str):
        # Assumes a search input with the name 'q'
        driver.get(f"{self.target_url}?q={payload}")

    def verify_result(self, driver: WebDriver) -> bool:
        # A simple check for a generic SQL error message
        return "sql" in driver.page_source.lower() or \
               "syntax" in driver.page_source.lower()

```

## Coding Conventions

Please follow these coding conventions when contributing to the Scythe framework:

  * All code should be formatted using the Black code formatter.
  * Type hints should be used for all function signatures.
  * Docstrings should be included for all modules, classes, and functions.
  * Follow the PEP 8 style guide for Python code.

By following these guidelines, you can help ensure that the Scythe framework
remains a high-quality and maintainable project.
