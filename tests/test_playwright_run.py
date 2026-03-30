import unittest
from unittest.mock import patch, Mock, MagicMock
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scythe.playwright.results import (
    PlaywrightResult,
    PlaywrightTestResult,
    parse_json_report,
)
from scythe.playwright.run import Run, PlaywrightRunAction, PlaywrightExpectationError


def _make_json_report(
    passed=1, failed=0, skipped=0, duration=1.5, tests=None
):
    """Build a fake pytest-json-report JSON string."""
    if tests is None:
        tests = []
        for i in range(passed):
            tests.append(
                {
                    "nodeid": f"test_file.py::test_pass_{i}",
                    "outcome": "passed",
                    "duration": 0.5,
                }
            )
        for i in range(failed):
            tests.append(
                {
                    "nodeid": f"test_file.py::test_fail_{i}",
                    "outcome": "failed",
                    "duration": 0.3,
                    "call": {
                        "outcome": "failed",
                        "longrepr": f"AssertionError: test_fail_{i} failed",
                    },
                }
            )
        for i in range(skipped):
            tests.append(
                {
                    "nodeid": f"test_file.py::test_skip_{i}",
                    "outcome": "skipped",
                    "duration": 0.0,
                }
            )
    return json.dumps(
        {
            "summary": {
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "total": passed + failed + skipped,
            },
            "duration": duration,
            "tests": tests,
        }
    )


class TestParseJsonReport(unittest.TestCase):
    """Tests for parse_json_report."""

    def test_all_passed(self):
        raw = _make_json_report(passed=3, failed=0)
        result = parse_json_report(raw)
        self.assertTrue(result.passed)
        self.assertEqual(result.total, 3)
        self.assertEqual(result.passed_count, 3)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(len(result.tests), 3)

    def test_some_failed(self):
        raw = _make_json_report(passed=2, failed=1)
        result = parse_json_report(raw)
        self.assertFalse(result.passed)
        self.assertEqual(result.total, 3)
        self.assertEqual(result.passed_count, 2)
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(len(result.errors), 1)

    def test_with_skipped(self):
        raw = _make_json_report(passed=1, failed=0, skipped=2)
        result = parse_json_report(raw)
        self.assertTrue(result.passed)
        self.assertEqual(result.skipped_count, 2)

    def test_invalid_json(self):
        result = parse_json_report("not json at all")
        self.assertFalse(result.passed)
        self.assertTrue(len(result.errors) > 0)

    def test_empty_string(self):
        result = parse_json_report("")
        self.assertFalse(result.passed)

    def test_duration_parsed(self):
        raw = _make_json_report(passed=1, duration=3.14)
        result = parse_json_report(raw)
        self.assertAlmostEqual(result.duration_s, 3.14)

    def test_summary_dict(self):
        raw = _make_json_report(passed=2, failed=1)
        result = parse_json_report(raw)
        summary = result.summary()
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["total"], 3)
        self.assertEqual(len(summary["tests"]), 3)


class TestRun(unittest.TestCase):
    """Tests for the Run class."""

    @patch("scythe.playwright.run.subprocess.run")
    def test_execute_success(self, mock_subprocess):
        mock_subprocess.return_value = Mock(
            stdout=_make_json_report(passed=2, failed=0),
            stderr="",
            returncode=0,
        )
        runner = Run("tests/test_example.py")
        result = runner.execute()
        self.assertTrue(result.passed)
        self.assertEqual(result.passed_count, 2)

    @patch("scythe.playwright.run.subprocess.run")
    def test_execute_failure(self, mock_subprocess):
        mock_subprocess.return_value = Mock(
            stdout=_make_json_report(passed=1, failed=1),
            stderr="",
            returncode=1,
        )
        runner = Run("tests/test_example.py")
        result = runner.execute()
        self.assertFalse(result.passed)
        self.assertEqual(result.failed_count, 1)

    @patch("scythe.playwright.run.subprocess.run")
    def test_execute_timeout(self, mock_subprocess):
        import subprocess

        mock_subprocess.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=10)
        runner = Run("tests/test_example.py", timeout=10)
        result = runner.execute()
        self.assertFalse(result.passed)
        self.assertIn("timed out", result.errors[0])

    @patch("scythe.playwright.run.subprocess.run")
    def test_expect_passed_true(self, mock_subprocess):
        mock_subprocess.return_value = Mock(
            stdout=_make_json_report(passed=3, failed=0),
            stderr="",
            returncode=0,
        )
        # Should not raise
        Run("tests/test_example.py").expect(passed=True)

    @patch("scythe.playwright.run.subprocess.run")
    def test_expect_passed_false(self, mock_subprocess):
        mock_subprocess.return_value = Mock(
            stdout=_make_json_report(passed=3, failed=0),
            stderr="",
            returncode=0,
        )
        # All passed but expected failure — should raise
        with self.assertRaises(PlaywrightExpectationError):
            Run("tests/test_example.py").expect(passed=False)

    @patch("scythe.playwright.run.subprocess.run")
    def test_expect_min_passed(self, mock_subprocess):
        mock_subprocess.return_value = Mock(
            stdout=_make_json_report(passed=1, failed=2),
            stderr="",
            returncode=1,
        )
        with self.assertRaises(PlaywrightExpectationError):
            Run("tests/test_example.py").expect(min_passed=2)

    @patch("scythe.playwright.run.subprocess.run")
    def test_expect_max_failed(self, mock_subprocess):
        mock_subprocess.return_value = Mock(
            stdout=_make_json_report(passed=1, failed=3),
            stderr="",
            returncode=1,
        )
        with self.assertRaises(PlaywrightExpectationError):
            Run("tests/test_example.py").expect(max_failed=1)

    @patch("scythe.playwright.run.subprocess.run")
    def test_expect_chaining(self, mock_subprocess):
        mock_subprocess.return_value = Mock(
            stdout=_make_json_report(passed=5, failed=0),
            stderr="",
            returncode=0,
        )
        result = Run("tests/test_example.py").expect(passed=True).expect(min_passed=3)
        self.assertIsInstance(result, Run)

    def test_build_command_basic(self):
        runner = Run("tests/test_login.py")
        cmd = runner._build_command()
        self.assertIn("tests/test_login.py", cmd)
        self.assertIn("--json-report", cmd)
        self.assertIn("--browser=chromium", cmd)
        self.assertNotIn("--headed", cmd)

    def test_build_command_options(self):
        runner = Run(
            "tests/test_login.py",
            headed=True,
            browser="firefox",
            marker="slow",
            keyword="login",
        )
        cmd = runner._build_command()
        self.assertIn("--headed", cmd)
        self.assertIn("--browser=firefox", cmd)
        self.assertIn("-m", cmd)
        self.assertIn("slow", cmd)
        self.assertIn("-k", cmd)
        self.assertIn("login", cmd)

    @patch("scythe.playwright.run.subprocess.run")
    def test_result_property(self, mock_subprocess):
        mock_subprocess.return_value = Mock(
            stdout=_make_json_report(passed=1),
            stderr="",
            returncode=0,
        )
        runner = Run("tests/test_example.py")
        self.assertIsNone(runner.result)
        runner.execute()
        self.assertIsNotNone(runner.result)


class TestPlaywrightRunAction(unittest.TestCase):
    """Tests for PlaywrightRunAction as a Journey Action."""

    @patch("scythe.playwright.run.subprocess.run")
    def test_execute_action_passed(self, mock_subprocess):
        mock_subprocess.return_value = Mock(
            stdout=_make_json_report(passed=2, failed=0),
            stderr="",
            returncode=0,
        )
        action = PlaywrightRunAction(
            test_file="tests/test_login.py",
            expected_result=True,
        )
        result = action.execute(driver=None, context={})
        self.assertTrue(result)
        self.assertTrue(action.execution_data["passed"])
        self.assertEqual(action.execution_data["passed_count"], 2)

    @patch("scythe.playwright.run.subprocess.run")
    def test_execute_action_failed(self, mock_subprocess):
        mock_subprocess.return_value = Mock(
            stdout=_make_json_report(passed=0, failed=2),
            stderr="",
            returncode=1,
        )
        action = PlaywrightRunAction(
            test_file="tests/test_login.py",
            expected_result=False,
        )
        result = action.execute(driver=None, context={})
        self.assertFalse(result)

    @patch("scythe.playwright.run.subprocess.run")
    def test_template_substitution(self, mock_subprocess):
        mock_subprocess.return_value = Mock(
            stdout=_make_json_report(passed=1),
            stderr="",
            returncode=0,
        )
        action = PlaywrightRunAction(
            test_file="tests/{test_dir}/test_login.py",
            expected_result=True,
        )
        action.execute(driver=None, context={"test_dir": "auth"})
        # Verify the resolved path was used
        call_args = mock_subprocess.call_args
        cmd = call_args[0][0]
        self.assertIn("tests/auth/test_login.py", cmd)

    @patch("scythe.playwright.run.subprocess.run")
    def test_env_template_substitution(self, mock_subprocess):
        mock_subprocess.return_value = Mock(
            stdout=_make_json_report(passed=1),
            stderr="",
            returncode=0,
        )
        action = PlaywrightRunAction(
            test_file="tests/test_login.py",
            expected_result=True,
            env={"BASE_URL": "{target_url}"},
        )
        action.execute(
            driver=None,
            context={"target_url": "http://localhost:8080"},
        )
        call_args = mock_subprocess.call_args
        env = call_args[1].get("env", {})
        self.assertEqual(env.get("BASE_URL"), "http://localhost:8080")

    @patch("scythe.playwright.run.subprocess.run")
    def test_action_in_step(self, mock_subprocess):
        """Test PlaywrightRunAction works within a Journey Step."""
        mock_subprocess.return_value = Mock(
            stdout=_make_json_report(passed=1),
            stderr="",
            returncode=0,
        )
        from scythe.journeys.base import Step

        action = PlaywrightRunAction(
            test_file="tests/test_login.py",
            expected_result=True,
        )
        step = Step(
            name="Run Playwright tests",
            description="Execute login tests",
            actions=[action],
        )
        result = step.execute(driver=None, context={})
        self.assertTrue(result)
        self.assertEqual(len(step.execution_results), 1)
        self.assertTrue(step.execution_results[0]["actual"])


if __name__ == "__main__":
    unittest.main()
