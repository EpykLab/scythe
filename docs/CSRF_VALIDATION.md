# CSRF Validation TTP

## Overview

The `CSRFValidationTTP` is a security testing tool that **validates whether CSRF protection is actually enforced** by your web application. It goes beyond simply checking if CSRF tokens are present - it actively tests whether the server rejects requests without valid tokens.

## Why You Need This

Many applications implement CSRF protection but don't properly enforce it. Common issues include:

- ❌ CSRF tokens generated but not validated
- ❌ Validation only checks for presence, not correctness
- ❌ Some endpoints protected, others vulnerable
- ❌ Invalid tokens accepted alongside valid ones

The `CSRFValidationTTP` detects these vulnerabilities by making actual requests to your endpoints and verifying the responses.

## How It Works

For each endpoint, the TTP runs three tests:

### Test 1: Request WITHOUT CSRF Token
**Expected:** Server should **reject** with 403 or 419
**Result:** If accepted (200), endpoint is **VULNERABLE**

### Test 2: Request WITH Valid CSRF Token
**Expected:** Server should **accept** with 200-299
**Result:** If rejected, CSRF implementation has issues

### Test 3: Request WITH Invalid/Fake CSRF Token
**Expected:** Server should **reject** with 403 or 419
**Result:** If accepted, server doesn't validate tokens properly

## Basic Usage

```python
from scythe.ttps.web.csrf_validation import CSRFValidationTTP
from scythe.core.csrf import CSRFProtection
from scythe.core.executor import TTPExecutor

# Configure CSRF extraction/injection
csrf = CSRFProtection(
    cookie_name='csrftoken',
    header_name='X-CSRF-Token'
)

# Create validation TTP
ttp = CSRFValidationTTP(
    target_endpoints=[
        '/api/users',
        '/api/posts',
        '/api/comments'
    ],
    http_method='POST',
    test_payload={'test': 'data'},
    csrf_protection=csrf,
    expected_result=True  # Expect CSRF to be enforced (secure)
)

# Execute validation
executor = TTPExecutor(ttp=ttp, target_url='https://your-app.com')
results = executor.run()

# Get detailed results
summary = ttp.get_validation_summary()
print(f"Overall: {summary['overall_result']}")  # SECURE or VULNERABLE
print(f"Protected: {summary['endpoints_protected']}")
print(f"Vulnerable: {summary['endpoints_vulnerable']}")
```

## Configuration Options

### Constructor Parameters

```python
CSRFValidationTTP(
    target_endpoints,              # List of endpoints to test (required)
    http_method='POST',            # HTTP method to use
    test_payload=None,             # Optional payload data
    csrf_protection=None,          # CSRFProtection configuration
    expected_rejection_codes=None, # Codes indicating rejection (default: [403, 419])
    expected_success_codes=None,   # Codes indicating success (default: 200-299)
    test_invalid_token=True,       # Test with invalid tokens
    invalid_token_value='...',     # Value to use for invalid token
    expected_result=True,          # True = expect enforcement (secure)
    authentication=None            # Optional authentication
)
```

### Parameters Explained

**`target_endpoints`** (required)
- List of API endpoints to test
- Example: `['/api/users', '/api/posts', '/api/delete']`

**`http_method`** (default: 'POST')
- HTTP method for testing
- Usually POST, PUT, PATCH, or DELETE

**`test_payload`** (optional)
- Data to send in request body
- Example: `{'action': 'test', 'data': 'value'}`

**`csrf_protection`** (required for full testing)
- `CSRFProtection` object configuring token extraction/injection
- If None, only tests rejection without tokens

**`expected_rejection_codes`** (default: `[403, 419]`)
- HTTP status codes indicating CSRF rejection
- 403 = Forbidden (Django, Rails)
- 419 = Page Expired (Laravel)

**`expected_success_codes`** (default: `200-299`)
- HTTP status codes indicating successful requests
- Usually 200, 201, 204

**`test_invalid_token`** (default: True)
- Whether to test with invalid/fake tokens
- Set to False to only test without tokens

**`invalid_token_value`** (default: 'invalid-csrf-token-12345')
- The fake token value to use for invalid token tests

**`expected_result`** (default: True)
- True = expect CSRF to be enforced (secure configuration)
- False = expect CSRF NOT to be enforced (for public endpoints)

**`authentication`** (optional)
- Authentication object for protected endpoints
- Example: `BearerTokenAuth(...)` or `BasicAuth(...)`

## Framework-Specific Configurations

### Django

```python
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='csrftoken',
    header_name='X-CSRFToken',
    inject_into='header'
)

ttp = CSRFValidationTTP(
    target_endpoints=['/api/endpoint'],
    csrf_protection=csrf,
    expected_rejection_codes=[403]  # Django uses 403
)
```

### Laravel

```python
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='XSRF-TOKEN',
    header_name='X-XSRF-TOKEN',
    inject_into='header'
)

ttp = CSRFValidationTTP(
    target_endpoints=['/api/endpoint'],
    csrf_protection=csrf,
    expected_rejection_codes=[419]  # Laravel uses 419
)
```

### Custom Application

```python
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='__Host-csrf_',
    header_name='X-CSRF-Token',
    inject_into='header'
)

ttp = CSRFValidationTTP(
    target_endpoints=['/api/endpoint'],
    csrf_protection=csrf
)
```

## Reading Results

### Get Summary

```python
summary = ttp.get_validation_summary()
```

**Summary Fields:**

- `overall_result`: 'SECURE' or 'VULNERABLE'
- `endpoints_tested`: Number of unique endpoints tested
- `endpoints_protected`: Endpoints with all tests passing
- `endpoints_vulnerable`: Endpoints with any test failing
- `protection_rate`: "X/Y" format (protected/total)
- `test_details`: List of all individual test results
- `endpoint_status`: Per-endpoint breakdown

### Individual Test Results

```python
for detail in summary['test_details']:
    print(f"{detail['endpoint']} - {detail['test_type']}")
    print(f"  Status: {detail['status_code']}")
    print(f"  Result: {detail['result']}")  # PASS or FAIL
    print(f"  Behavior: {detail['behavior']}")
```

**Test Detail Fields:**

- `endpoint`: The endpoint tested
- `test_type`: 'without_token', 'with_valid_token', or 'with_invalid_token'
- `expected_outcome`: 'rejected' or 'success'
- `status_code`: HTTP response code
- `response_time_ms`: Time taken in milliseconds
- `result`: 'PASS' or 'FAIL'
- `behavior`: Description of what happened

## Common Use Cases

### 1. Security Audit

Test all API endpoints to find CSRF vulnerabilities:

```python
ttp = CSRFValidationTTP(
    target_endpoints=[
        '/api/users',
        '/api/posts',
        '/api/comments',
        '/api/admin/settings',
        '/api/data/export',
        '/api/account/delete'
    ],
    csrf_protection=csrf,
    expected_result=True
)
```

### 2. Regression Testing

Ensure CSRF protection wasn't broken by recent changes:

```python
# Run after deployments
ttp = CSRFValidationTTP(
    target_endpoints=['/api/critical-endpoint'],
    csrf_protection=csrf,
    expected_result=True
)

results = executor.run()
summary = ttp.get_validation_summary()

if summary['overall_result'] != 'SECURE':
    raise Exception("CSRF protection regression detected!")
```

### 3. Testing Public Endpoints

Verify that public endpoints correctly don't require CSRF:

```python
ttp = CSRFValidationTTP(
    target_endpoints=[
        '/api/public/contact',
        '/api/public/newsletter'
    ],
    csrf_protection=csrf,
    expected_result=False  # Should NOT be enforced
)
```

### 4. Authenticated Endpoints

Test CSRF on endpoints requiring authentication:

```python
from scythe.auth.bearer import BearerTokenAuth

auth = BearerTokenAuth(
    login_url='/api/login',
    username='testuser',
    password='testpass'
)

ttp = CSRFValidationTTP(
    target_endpoints=['/api/profile/update'],
    csrf_protection=csrf,
    authentication=auth
)
```

## Interpreting Results

### Secure Configuration

```
Overall Result: SECURE
Endpoints Tested: 3
Protected: 3
Vulnerable: 0
Protection Rate: 3/3

✓ /api/users - without_token: 403 - Correctly rejected
✓ /api/users - with_valid_token: 200 - Correctly accepted
✓ /api/users - with_invalid_token: 403 - Correctly rejected
✓ /api/posts - without_token: 403 - Correctly rejected
✓ /api/posts - with_valid_token: 200 - Correctly accepted
✓ /api/posts - with_invalid_token: 403 - Correctly rejected
✓ /api/comments - without_token: 403 - Correctly rejected
✓ /api/comments - with_valid_token: 200 - Correctly accepted
✓ /api/comments - with_invalid_token: 403 - Correctly rejected
```

**Interpretation:** All endpoints properly enforce CSRF protection. ✅

### Vulnerable Configuration

```
Overall Result: VULNERABLE
Endpoints Tested: 3
Protected: 2
Vulnerable: 1
Protection Rate: 2/3

✓ /api/users - without_token: 403 - Correctly rejected
✓ /api/users - with_valid_token: 200 - Correctly accepted
✓ /api/posts - without_token: 403 - Correctly rejected
✓ /api/posts - with_valid_token: 200 - Correctly accepted
✗ /api/delete - without_token: 200 - Should reject but got 200  ⚠️
✓ /api/delete - with_valid_token: 200 - Correctly accepted
```

**Interpretation:** `/api/delete` accepts requests without CSRF tokens - **CRITICAL VULNERABILITY** ⚠️

### Partial Issues

```
✓ /api/users - without_token: 403 - Correctly rejected
✓ /api/users - with_valid_token: 200 - Correctly accepted
✗ /api/users - with_invalid_token: 200 - Should reject but got 200
```

**Interpretation:** Server checks for token presence but doesn't validate it properly.

## Best Practices

### 1. Test All State-Changing Endpoints

```python
# Test POST, PUT, PATCH, DELETE - not GET
for method in ['POST', 'PUT', 'PATCH', 'DELETE']:
    ttp = CSRFValidationTTP(
        target_endpoints=get_endpoints_for_method(method),
        http_method=method,
        csrf_protection=csrf
    )
    executor.run()
```

### 2. Run Regularly

- Include in CI/CD pipeline
- Run after every deployment
- Schedule periodic security audits

### 3. Test Different User Roles

```python
for role in ['user', 'admin', 'moderator']:
    auth = get_auth_for_role(role)
    ttp = CSRFValidationTTP(
        target_endpoints=get_endpoints_for_role(role),
        csrf_protection=csrf,
        authentication=auth
    )
    executor.run()
```

### 4. Document Results

```python
summary = ttp.get_validation_summary()

# Save to file
with open('csrf_audit.json', 'w') as f:
    json.dump(summary, f, indent=2)

# Generate report
generate_security_report(summary)
```

## Troubleshooting

### Issue: All Tests Fail

**Possible causes:**
- CSRF configuration incorrect
- Endpoints require authentication (add `authentication` parameter)
- Wrong base URL

### Issue: Invalid Token Test Passes (Vulnerability)

**Meaning:** Server is NOT validating token correctness

**Action:** Review server-side CSRF validation logic

### Issue: Valid Token Test Fails

**Possible causes:**
- Token extraction not working
- Token not being injected correctly
- Token expires too quickly
- Server expects token in different format

## Limitations

- Only tests API mode (HTTP requests)
- Requires CSRF protection to be configured
- Cannot test time-based token expiration automatically
- Does not test CSRF protection in forms (UI mode)

## Security Impact

**High-Risk Vulnerabilities:**
- Requests without tokens accepted
- Invalid tokens accepted
- State-changing endpoints unprotected

**Medium-Risk Issues:**
- Inconsistent protection across endpoints
- Different validation for different methods

**Recommendations:**
- Fix all vulnerabilities before production
- Implement comprehensive CSRF protection
- Regularly test with this TTP

## Example Output

```
CSRF VALIDATION SUMMARY
============================================================
Overall Result: VULNERABLE
Endpoints Tested: 5
Protected: 3
Vulnerable: 2
Protection Rate: 3/5

------------------------------------------------------------
DETAILED RESULTS:
------------------------------------------------------------
✓ /api/users - without_token: 403 - Correctly rejected
✓ /api/users - with_valid_token: 200 - Correctly accepted
✓ /api/users - with_invalid_token: 403 - Correctly rejected
✓ /api/posts - without_token: 403 - Correctly rejected
✓ /api/posts - with_valid_token: 200 - Correctly accepted
✓ /api/posts - with_invalid_token: 403 - Correctly rejected
✗ /api/delete - without_token: 200 - Should reject but got 200 ⚠️
✓ /api/delete - with_valid_token: 200 - Correctly accepted
✓ /api/settings - without_token: 403 - Correctly rejected
✗ /api/settings - with_invalid_token: 200 - Should reject but got 200 ⚠️
```

## Related Documentation

- [CSRF Protection Configuration](CSRF_PROTECTION.md)
- [CSRFProtection Class Reference](../scythe/core/csrf.py)
- [API Request Actions](../scythe/journeys/actions.py)
