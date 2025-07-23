# Changelog

All notable changes to Scythe will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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