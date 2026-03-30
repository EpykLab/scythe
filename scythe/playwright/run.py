"""Run primitive — execute Python Playwright tests via pytest subprocess."""

import os
import subprocess
import sys
import logging
from typing import Any, Dict, List, Optional

from selenium.webdriver.remote.webdriver import WebDriver

from ..journeys.base import Action
from .results import PlaywrightResult, parse_json_report

logger = logging.getLogger(__name__)


class PlaywrightExpectationError(Exception):
    """Raised when a Run().expect() assertion fails."""

    pass


class Run:
    """Execute a Python Playwright test file via pytest and inspect results.

    Usage::

        from scythe.playwright import Run

        # Run and assert
        Run("tests/test_login.py").expect(passed=True)

        # Run with options
        Run("tests/test_login.py", browser="firefox", headed=True).expect(passed=True)

        # Run and inspect results
        result = Run("tests/test_login.py").execute()
        print(result.passed_count, result.failed_count)
    """

    def __init__(
        self,
        test_file: str,
        *,
        marker: Optional[str] = None,
        keyword: Optional[str] = None,
        timeout: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
        headed: bool = False,
        browser: str = "chromium",
        extra_args: Optional[List[str]] = None,
    ):
        """
        Args:
            test_file: Path to the pytest-playwright test file.
            marker: pytest -m marker expression to filter tests.
            keyword: pytest -k keyword expression to filter tests.
            timeout: Timeout in seconds for the subprocess.
            env: Extra environment variables for the subprocess.
            headed: Run browser in headed mode (--headed).
            browser: Browser to use (chromium, firefox, webkit).
            extra_args: Additional pytest CLI arguments.
        """
        self.test_file = test_file
        self.marker = marker
        self.keyword = keyword
        self.timeout = timeout
        self.env = env or {}
        self.headed = headed
        self.browser = browser
        self.extra_args = extra_args or []
        self._result: Optional[PlaywrightResult] = None

    def _build_command(self) -> List[str]:
        """Build the pytest command line."""
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            self.test_file,
            "--tb=short",
            "-q",
            "--json-report",
            "--json-report-file=-",
            f"--browser={self.browser}",
        ]

        if self.headed:
            cmd.append("--headed")

        if self.marker:
            cmd.extend(["-m", self.marker])

        if self.keyword:
            cmd.extend(["-k", self.keyword])

        cmd.extend(self.extra_args)

        return cmd

    def execute(self) -> PlaywrightResult:
        """Run the pytest subprocess and parse results.

        Returns:
            PlaywrightResult with parsed test outcomes.
        """
        cmd = self._build_command()
        run_env = {**os.environ, **self.env}

        logger.info(f"Running Playwright tests: {' '.join(cmd)}")

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=run_env,
            )
        except subprocess.TimeoutExpired:
            logger.error(f"Playwright test timed out after {self.timeout}s")
            self._result = PlaywrightResult(
                passed=False,
                errors=[f"Test execution timed out after {self.timeout}s"],
            )
            return self._result
        except FileNotFoundError as e:
            logger.error(f"Failed to run pytest: {e}")
            self._result = PlaywrightResult(
                passed=False,
                errors=[f"Failed to run pytest: {e}"],
            )
            return self._result

        # pytest-json-report writes JSON to stdout when using --json-report-file=-
        # The actual test output goes to stderr in this mode
        raw_output = proc.stdout
        self._result = parse_json_report(raw_output)
        self._result.raw_output = f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"

        logger.info(
            f"Playwright tests completed: {self._result.passed_count} passed, "
            f"{self._result.failed_count} failed, {self._result.skipped_count} skipped"
        )

        return self._result

    def expect(
        self,
        passed: Optional[bool] = None,
        min_passed: Optional[int] = None,
        max_failed: Optional[int] = None,
    ) -> "Run":
        """Assert expectations on the test result. Executes if not already run.

        Args:
            passed: Expect all tests to pass (True) or at least one failure (False).
            min_passed: Minimum number of tests that must pass.
            max_failed: Maximum number of tests allowed to fail.

        Returns:
            self for chaining.

        Raises:
            PlaywrightExpectationError: If any expectation is not met.
        """
        if self._result is None:
            self.execute()

        result = self._result
        failures = []

        if passed is not None:
            if passed and not result.passed:
                failures.append(
                    f"Expected all tests to pass but {result.failed_count} failed: "
                    + "; ".join(result.errors[:3])
                )
            elif not passed and result.passed:
                failures.append(
                    "Expected test failures but all tests passed"
                )

        if min_passed is not None and result.passed_count < min_passed:
            failures.append(
                f"Expected at least {min_passed} tests to pass "
                f"but only {result.passed_count} passed"
            )

        if max_failed is not None and result.failed_count > max_failed:
            failures.append(
                f"Expected at most {max_failed} failures "
                f"but {result.failed_count} failed"
            )

        if failures:
            raise PlaywrightExpectationError("; ".join(failures))

        return self

    @property
    def result(self) -> Optional[PlaywrightResult]:
        """Access the result after execute() or expect()."""
        return self._result


class PlaywrightRunAction(Action):
    """Journey Action that runs a Python Playwright test file via pytest.

    Usage in a Journey::

        from scythe.playwright import PlaywrightRunAction

        Step(
            name="Run login tests",
            actions=[
                PlaywrightRunAction(
                    test_file="tests/test_login.py",
                    expected_result=True,
                    browser="chromium",
                )
            ]
        )

    Supports ``{context_key}`` template substitution in ``test_file``
    and ``env`` values from the journey context.
    """

    def __init__(
        self,
        test_file: str,
        expected_result: bool = True,
        name: Optional[str] = None,
        description: Optional[str] = None,
        **run_kwargs: Any,
    ):
        """
        Args:
            test_file: Path to the pytest-playwright test file.
                Supports {context_key} template substitution.
            expected_result: True if tests are expected to pass, False otherwise.
            name: Optional action name override.
            description: Optional action description override.
            **run_kwargs: Additional keyword arguments passed to Run().
        """
        self.test_file = test_file
        self.run_kwargs = run_kwargs

        name = name or f"Playwright Run: {test_file}"
        description = description or f"Run Playwright test file: {test_file}"
        super().__init__(name, description, expected_result)

    def _resolve_templates(self, context: Dict[str, Any]) -> tuple:
        """Resolve {context_key} templates in test_file and env."""
        test_file = self.test_file
        for key, value in context.items():
            if isinstance(value, str):
                test_file = test_file.replace(f"{{{key}}}", value)

        env = dict(self.run_kwargs.get("env", {}) or {})
        for env_key, env_val in env.items():
            if isinstance(env_val, str):
                for ctx_key, ctx_val in context.items():
                    if isinstance(ctx_val, str):
                        env[env_key] = env[env_key].replace(
                            f"{{{ctx_key}}}", ctx_val
                        )

        return test_file, env

    def execute(self, driver: WebDriver, context: Dict[str, Any]) -> bool:
        """Execute the Playwright test run.

        Args:
            driver: WebDriver instance (unused, present for Action interface).
            context: Shared journey context.

        Returns:
            True if test outcome matches expected_result.
        """
        try:
            test_file, env = self._resolve_templates(context)

            kwargs = dict(self.run_kwargs)
            kwargs["env"] = env

            runner = Run(test_file, **kwargs)
            result = runner.execute()

            self.store_result("playwright_result", result.summary())
            self.store_result("passed", result.passed)
            self.store_result("total", result.total)
            self.store_result("passed_count", result.passed_count)
            self.store_result("failed_count", result.failed_count)
            self.store_result("duration_s", result.duration_s)

            if result.errors:
                self.store_result("errors", result.errors)

            return result.passed

        except Exception as e:
            logger.error(f"PlaywrightRunAction failed: {e}")
            self.store_result("error", str(e))
            return False
