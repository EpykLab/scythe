"""Wrap primitive — direct Playwright sync API integration with scythe hooks."""

import logging
from abc import abstractmethod
from typing import Any, Dict, Optional, List, TYPE_CHECKING

from selenium.webdriver.remote.webdriver import WebDriver

from ..journeys.base import Action

if TYPE_CHECKING:
    from playwright.sync_api import Browser, BrowserContext, Page, Playwright

logger = logging.getLogger(__name__)


class WrapAssertionError(Exception):
    """Raised when a Wrap assertion fails."""

    pass


class Wrap:
    """Managed Playwright browser context with scythe lifecycle hooks.

    Usage::

        from scythe.playwright import Wrap

        with Wrap(headless=True) as pw:
            pw.page.goto("https://target.com/login")
            pw.page.fill("#username", "admin")
            pw.page.fill("#password", "password123")
            pw.page.click("button[type=submit]")

            pw.expect_url_contains("/dashboard")
            pw.expect_element_visible(".welcome-message")

    The ``page``, ``browser``, and ``browser_context`` properties give direct
    access to Playwright's sync API objects.
    """

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        behavior: Optional[Any] = None,
        **launch_kwargs: Any,
    ):
        """
        Args:
            headless: Run browser in headless mode.
            browser_type: Browser engine — "chromium", "firefox", or "webkit".
            behavior: Optional scythe Behavior instance for lifecycle hooks.
            **launch_kwargs: Additional kwargs passed to browser.launch().
        """
        self.headless = headless
        self.browser_type = browser_type
        self.behavior = behavior
        self.launch_kwargs = launch_kwargs

        self._playwright: Optional["Playwright"] = None
        self._browser: Optional["Browser"] = None
        self._browser_context: Optional["BrowserContext"] = None
        self._page: Optional["Page"] = None
        self._assertions: List[Dict[str, Any]] = []

    def __enter__(self) -> "Wrap":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise ImportError(
                "Playwright is required for Wrap. "
                "Install it with: pip install 'scythe-ttp[playwright]' "
                "and then run: playwright install"
            )

        self._playwright = sync_playwright().start()

        launcher = getattr(self._playwright, self.browser_type)
        self._browser = launcher.launch(
            headless=self.headless, **self.launch_kwargs
        )
        self._browser_context = self._browser.new_context()
        self._page = self._browser_context.new_page()

        logger.info(
            f"Playwright {self.browser_type} browser started "
            f"(headless={self.headless})"
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self._page:
                self._page.close()
            if self._browser_context:
                self._browser_context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.warning(f"Error during Playwright cleanup: {e}")

        logger.info("Playwright browser closed")
        return False

    @property
    def page(self) -> "Page":
        """The active Playwright Page — full sync API access."""
        if self._page is None:
            raise RuntimeError("Wrap must be used as a context manager")
        return self._page

    @property
    def browser(self) -> "Browser":
        """The Playwright Browser instance."""
        if self._browser is None:
            raise RuntimeError("Wrap must be used as a context manager")
        return self._browser

    @property
    def browser_context(self) -> "BrowserContext":
        """The Playwright BrowserContext instance."""
        if self._browser_context is None:
            raise RuntimeError("Wrap must be used as a context manager")
        return self._browser_context

    @property
    def assertions(self) -> List[Dict[str, Any]]:
        """List of assertion results from expect_* calls."""
        return self._assertions

    def expect_url_contains(self, substring: str) -> "Wrap":
        """Assert the current page URL contains the given substring.

        Args:
            substring: Expected substring in the URL.

        Returns:
            self for chaining.

        Raises:
            WrapAssertionError: If the URL does not contain the substring.
        """
        current_url = self.page.url
        passed = substring in current_url
        self._assertions.append(
            {
                "type": "url_contains",
                "expected": substring,
                "actual": current_url,
                "passed": passed,
            }
        )
        if not passed:
            raise WrapAssertionError(
                f"Expected URL to contain '{substring}' but got '{current_url}'"
            )
        return self

    def expect_element_visible(
        self, selector: str, timeout: float = 5000
    ) -> "Wrap":
        """Assert that an element matching the selector is visible.

        Args:
            selector: CSS selector for the element.
            timeout: Max time to wait in milliseconds.

        Returns:
            self for chaining.

        Raises:
            WrapAssertionError: If the element is not visible within timeout.
        """
        try:
            locator = self.page.locator(selector)
            locator.wait_for(state="visible", timeout=timeout)
            passed = True
            error = None
        except Exception as e:
            passed = False
            error = str(e)

        self._assertions.append(
            {
                "type": "element_visible",
                "selector": selector,
                "passed": passed,
                "error": error,
            }
        )
        if not passed:
            raise WrapAssertionError(
                f"Expected element '{selector}' to be visible: {error}"
            )
        return self

    def expect_element_hidden(
        self, selector: str, timeout: float = 5000
    ) -> "Wrap":
        """Assert that an element matching the selector is hidden or absent.

        Args:
            selector: CSS selector for the element.
            timeout: Max time to wait in milliseconds.

        Returns:
            self for chaining.

        Raises:
            WrapAssertionError: If the element is still visible after timeout.
        """
        try:
            locator = self.page.locator(selector)
            locator.wait_for(state="hidden", timeout=timeout)
            passed = True
            error = None
        except Exception as e:
            passed = False
            error = str(e)

        self._assertions.append(
            {
                "type": "element_hidden",
                "selector": selector,
                "passed": passed,
                "error": error,
            }
        )
        if not passed:
            raise WrapAssertionError(
                f"Expected element '{selector}' to be hidden: {error}"
            )
        return self

    def expect_text_content(
        self, selector: str, expected_text: str, timeout: float = 5000
    ) -> "Wrap":
        """Assert that an element's text content matches.

        Args:
            selector: CSS selector for the element.
            expected_text: Expected text content (substring match).
            timeout: Max time to wait for the element in milliseconds.

        Returns:
            self for chaining.

        Raises:
            WrapAssertionError: If the text does not match.
        """
        try:
            locator = self.page.locator(selector)
            locator.wait_for(state="visible", timeout=timeout)
            actual_text = locator.text_content() or ""
            passed = expected_text in actual_text
            error = None
        except Exception as e:
            actual_text = ""
            passed = False
            error = str(e)

        self._assertions.append(
            {
                "type": "text_content",
                "selector": selector,
                "expected": expected_text,
                "actual": actual_text,
                "passed": passed,
                "error": error,
            }
        )
        if not passed:
            msg = (
                f"Expected text '{expected_text}' in '{selector}' "
                f"but got '{actual_text}'"
            )
            if error:
                msg += f": {error}"
            raise WrapAssertionError(msg)
        return self


class PlaywrightWrapAction(Action):
    """Abstract Journey Action for inline Playwright browser interaction.

    Subclass and implement ``run()`` to use Playwright's sync API directly
    within a scythe Journey::

        from scythe.playwright import PlaywrightWrapAction

        class LoginTest(PlaywrightWrapAction):
            def run(self, page, context):
                page.goto(context["target_url"] + "/login")
                page.fill("#username", context.get("username", "admin"))
                page.fill("#password", context.get("password", "test"))
                page.click("button[type=submit]")
                return "/dashboard" in page.url
    """

    def __init__(
        self,
        name: str = "Playwright Wrap Action",
        description: str = "Execute Playwright browser interaction",
        expected_result: bool = True,
        headless: bool = True,
        browser_type: str = "chromium",
        **launch_kwargs: Any,
    ):
        self.headless = headless
        self.browser_type = browser_type
        self.launch_kwargs = launch_kwargs
        super().__init__(name, description, expected_result)

    @abstractmethod
    def run(self, page: "Page", context: Dict[str, Any]) -> bool:
        """Implement your Playwright test logic here.

        Args:
            page: Playwright sync Page object with full API access.
            context: Shared journey context dict.

        Returns:
            True if the test passed, False otherwise.
        """
        ...

    def execute(self, driver: WebDriver, context: Dict[str, Any]) -> bool:
        """Execute the Playwright wrap action within a managed lifecycle.

        Args:
            driver: WebDriver instance (unused, present for Action interface).
            context: Shared journey context.

        Returns:
            True if run() returned True, False otherwise.
        """
        try:
            with Wrap(
                headless=self.headless,
                browser_type=self.browser_type,
                **self.launch_kwargs,
            ) as pw:
                result = self.run(pw.page, context)

                self.store_result("passed", result)
                self.store_result("assertions", pw.assertions)
                self.store_result("final_url", pw.page.url)

                return result

        except WrapAssertionError as e:
            logger.error(f"PlaywrightWrapAction assertion failed: {e}")
            self.store_result("error", str(e))
            self.store_result("passed", False)
            return False

        except ImportError as e:
            logger.error(f"Playwright not installed: {e}")
            self.store_result("error", str(e))
            return False

        except Exception as e:
            logger.error(f"PlaywrightWrapAction failed: {e}")
            self.store_result("error", str(e))
            return False
