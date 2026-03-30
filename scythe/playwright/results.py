"""Result parsing for pytest-json-report output."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class PlaywrightTestResult:
    """Result of a single Playwright test case."""

    name: str
    outcome: str  # "passed", "failed", "skipped", "error"
    duration_s: float = 0.0
    error: Optional[str] = None


@dataclass
class PlaywrightResult:
    """Aggregated result of a Playwright test run."""

    passed: bool
    total: int = 0
    passed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    duration_s: float = 0.0
    tests: List[PlaywrightTestResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    raw_output: str = ""

    def summary(self) -> Dict[str, Any]:
        """Return a summary dict suitable for scythe execution_data."""
        return {
            "passed": self.passed,
            "total": self.total,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "duration_s": self.duration_s,
            "errors": self.errors,
            "tests": [
                {
                    "name": t.name,
                    "outcome": t.outcome,
                    "duration_s": t.duration_s,
                    "error": t.error,
                }
                for t in self.tests
            ],
        }


def parse_json_report(raw: str) -> PlaywrightResult:
    """Parse pytest-json-report JSON output into a PlaywrightResult.

    Args:
        raw: Raw JSON string from pytest-json-report (--json-report-file=-)

    Returns:
        Parsed PlaywrightResult
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse pytest-json-report output: {e}")
        return PlaywrightResult(
            passed=False,
            errors=[f"Failed to parse test output: {e}"],
            raw_output=raw or "",
        )

    summary = data.get("summary", {})
    tests_data = data.get("tests", [])

    tests = []
    errors = []

    for t in tests_data:
        nodeid = t.get("nodeid", "unknown")
        outcome = t.get("outcome", "unknown")
        duration = t.get("duration", 0.0)

        error_msg = None
        if outcome in ("failed", "error"):
            # Extract failure message from call or setup phase
            for phase in ("call", "setup", "teardown"):
                phase_data = t.get(phase, {})
                if phase_data.get("outcome") in ("failed", "error"):
                    longrepr = phase_data.get("longrepr", "")
                    error_msg = longrepr if isinstance(longrepr, str) else str(longrepr)
                    errors.append(f"{nodeid}: {error_msg}")
                    break

        tests.append(
            PlaywrightTestResult(
                name=nodeid,
                outcome=outcome,
                duration_s=duration,
                error=error_msg,
            )
        )

    passed_count = summary.get("passed", 0)
    failed_count = summary.get("failed", 0)
    skipped_count = summary.get("skipped", 0)
    error_count = summary.get("error", 0)
    total = summary.get("total", len(tests))
    duration_s = data.get("duration", 0.0)

    all_passed = failed_count == 0 and error_count == 0

    return PlaywrightResult(
        passed=all_passed,
        total=total,
        passed_count=passed_count,
        failed_count=failed_count + error_count,
        skipped_count=skipped_count,
        duration_s=duration_s,
        tests=tests,
        errors=errors,
        raw_output=raw,
    )
