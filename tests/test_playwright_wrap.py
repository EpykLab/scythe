import unittest
from unittest.mock import patch, Mock, MagicMock, PropertyMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scythe.playwright.wrap import Wrap, PlaywrightWrapAction, WrapAssertionError


def _mock_playwright():
    """Create a mock playwright sync API stack."""
    mock_page = MagicMock()
    mock_page.url = "https://example.com/dashboard"
    mock_page.close = MagicMock()

    mock_locator = MagicMock()
    mock_locator.wait_for = MagicMock()
    mock_locator.text_content = MagicMock(return_value="Welcome, admin")
    mock_page.locator = MagicMock(return_value=mock_locator)

    mock_context = MagicMock()
    mock_context.new_page = MagicMock(return_value=mock_page)
    mock_context.close = MagicMock()

    mock_browser = MagicMock()
    mock_browser.new_context = MagicMock(return_value=mock_context)
    mock_browser.close = MagicMock()

    mock_chromium = MagicMock()
    mock_chromium.launch = MagicMock(return_value=mock_browser)

    mock_pw = MagicMock()
    mock_pw.chromium = mock_chromium
    mock_pw.firefox = MagicMock()
    mock_pw.webkit = MagicMock()
    mock_pw.stop = MagicMock()

    mock_sync_playwright = MagicMock()
    mock_sync_playwright.start = MagicMock(return_value=mock_pw)

    return mock_sync_playwright, mock_pw, mock_browser, mock_context, mock_page, mock_locator


class TestWrap(unittest.TestCase):
    """Tests for the Wrap context manager."""

    @patch("scythe.playwright.wrap.sync_playwright", create=True)
    def test_context_manager_lifecycle(self, _):
        """Test that Wrap properly manages playwright lifecycle."""
        mock_sync, mock_pw, mock_browser, mock_ctx, mock_page, _ = _mock_playwright()

        with patch(
            "scythe.playwright.wrap.sync_playwright", create=True
        ) as mock_import:
            # We need to patch the import inside the __enter__ method
            pass

        # Test using direct attribute manipulation
        wrap = Wrap(headless=True)
        mock_sync_pw, mock_pw, mock_browser, mock_ctx, mock_page, _ = _mock_playwright()

        # Simulate __enter__
        wrap._playwright = mock_pw
        wrap._browser = mock_browser
        wrap._browser_context = mock_ctx
        wrap._page = mock_page

        self.assertEqual(wrap.page, mock_page)
        self.assertEqual(wrap.browser, mock_browser)
        self.assertEqual(wrap.browser_context, mock_ctx)

        # Simulate __exit__
        wrap.__exit__(None, None, None)
        mock_page.close.assert_called_once()
        mock_ctx.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_pw.stop.assert_called_once()

    def test_page_property_raises_without_context(self):
        wrap = Wrap()
        with self.assertRaises(RuntimeError):
            _ = wrap.page

    def test_browser_property_raises_without_context(self):
        wrap = Wrap()
        with self.assertRaises(RuntimeError):
            _ = wrap.browser

    def test_browser_context_property_raises_without_context(self):
        wrap = Wrap()
        with self.assertRaises(RuntimeError):
            _ = wrap.browser_context

    def test_expect_url_contains_pass(self):
        wrap = Wrap()
        mock_page = MagicMock()
        mock_page.url = "https://example.com/dashboard?tab=home"
        wrap._page = mock_page

        result = wrap.expect_url_contains("/dashboard")
        self.assertIs(result, wrap)
        self.assertEqual(len(wrap.assertions), 1)
        self.assertTrue(wrap.assertions[0]["passed"])

    def test_expect_url_contains_fail(self):
        wrap = Wrap()
        mock_page = MagicMock()
        mock_page.url = "https://example.com/login"
        wrap._page = mock_page

        with self.assertRaises(WrapAssertionError):
            wrap.expect_url_contains("/dashboard")

        self.assertEqual(len(wrap.assertions), 1)
        self.assertFalse(wrap.assertions[0]["passed"])

    def test_expect_element_visible_pass(self):
        wrap = Wrap()
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.wait_for = MagicMock()
        mock_page.locator = MagicMock(return_value=mock_locator)
        wrap._page = mock_page

        result = wrap.expect_element_visible("h1.title")
        self.assertIs(result, wrap)
        self.assertTrue(wrap.assertions[0]["passed"])
        mock_page.locator.assert_called_with("h1.title")
        mock_locator.wait_for.assert_called_with(state="visible", timeout=5000)

    def test_expect_element_visible_fail(self):
        wrap = Wrap()
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.wait_for = MagicMock(side_effect=TimeoutError("timed out"))
        mock_page.locator = MagicMock(return_value=mock_locator)
        wrap._page = mock_page

        with self.assertRaises(WrapAssertionError):
            wrap.expect_element_visible("h1.missing")

        self.assertFalse(wrap.assertions[0]["passed"])

    def test_expect_element_hidden_pass(self):
        wrap = Wrap()
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.wait_for = MagicMock()
        mock_page.locator = MagicMock(return_value=mock_locator)
        wrap._page = mock_page

        result = wrap.expect_element_hidden(".spinner")
        self.assertIs(result, wrap)
        self.assertTrue(wrap.assertions[0]["passed"])
        mock_locator.wait_for.assert_called_with(state="hidden", timeout=5000)

    def test_expect_element_hidden_fail(self):
        wrap = Wrap()
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.wait_for = MagicMock(side_effect=TimeoutError("still visible"))
        mock_page.locator = MagicMock(return_value=mock_locator)
        wrap._page = mock_page

        with self.assertRaises(WrapAssertionError):
            wrap.expect_element_hidden(".spinner")

    def test_expect_text_content_pass(self):
        wrap = Wrap()
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.wait_for = MagicMock()
        mock_locator.text_content = MagicMock(return_value="Welcome, admin")
        mock_page.locator = MagicMock(return_value=mock_locator)
        wrap._page = mock_page

        result = wrap.expect_text_content("h1", "Welcome")
        self.assertIs(result, wrap)
        self.assertTrue(wrap.assertions[0]["passed"])

    def test_expect_text_content_fail(self):
        wrap = Wrap()
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.wait_for = MagicMock()
        mock_locator.text_content = MagicMock(return_value="Access denied")
        mock_page.locator = MagicMock(return_value=mock_locator)
        wrap._page = mock_page

        with self.assertRaises(WrapAssertionError):
            wrap.expect_text_content("h1", "Welcome")

    def test_assertions_chaining(self):
        """Test that expect methods can be chained."""
        wrap = Wrap()
        mock_page = MagicMock()
        mock_page.url = "https://example.com/dashboard"
        mock_locator = MagicMock()
        mock_locator.wait_for = MagicMock()
        mock_locator.text_content = MagicMock(return_value="Welcome")
        mock_page.locator = MagicMock(return_value=mock_locator)
        wrap._page = mock_page

        wrap.expect_url_contains("/dashboard").expect_element_visible(
            "h1"
        ).expect_text_content("h1", "Welcome")

        self.assertEqual(len(wrap.assertions), 3)
        self.assertTrue(all(a["passed"] for a in wrap.assertions))


class TestPlaywrightWrapAction(unittest.TestCase):
    """Tests for PlaywrightWrapAction as a Journey Action."""

    def test_abstract_run_not_callable(self):
        """PlaywrightWrapAction cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            PlaywrightWrapAction()

    def test_subclass_execute(self):
        """Test a concrete subclass works with mocked Playwright."""

        class MyAction(PlaywrightWrapAction):
            def run(self, page, context):
                page.goto(context.get("target_url", "https://example.com"))
                return True

        action = MyAction(name="Test", description="Test action")

        # Mock the Wrap context manager
        mock_page = MagicMock()
        mock_page.url = "https://example.com"

        with patch("scythe.playwright.wrap.Wrap") as MockWrap:
            mock_wrap_instance = MagicMock()
            mock_wrap_instance.page = mock_page
            mock_wrap_instance.assertions = []
            mock_wrap_instance.__enter__ = MagicMock(return_value=mock_wrap_instance)
            mock_wrap_instance.__exit__ = MagicMock(return_value=False)
            MockWrap.return_value = mock_wrap_instance

            result = action.execute(driver=None, context={"target_url": "https://target.com"})

        self.assertTrue(result)
        self.assertTrue(action.execution_data["passed"])
        mock_page.goto.assert_called_with("https://target.com")

    def test_subclass_execute_failure(self):
        """Test that run() returning False is captured."""

        class FailingAction(PlaywrightWrapAction):
            def run(self, page, context):
                return False

        action = FailingAction(name="Fail", description="Fails")

        mock_page = MagicMock()
        mock_page.url = "https://example.com"

        with patch("scythe.playwright.wrap.Wrap") as MockWrap:
            mock_wrap_instance = MagicMock()
            mock_wrap_instance.page = mock_page
            mock_wrap_instance.assertions = []
            mock_wrap_instance.__enter__ = MagicMock(return_value=mock_wrap_instance)
            mock_wrap_instance.__exit__ = MagicMock(return_value=False)
            MockWrap.return_value = mock_wrap_instance

            result = action.execute(driver=None, context={})

        self.assertFalse(result)
        self.assertFalse(action.execution_data["passed"])

    def test_subclass_exception_handling(self):
        """Test that exceptions in run() are caught and reported."""

        class CrashingAction(PlaywrightWrapAction):
            def run(self, page, context):
                raise RuntimeError("browser crashed")

        action = CrashingAction(name="Crash", description="Crashes")

        mock_page = MagicMock()
        mock_page.url = "https://example.com"

        with patch("scythe.playwright.wrap.Wrap") as MockWrap:
            mock_wrap_instance = MagicMock()
            mock_wrap_instance.page = mock_page
            mock_wrap_instance.assertions = []
            mock_wrap_instance.__enter__ = MagicMock(return_value=mock_wrap_instance)
            mock_wrap_instance.__exit__ = MagicMock(return_value=False)
            MockWrap.return_value = mock_wrap_instance

            result = action.execute(driver=None, context={})

        self.assertFalse(result)
        self.assertIn("browser crashed", action.execution_data["error"])

    def test_action_in_step(self):
        """Test PlaywrightWrapAction works within a Journey Step."""

        class SimpleAction(PlaywrightWrapAction):
            def run(self, page, context):
                return True

        action = SimpleAction(name="Simple", description="Simple test")

        mock_page = MagicMock()
        mock_page.url = "https://example.com"

        with patch("scythe.playwright.wrap.Wrap") as MockWrap:
            mock_wrap_instance = MagicMock()
            mock_wrap_instance.page = mock_page
            mock_wrap_instance.assertions = []
            mock_wrap_instance.__enter__ = MagicMock(return_value=mock_wrap_instance)
            mock_wrap_instance.__exit__ = MagicMock(return_value=False)
            MockWrap.return_value = mock_wrap_instance

            from scythe.journeys.base import Step

            step = Step(
                name="Playwright step",
                description="Run playwright action",
                actions=[action],
            )
            result = step.execute(driver=None, context={})

        self.assertTrue(result)
        self.assertEqual(len(step.execution_results), 1)
        self.assertTrue(step.execution_results[0]["actual"])


if __name__ == "__main__":
    unittest.main()
