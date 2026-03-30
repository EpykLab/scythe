"""
Playwright module for Scythe framework.

Provides two primitives for integrating Playwright tests into scythe:

- **Run** / **PlaywrightRunAction**: Execute existing pytest-playwright test
  files as subprocesses and assert on results.
- **Wrap** / **PlaywrightWrapAction**: Use Playwright's sync Page API directly
  within scythe's execution model (behaviors, context, result tracking).
"""

from .run import Run, PlaywrightRunAction, PlaywrightExpectationError
from .wrap import Wrap, PlaywrightWrapAction, WrapAssertionError
from .results import PlaywrightResult, PlaywrightTestResult

__all__ = [
    "Run",
    "PlaywrightRunAction",
    "PlaywrightExpectationError",
    "Wrap",
    "PlaywrightWrapAction",
    "WrapAssertionError",
    "PlaywrightResult",
    "PlaywrightTestResult",
]
