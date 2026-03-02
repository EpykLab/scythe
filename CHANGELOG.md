# Changelog

All notable changes to Scythe will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Deterministic execution hooks for testing:
  - `sleep_fn` support in `TTPExecutor` and `JourneyExecutor`
  - `_time_fn` / `_sleep_fn` context hooks respected by Journey/API action timing paths
  - `rng_seed` support in `RequestFloodingTTP` for stable randomized payload generation
- Retry observability metadata in `ApiRequestAction` (`attempt_count`, `retry_reason`, `retry_wait_s`, `final_error_type`, `final_error_message`)
- JSON path assertions for `ApiRequestAction` via `expected_json_paths`, including `"__exists__"` presence checks and per-path diagnostics (`json_path_checks`, `json_paths_ok`, `api_assertions_ok`).
- Mandatory CI test gates for release/publish workflows and a dedicated `.github/workflows/tests.yaml`

### Changed
- Removed library-level global logging configuration from executors; applications now own logging setup.
- Improved orchestration determinism by isolating mutable state per replication and sorting parallel/distributed results deterministically.
- `Step.execute()` now resets step/action execution state per run to prevent cross-run contamination.

### Fixed
- SQL injection TTP mutable default payload state (`full_form_payload`) no longer leaks across runs.
- UUID guessing status-code check now correctly evaluates `404/401/403` using membership testing.

### Documentation
- Updated executor/API reference docs for deterministic hooks and logging behavior.
- Updated API mode guide examples to use `JourneyExecutor(..., mode="API")` and `run()`.
- Updated getting-started guidance to reflect application-owned logging and deterministic testing patterns.
- Added documentation and examples for `ApiRequestAction.expected_json_paths` in API reference, getting-started guide, and README.

### Added
- **X-SCYTHE-TARGET-VERSION Header Extraction**: Scythe now automatically captures and displays the `X-SCYTHE-TARGET-VERSION` header from HTTP responses
  - Shows version information in test results and summaries
  - Helps track which version of your web application is being tested
  - Supports case-insensitive header detection
  - Available in both TTP and Journey test executions
  - Includes version summary statistics across multiple test results
- New `HeaderExtractor` utility class for HTTP response header capture
- Enhanced test result logging with version information display
- Example scripts demonstrating version header functionality
- Test server implementation that sets version headers for testing

### Enhanced
- TTPExecutor now includes version information in result entries and summary output
- JourneyExecutor displays version data for each step and overall journey results
- Chrome WebDriver setup automatically enables performance logging for header extraction
- Result dictionaries now include `target_version` field when version headers are detected

### Documentation
- Added version detection section to README with usage examples
- Included server-side implementation examples for various frameworks (Flask, Express, Spring Boot)
- Created comprehensive example script (`version_header_example.py`)
- Added test server (`test_server_with_version.py`) for feature demonstration

### Technical Details
- Header extraction uses Chrome DevTools performance logs via Selenium
- Graceful fallback when headers are not present or logging fails
- Supports URL filtering to match headers from specific target responses
- Thread-safe implementation suitable for concurrent test execution

This feature enables teams to:
- Track test results by application version
- Verify deployment status during testing  
- Correlate issues with specific software versions
- Ensure consistency across test environments
