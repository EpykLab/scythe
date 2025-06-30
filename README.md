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

    # Create a TTP executor
    executor = TTPExecutor(
        ttp=login_bruteforce_ttp,
        target_url="http://localhost:5000/login"
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
