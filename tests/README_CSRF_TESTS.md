# CSRF Protection Tests

## Overview

Comprehensive unit and integration tests for CSRF protection functionality in Scythe.

## Test Files

### 1. `test_csrf.py` - Unit Tests

Comprehensive unit tests for the `CSRFProtection` class covering all core functionality.

**Test Classes:**

- **TestCSRFProtectionInitialization** (2 tests)
  - Default initialization with all default parameters
  - Custom initialization with all parameters configured

- **TestCSRFTokenExtraction** (6 tests)
  - Extract token from response cookie
  - Extract token from session cookie
  - Extract token from response header
  - Extract token from JSON body
  - Handle missing token gracefully
  - Handle invalid JSON gracefully

- **TestCSRFTokenInjection** (8 tests)
  - Inject token into request headers
  - Inject token into request body
  - Skip injection for GET requests
  - Inject for POST requests
  - Custom method requirements (POST, DELETE only)
  - Handle missing token gracefully
  - Create headers dict if None

- **TestCSRFTokenRefresh** (4 tests)
  - Refresh with dedicated endpoint
  - Refresh without endpoint (uses base URL)
  - Handle request failures
  - Handle absolute URL endpoints

- **TestCSRFFailureHandling** (4 tests)
  - Retry on 403 status
  - Retry on 419 status
  - Don't retry on other statuses
  - Handle CSRF failure workflow

- **TestCSRFGetToken** (4 tests)
  - Get token from context
  - Get token from internal state
  - Context priority over internal state
  - Return None when no token

- **TestCSRFFrameworkPatterns** (3 tests)
  - Django pattern (csrftoken → X-CSRFToken)
  - Laravel pattern (XSRF-TOKEN → X-XSRF-TOKEN)
  - Custom __Host-csrf_ pattern

- **TestCSRFRepr** (1 test)
  - String representation

**Total Unit Tests: 32**

### 2. `test_csrf_integration.py` - Integration Tests

Integration tests verifying CSRF functionality with Journeys, Actions, and TTPs.

**Test Classes:**

- **TestApiRequestActionCSRFIntegration** (6 tests)
  - CSRF token injection in ApiRequestAction
  - Token extraction from response
  - Automatic retry on 403 with token refresh
  - No injection for GET requests
  - Works without CSRF protection (backward compatibility)

- **TestJourneyCSRFIntegration** (2 tests)
  - Journey initialization with CSRF
  - Executor sets CSRF in context

- **TestRequestFloodingCSRFIntegration** (2 tests)
  - RequestFloodingTTP initialization with CSRF
  - Token injection in flooding requests

- **TestCSRFBackwardCompatibility** (3 tests)
  - ApiRequestAction without CSRF still works
  - Journey without CSRF still works
  - TTP without CSRF still works

- **TestCSRFWithDifferentFrameworks** (2 tests)
  - Django CSRF pattern in action
  - Laravel CSRF pattern in action

**Total Integration Tests: 15**

## Total Test Coverage

**47 unit + integration tests** covering:

✅ CSRF token extraction (cookie, header, body)
✅ CSRF token injection (header, body)
✅ Automatic token refresh
✅ 403/419 retry logic
✅ Method-specific requirements
✅ Framework-specific patterns (Django, Laravel, custom)
✅ Integration with ApiRequestAction
✅ Integration with Journey
✅ Integration with RequestFloodingTTP
✅ Backward compatibility (no breaking changes)

## Running the Tests

### All CSRF Tests

```bash
# Run unit tests
python -m unittest tests.test_csrf -v

# Run integration tests
python -m unittest tests.test_csrf_integration -v

# Run all CSRF tests
python -m unittest discover -s tests -p "test_csrf*.py" -v
```

### Individual Test Classes

```bash
# Example: Run only extraction tests
python -m unittest tests.test_csrf.TestCSRFTokenExtraction -v

# Example: Run only integration tests
python -m unittest tests.test_csrf_integration.TestApiRequestActionCSRFIntegration -v
```

### Run All Tests Including Existing Tests

```bash
python -m unittest discover -s tests -p "test*.py" -v
```

## Test Coverage by Feature

### Core Functionality
- ✅ Initialization and configuration
- ✅ Token extraction from all sources
- ✅ Token injection into all targets
- ✅ Token storage and retrieval
- ✅ Method filtering

### Error Handling
- ✅ Missing tokens
- ✅ Invalid JSON
- ✅ Network errors
- ✅ 403/419 failures
- ✅ Refresh failures

### Integration
- ✅ ApiRequestAction integration
- ✅ Journey integration
- ✅ RequestFloodingTTP integration
- ✅ Executor context setup

### Backward Compatibility
- ✅ Code works without CSRF (optional feature)
- ✅ No breaking changes to existing APIs

### Framework Support
- ✅ Django pattern
- ✅ Laravel/Spring pattern
- ✅ Custom patterns

## Backward Compatibility Verification

All tests include backward compatibility checks:

1. **ApiRequestAction** - Works with and without CSRF protection
2. **Journey** - csrf_protection parameter is optional
3. **TTP** - csrf_protection parameter is optional
4. **RequestFloodingTTP** - Works with and without CSRF

No existing code should break due to CSRF additions.

## Key Test Scenarios Covered

### Scenario 1: Normal Flow
1. First request extracts token from cookie
2. Second POST request injects token
3. Response updates token
4. Third request uses updated token

### Scenario 2: 403 Retry Flow
1. POST request fails with 403
2. GET request to base URL to refresh token
3. Extract new token from response
4. Retry POST with new token
5. Success

### Scenario 3: Without CSRF (Backward Compatibility)
1. Make requests without CSRF configuration
2. Everything works as before
3. No errors or warnings

### Scenario 4: Multiple Framework Patterns
1. Configure for Django (csrftoken → X-CSRFToken)
2. Configure for Laravel (XSRF-TOKEN → X-XSRF-TOKEN)
3. Configure for custom (__Host-csrf_ → X-CSRF-Token)
4. All patterns work correctly

## Mock Strategy

Tests use `unittest.mock` to:
- Mock `requests.Session` for HTTP operations
- Mock responses with controlled status codes and cookies
- Mock drivers for Selenium-based operations
- Verify method calls and arguments
- Test error conditions without real network calls

## Notes

- All tests are self-contained and don't require external services
- Tests use mocking extensively to avoid network dependencies
- Tests verify both success and failure paths
- Edge cases are covered (missing tokens, invalid JSON, network errors)
- Tests compile successfully (syntax verified)
