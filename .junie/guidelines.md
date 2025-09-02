Scythe – Project-Specific Development Guidelines

Audience: advanced contributors working on Scythe’s core (TTPs, Journeys, Orchestrators, Behaviors, Auth, Headers).

1. Build and Configuration
- Supported Python: 3.8+ (setup.py declares python_requires>=3.8). The test suite has been exercised with Python 3.13 in a venv.
- Dependencies: pinned in requirements.txt; install with:
  - python -m venv venv
  - source venv/bin/activate  # adapt for your shell
  - pip install -r requirements.txt
- Local install (editable) for IDE navigation:
  - pip install -e .
- Browser/WebDriver: Runtime features use Selenium (selenium==4.34.0). The unit tests are driver-mocked; a browser is not required to run the suite. For manual runs that rely on Chrome DevTools logs, ensure Chrome is installed and use selenium’s ChromeOptions as described in scythe.core.headers.HeaderExtractor.enable_logging_for_driver.
- Packaging: setup.py reads README.md and requirements.txt; packages are discovered with find_packages(exclude=["tests*", "examples*"]). Version bump is synchronized by Taskfile.yml release task (uses VERSION file and rewrites setup.py version string).

2. Testing
2.1 Test Runner
- Framework: unittest (standard library). No pytest dependency is required.
- Run full suite from repo root:
  - python -m unittest -q
- Run a specific test file:
  - python -m unittest -q tests/test_header_extraction.py
- Run a specific test case or method:
  - python -m unittest -q tests.test_header_extraction.TestHeaderExtractor.test_get_version_summary_with_versions

2.2 Test Layout and Conventions
- Tests live under tests/ and rely on sys.path injection to import the in-repo scythe package.
- Use unittest.TestCase with method names starting with test_.
- Prefer mocking for WebDriver, network I/O, and time.sleep to keep tests deterministic and fast.
- When validating logs/headers, prefer unit-level helpers on HeaderExtractor rather than full browser flows.
- Long-running orchestration behavior is already covered; keep additional integration tests short and deterministic (e.g., set small delays, deterministic payloads).

2.3 Adding a New Test (example verified)
- Example file that was created and executed during this session:
  - Path: tests/test_demo_header_extractor_example.py
  - Purpose: show how to validate version header parsing without a browser.
  - Content gist:
    - from scythe.core.headers import HeaderExtractor
    - extractor = HeaderExtractor()
    - version = extractor._find_version_header({"X-SCYTHE-TARGET-VERSION": "9.9.9"})
    - assert version == "9.9.9"
- Run just this test:
  - python -m unittest -q tests/test_demo_header_extractor_example.py
- Result: Ran 1 test, OK.
- Note: This file has been removed after demonstration to keep the repo clean. Use it as a template when adding new tests.

2.4 Guidance for Writing Tests for Key Subsystems
- Behaviors (scythe/behaviors/*):
  - Validate timing semantics and continuation logic via Behavior.get_step_delay, should_continue, on_error.
  - See tests/test_behaviors.py for lifecycle hooks integration with TTPExecutor; use MockTTP to avoid real drivers.
- Expected results system (TTP + TTPExecutor):
  - Ensure expected_result gating yields the correct summary classifications (EXPECTED SUCCESS/FAILURE). See tests/test_expected_results.py.
- Journeys and Actions:
  - Use mocks for WebDriver interactions; see tests/test_journeys.py for NavigateAction, ClickAction, FillFormAction, WaitAction, TTPAction, AssertAction.
- Orchestrators (scale/distributed/batch):
  - Keep orchestration delays tiny to prevent slow tests; see tests/test_orchestrators.py for patterns.
- Header extraction:
  - Prefer HeaderExtractor._find_version_header for isolated checks and extract_all_headers/extract_target_version with mocked driver logs for end-to-end parsing. See tests/test_header_extraction.py.

2.5 What the Suite Does Not Require
- No Chrome/Chromedriver is needed to run the unit tests (WebDriver interactions are mocked).
- No network access is needed; requests usage is limited and tested indirectly/mocked.

3. Additional Development Information
3.1 Coding Style and Practices
- Type hints: consistently used across core APIs; add typing to public interfaces and complex private helpers.
- Docstrings: document behavior, side effects, and expected semantics, especially for timing and retry logic.
- Logging: use component-scoped loggers for traceability. Patterns observed:
  - TTP logging prefix: "{TTP name}"; Journey and Orchestrator have scoped names as well.
  - HeaderExtractor uses a class-specific logger ("HeaderExtractor"). Avoid print; use logging with appropriate levels.
- Error handling:
  - Behaviors may alter continuation logic on_error; avoid raising unless it’s a hard failure path documented by the subsystem.
  - Authentication errors should surface as AuthenticationError with method context when available.

3.2 Architectural Notes (useful when extending)
- Behaviors are optional and backward-compatible. TTPExecutor runs unchanged if behavior is None.
- Expected results system is central: tests should assert summaries rather than only boolean outcomes.
- Journeys compose Actions; Actions should be deterministic and small in scope; external effects mocked in tests.
- Orchestrators accept strategies and can run sequentially or with workers; ensure determinism in unit tests by avoiding true concurrency.

3.3 Chrome DevTools Logging (when you do browser E2E)
- For capturing headers in live runs, configure Chrome options via HeaderExtractor.enable_logging_for_driver(chrome_options) before driver instantiation. The extractor parses Network.responseReceived/ExtraInfo entries and normalizes header keys. For unit tests, patch driver.get_log to return serialized CDP entries as shown in tests/test_header_extraction.py.

3.4 Release and Versioning
- VERSION file contains the target package version used by Taskfile.yml release task to rewrite setup.py.
- To prepare a release:
  - Update VERSION
  - task release  # requires Taskfile tooling (https://taskfile.dev)
  - Push tags as needed.

3.5 Common Pitfalls
- Do not introduce real sleeps in tests; mock time.sleep or set minimal delays.
- Keep selenium-using code paths behind mocks in tests to avoid CI flakiness.
- When adding new modules, ensure they are included by find_packages and not under tests/ or examples/.

Appendix: Quick Commands
- Install deps: pip install -r requirements.txt
- Full test run: python -m unittest -q
- Single file: python -m unittest -q tests/test_behaviors.py
- Single test: python -m unittest -q tests.test_behaviors.TestMachineBehavior.test_statistics
