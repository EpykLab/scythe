# Authentication with CSRF Protection

This document explains how to integrate CSRF protection with Scythe's authentication system.

## Overview

Many web applications require CSRF tokens to authenticate users. The Scythe framework now supports CSRF protection across all authentication methods:

- **BasicAuth** - Form-based authentication (browser handles CSRF automatically)
- **BearerTokenAuth** - Token-based API authentication
- **CookieJWTAuth** - API authentication that uses JWT as cookies

## Quick Start

### Example 1: CookieJWTAuth with Django CSRF

```python
from scythe.auth.cookie_jwt import CookieJWTAuth
from scythe.core.csrf import CSRFProtection

# Configure CSRF for Django (default pattern)
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='csrftoken',      # Django default cookie name
    header_name='X-CSRFToken'      # Django header name
)

# Configure JWT authentication with CSRF
auth = CookieJWTAuth(
    login_url='https://django-app.com/api/login',
    username='user@example.com',
    password='password',
    csrf_protection=csrf
)

# CookieJWTAuth will now:
# 1. GET login endpoint to extract CSRF token
# 2. POST credentials with CSRF token in header
# 3. Extract JWT from response
# 4. Return JWT as cookie for subsequent requests
```

### Example 2: Bearer Token with CSRF

```python
from scythe.auth.bearer import BearerTokenAuth
from scythe.core.csrf import CSRFProtection

csrf = CSRFProtection(
    cookie_name='csrftoken',
    header_name='X-CSRF-Token'
)

# With pre-existing token (CSRF config stored but not used)
auth = BearerTokenAuth(
    token='existing-jwt-token',
    csrf_protection=csrf
)

# Or for token acquisition (CSRF used during login)
auth = BearerTokenAuth(
    token_url='https://api.example.com/oauth/token',
    username='service_account',
    password='service_secret',
    csrf_protection=csrf
)
```

### Example 3: BasicAuth with CSRF (UI Mode)

```python
from scythe.auth.basic import BasicAuth
from scythe.core.csrf import CSRFProtection

csrf = CSRFProtection(
    cookie_name='csrftoken',
    header_name='X-CSRF-Token'
)

# In UI mode, Selenium/WebDriver handles CSRF automatically
# CSRF config is stored for reference/documentation
auth = BasicAuth(
    username='testuser',
    password='testpass',
    login_url='https://app.com/login',
    csrf_protection=csrf
)
```

## Framework-Specific Configurations

### Django

Django uses `csrftoken` cookie and `X-CSRFToken` header by default:

```python
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='csrftoken',
    header_name='X-CSRFToken',
    inject_into='header'
)

auth = CookieJWTAuth(
    login_url='https://django-app.com/api/login',
    username='user',
    password='pass',
    csrf_protection=csrf
)
```

### Laravel

Laravel uses `XSRF-TOKEN` cookie and `X-XSRF-TOKEN` header:

```python
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='XSRF-TOKEN',
    header_name='X-XSRF-TOKEN',
    inject_into='header'
)

auth = CookieJWTAuth(
    login_url='https://laravel-app.com/api/login',
    username='user',
    password='pass',
    csrf_protection=csrf
)
```

### Custom Applications

For custom CSRF implementations:

```python
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='__Host-csrf_',          # Custom cookie name
    header_name='X-CSRF-Token',
    body_field='_csrf_token',            # Can also be in body
    inject_into='header',                 # or 'body'
    refresh_endpoint='/api/csrf-token',  # Optional dedicated endpoint
    auto_extract=True                    # Extract updated tokens from responses
)

auth = CookieJWTAuth(
    login_url='https://custom-app.com/login',
    username='user',
    password='pass',
    csrf_protection=csrf
)
```

## Integration with TTPs

### Using Authentication in a TTP

```python
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.core.executor import TTPExecutor
from scythe.core.csrf import CSRFProtection
from scythe.auth.cookie_jwt import CookieJWTAuth

# Configure CSRF
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='csrftoken',
    header_name='X-CSRF-Token'
)

# Configure authentication
auth = CookieJWTAuth(
    login_url='https://api.example.com/login',
    username='admin',
    password='password',
    csrf_protection=csrf
)

# Create TTP with authentication
ttp = LoginBruteforceTTP(
    payload_generator=password_generator,
    username='testuser',
    execution_mode='api',
    api_endpoint='/api/login',
    authentication=auth,  # Use authenticated session
    csrf_protection=csrf  # Also protect the bruteforce requests
)

# Execute
executor = TTPExecutor(ttp=ttp, target_url='https://api.example.com')
results = executor.run()
```

## How It Works

### Flow for CookieJWTAuth with CSRF

1. **GET request** to login endpoint to extract CSRF token
   - Extracts token from response cookie (or header/body)
   - Stores token in context

2. **POST request** with credentials
   - Injects CSRF token into headers or body
   - Sends login credentials

3. **Extract JWT token** from response
   - Saves JWT for subsequent authenticated requests

4. **Auto-extract updated tokens** (if enabled)
   - CSRF tokens may be refreshed with every response
   - Automatically updated for next request

### Automatic Retry on CSRF Failure

When a request fails with 403/419 (Forbidden/Unprocessable Entity):

1. Framework detects CSRF token may be expired
2. Makes GET request to refresh CSRF token
3. Retries POST request with new token
4. Logs the retry attempt for debugging

## Configuration Options

### CSRFProtection Parameters

```python
csrf = CSRFProtection(
    # Token extraction
    extract_from='cookie',              # 'cookie', 'header', or 'body'
    cookie_name='csrftoken',            # Cookie name to extract from
    header_name='X-CSRF-Token',         # Header name to extract from
    body_field='csrfToken',             # JSON field name in response body

    # Token injection
    inject_into='header',               # 'header' or 'body'

    # Token refresh
    refresh_endpoint=None,              # Optional dedicated refresh endpoint
    auto_extract=True,                  # Extract updated tokens from responses
    required_for_methods=['POST', 'PUT', 'DELETE', 'PATCH'],

    # Error handling
    retry_on_failure=True               # Automatically retry on 403/419
)
```

### Authentication Parameters with CSRF

All authentication classes accept `csrf_protection`:

```python
# BasicAuth
auth = BasicAuth(
    username='user',
    password='pass',
    csrf_protection=csrf  # Optional
)

# BearerTokenAuth
auth = BearerTokenAuth(
    token='existing-token',
    csrf_protection=csrf  # Optional
)

# CookieJWTAuth
auth = CookieJWTAuth(
    login_url='https://api.example.com/login',
    username='user',
    password='pass',
    csrf_protection=csrf  # Optional
)
```

## Best Practices

### 1. Use Framework-Specific Configurations

Different frameworks have different CSRF patterns. Use the correct configuration:

```python
# Django
CSRFProtection(cookie_name='csrftoken', header_name='X-CSRFToken')

# Laravel
CSRFProtection(cookie_name='XSRF-TOKEN', header_name='X-XSRF-TOKEN')

# Custom
CSRFProtection(cookie_name='__Host-csrf_', header_name='X-CSRF-Token')
```

### 2. Enable Auto-Extraction for Dynamic Tokens

If your API refreshes CSRF tokens with each response:

```python
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='csrftoken',
    auto_extract=True  # Always extract updated tokens
)
```

### 3. Provide Refresh Endpoint if Available

Some APIs have dedicated endpoints to get fresh CSRF tokens:

```python
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='csrftoken',
    refresh_endpoint='/api/csrf-token'  # Called on 403/419 errors
)
```

### 4. Combine Auth and CSRF for Complete Protection

```python
csrf = CSRFProtection(...)
auth = CookieJWTAuth(
    login_url='...',
    username='...',
    password='...',
    csrf_protection=csrf  # Login uses CSRF
)

ttp = SomeTTP(
    authentication=auth,   # Use auth for login
    csrf_protection=csrf   # Use CSRF for requests
)
```

## Troubleshooting

### Issue: "CSRF token not found in response"

**Cause:** The CSRF token is in a different location than configured.

**Solution:** Check your app's login page and verify the cookie/header/body field names:

```python
# Debug: Check what's in the response
import requests
session = requests.Session()
response = session.get('https://api.example.com/login')

# Inspect cookies
print("Cookies:", dict(response.cookies))

# Inspect headers
print("Headers:", response.headers)

# Inspect body
print("Body:", response.text[:500])

# Adjust your configuration accordingly
csrf = CSRFProtection(
    extract_from='cookie',  # or 'header' or 'body'
    cookie_name='correct_name',
    header_name='Correct-Header-Name'
)
```

### Issue: "401 Unauthorized" during login

**Cause:** CSRF token is missing or invalid.

**Cause:** Credentials are wrong.

**Solution:** Check that:

1. CSRF configuration is correct
2. Credentials are valid
3. Login endpoint is correct
4. Network requests are being made (enable logging)

### Issue: Requests keep failing with 403

**Cause:** CSRF token expires between requests.

**Solution:** Enable auto-extraction and automatic retry:

```python
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='csrftoken',
    auto_extract=True,      # Extract tokens from every response
    retry_on_failure=True   # Retry on 403/419
)
```

## Testing Authentication with CSRF

```python
from scythe.auth.cookie_jwt import CookieJWTAuth
from scythe.core.csrf import CSRFProtection

def test_auth_with_csrf():
    csrf = CSRFProtection(...)
    auth = CookieJWTAuth(
        login_url='...',
        username='test_user',
        password='test_pass',
        csrf_protection=csrf
    )

    # Test getting cookies (triggers auth flow)
    cookies = auth.get_auth_cookies()

    assert cookies is not None
    assert 'auth' in cookies or 'token' in cookies

    # Test auth headers
    headers = auth.get_auth_headers()
    # Most cookie-based auth won't have headers
    assert headers == {}

    # Test authentication status
    assert auth.is_authenticated(driver) == True
```

## Examples

See `examples/auth_csrf_example.py` for complete working examples:

1. Django form-based login with CSRF
2. API JWT login with CSRF
3. Bearer token auth with CSRF
4. Complete bruteforce test with auth
5. Multiple authentication methods
6. Manual CSRF token management
7. CSRF-protected auth in Journey

## See Also

- [CSRF Protection](CSRF_PROTECTION.md) - Core CSRF functionality
- [CSRF Validation](CSRF_VALIDATION.md) - Testing CSRF protection
- [Authentication Documentation](../scythe/auth/base.py) - Auth API reference
