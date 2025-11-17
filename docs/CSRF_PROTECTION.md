# CSRF Protection in Scythe

## Overview

Scythe now supports CSRF (Cross-Site Request Forgery) protection for API mode testing. This allows you to test web applications that require CSRF tokens with their API requests.

**Note:** CSRF support is **only needed for API mode**. UI mode using Selenium automatically handles CSRF tokens since the browser manages cookies and session state.

## When Do You Need This?

You need CSRF protection when:
- Testing in **API mode** (making raw HTTP requests)
- The target application requires CSRF tokens for state-changing requests (POST, PUT, PATCH, DELETE)
- CSRF tokens are provided via cookies, response headers, or response bodies

You **do not** need CSRF protection when:
- Testing in **UI mode** (Selenium/browser-based testing) - the browser handles this automatically

## Common CSRF Patterns by Framework

Different web frameworks implement CSRF protection differently. Here are the most common patterns:

| Framework | Cookie Name | Header/Body Name | Pattern |
|-----------|-------------|------------------|---------|
| **Django** | `csrftoken` | `X-CSRFToken` (header) or `csrfmiddlewaretoken` (body) | Cookie → Header |
| **Laravel** | `XSRF-TOKEN` | `X-XSRF-TOKEN` | Cookie → Header |
| **Spring Security** | `XSRF-TOKEN` | `X-XSRF-TOKEN` | Cookie → Header |
| **Ruby on Rails** | varies | `X-CSRF-Token` | Meta tag/Header |
| **Express.js (csurf)** | `_csrf` | `CSRF-Token` or body field | Configurable |
| **Custom** | varies | varies | Configurable |

## Basic Usage

### 1. Import the CSRFProtection class

```python
from scythe.core.csrf import CSRFProtection
```

### 2. Create a CSRF protection configuration

```python
# Django example
csrf = CSRFProtection(
    extract_from='cookie',      # Extract token from cookie
    cookie_name='csrftoken',    # Django's cookie name
    header_name='X-CSRFToken',  # Header to send token in
    inject_into='header'        # Send token via header
)
```

### 3. Add to your Journey or TTP

```python
from scythe.journeys.base import Journey
from scythe.core.csrf import CSRFProtection

csrf = CSRFProtection(
    cookie_name='csrftoken',
    header_name='X-CSRFToken'
)

journey = Journey(
    name="My API Journey",
    description="Test with CSRF protection",
    csrf_protection=csrf  # Add CSRF config here
)
```

## Configuration Examples

### Django (Cookie-based)

```python
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='csrftoken',
    header_name='X-CSRFToken',
    inject_into='header'
)
```

### Laravel / Spring Security

```python
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='XSRF-TOKEN',
    header_name='X-XSRF-TOKEN',
    inject_into='header'
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
```

### Token from Response Header

Some applications return the CSRF token in a response header instead of a cookie:

```python
csrf = CSRFProtection(
    extract_from='header',           
    header_name='X-CSRF-Token',      
    inject_into='header'
)
```

### Token from JSON Response Body

Some APIs return the CSRF token in the JSON response:

```python
csrf = CSRFProtection(
    extract_from='body',             
    body_field='csrfToken',        
    header_name='X-CSRF-Token',    
    inject_into='header'
)
```

### Token in Request Body (instead of header)

Some frameworks expect the CSRF token in the POST body:

```python
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='_csrf',
    body_field='_csrf',              
    inject_into='body'               
)
```

### With Automatic Retry (No Dedicated Refresh Endpoint)

**Most common scenario:** Your API automatically updates the CSRF cookie with every response, but there's no dedicated refresh endpoint. In this case, just configure CSRF protection normally - Scythe will automatically handle retries:

```python
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='__Host-csrf_',
    header_name='X-CSRF-Token',
    inject_into='header'
    # No refresh_endpoint needed!
)
```

**How it works:**
1. If a request fails with 403 or 419 (CSRF failure codes)
2. Scythe automatically makes a GET request to the base URL
3. Extracts the fresh CSRF token from the response cookie
4. Retries the original request with the new token

This handles the common pattern where APIs automatically rotate CSRF tokens with every response.

### With Dedicated Refresh Endpoint

If your application has a specific endpoint to get CSRF tokens:

```python
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='csrftoken',
    header_name='X-CSRFToken',
    refresh_endpoint='/api/csrf-token'  # Use this endpoint for refresh
)
```

## Complete Journey Example

```python
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import ApiRequestAction
from scythe.core.csrf import CSRFProtection
from scythe.auth.bearer import BearerTokenAuth

# Configure CSRF protection
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='__Host-csrf_',
    header_name='X-CSRF-Token',
    inject_into='header'
)

# Configure authentication
auth = BearerTokenAuth(
    login_url='/api/login',
    username='testuser',
    password='testpass'
)

# Create journey
journey = Journey(
    name="Create User Journey",
    description="Test creating a user with CSRF protection",
    authentication=auth,
    csrf_protection=csrf  # Enable CSRF
)

# Add step with API actions
step1 = Step(
    name="Initial GET request",
    description="Get the page and extract CSRF token",
    actions=[
        ApiRequestAction(
            method='GET',
            url='/api/users',
            expected_status=200
        )
    ]
)

step2 = Step(
    name="Create user",
    description="POST request with CSRF token",
    actions=[
        ApiRequestAction(
            method='POST',
            url='/api/users',
            body_json={
                'username': 'newuser',
                'email': 'newuser@example.com'
            },
            expected_status=201
        )
    ]
)

journey.add_step(step1)
journey.add_step(step2)

# Execute
from scythe.journeys.executor import JourneyExecutor

executor = JourneyExecutor(
    journey=journey,
    target_url='https://your-app.com',
    mode='API'  # Must be API mode
)

executor.run()
```

## Complete TTP Example (Request Flooding with CSRF)

```python
from scythe.ttps.web.request_flooding import RequestFloodingTTP
from scythe.core.csrf import CSRFProtection
from scythe.core.executor import TTPExecutor

# Configure CSRF
csrf = CSRFProtection(
    extract_from='cookie',
    cookie_name='XSRF-TOKEN',
    header_name='X-XSRF-TOKEN'
)

# Create TTP
ttp = RequestFloodingTTP(
    target_endpoints=['/api/products'],
    request_count=50,
    http_method='POST',
    payload_data={'search': 'test'},
    expected_result=False,  # Expect rate limiting
    execution_mode='api',
    csrf_protection=csrf  # Enable CSRF
)

# Execute
executor = TTPExecutor(
    ttp=ttp,
    target_url='https://your-app.com'
)

executor.run()
```

## How It Works

1. **First Request:** When you make the first API request, Scythe automatically extracts the CSRF token from:
   - Response cookies (if `extract_from='cookie'`)
   - Response headers (if `extract_from='header'`)
   - Response JSON body (if `extract_from='body'`)

2. **Token Storage:** The token is stored in the context and persists across all requests in the journey/TTP.

3. **Subsequent Requests:** For state-changing requests (POST, PUT, PATCH, DELETE), Scythe automatically injects the token into:
   - Request headers (if `inject_into='header'`)
   - Request body (if `inject_into='body'`)

4. **Automatic Extraction:** By default (`auto_extract=True`), every response is checked for a CSRF token, allowing it to be updated if the server rotates tokens.

5. **Automatic Retry on Failure:** If a request fails with status 403 or 419 (common CSRF failure codes), Scythe automatically:
   - Makes a GET request to refresh the CSRF token (uses `refresh_endpoint` if configured, otherwise uses base URL)
   - Extracts the new token from the response/cookie
   - Retries the original request with the fresh token
   - This works even without a dedicated refresh endpoint - perfect for APIs that auto-update CSRF cookies with every response

## Advanced Configuration

### Disable Auto-Extraction

If you only want to extract the token once:

```python
csrf = CSRFProtection(
    cookie_name='csrftoken',
    header_name='X-CSRFToken',
    auto_extract=False  # Only extract manually
)
```

### Specify Which Methods Require CSRF

By default, CSRF is only sent for POST, PUT, PATCH, DELETE. To customize:

```python
csrf = CSRFProtection(
    cookie_name='csrftoken',
    header_name='X-CSRFToken',
    required_for_methods=['POST', 'PUT', 'DELETE']  # Custom list
)
```

### Manual Token Management

You can manually extract and inject tokens:

```python
# Manual extraction
token = csrf.extract_token(response=response, session=session, context=context)

# Manual injection
headers, data = csrf.inject_token(
    token=token,
    headers=headers,
    data=data,
    method='POST',
    context=context
)
```

## Troubleshooting

### CSRF token not being extracted

1. Check the correct extraction source:
   - Use browser DevTools to see where the token comes from
   - Check Network tab → Response Headers or Cookies
   - Verify `extract_from`, `cookie_name`, `header_name`, or `body_field` match your application

2. Enable debug logging:
   ```python
   import logging
   logging.getLogger('scythe.core.csrf').setLevel(logging.DEBUG)
   ```

### CSRF failures still occurring

1. Verify the correct header/field name for injection
2. Check if your app requires the token in the body instead of header (or vice versa)
3. Some apps require BOTH the cookie AND the header - ensure the cookie is preserved by using the same session
4. Check if your app rotates tokens - ensure `auto_extract=True` (default)

### Token extracted but requests still fail

1. Your app might need the token in a different format
2. Some apps require the cookie to be present even when sending the header
3. Check if there's additional authentication needed (cookies, headers)

### Distinguishing CSRF failures from authorization failures

Both can return 403 Forbidden. Here's how Scythe handles this:

1. **First 403/419:** Scythe automatically attempts to refresh the CSRF token and retries
2. **Second 403 after retry:** If the retry also fails with 403, it's likely an authorization issue (not CSRF)

**What gets logged:**
```
[INFO] Hit 403 (possible CSRF failure); attempting to refresh token and retry
[INFO] Successfully refreshed CSRF token; retrying request
[WARNING] Request failed with 403 after CSRF retry - likely authorization issue
```

**To debug:**
- Enable debug logging to see token extraction/injection
- Check if the token is being updated between requests
- Verify your authentication is working (separate from CSRF)
- Use browser DevTools to compare your API requests with real browser requests

## Validating CSRF Enforcement

### CSRFValidationTTP - Test if CSRF is Actually Working

Scythe includes a dedicated TTP to **test whether CSRF protection is actually enforced** by your application:

```python
from scythe.ttps.web.csrf_validation import CSRFValidationTTP
from scythe.core.executor import TTPExecutor

csrf = CSRFProtection(
    cookie_name='__Host-csrf_',
    header_name='X-CSRF-Token'
)

ttp = CSRFValidationTTP(
    target_endpoints=['/api/users', '/api/posts', '/api/delete'],
    csrf_protection=csrf,
    expected_result=True  # Expect CSRF to be enforced
)

executor = TTPExecutor(ttp=ttp, target_url='https://your-app.com')
executor.run()

summary = ttp.get_validation_summary()
print(f"Result: {summary['overall_result']}")  # SECURE or VULNERABLE
print(f"Protected: {summary['protection_rate']}")
```

**What it tests:**
1. ❌ Requests WITHOUT CSRF token → Should be rejected (403/419)
2. ✅ Requests WITH valid CSRF token → Should succeed (200)
3. ❌ Requests with INVALID CSRF token → Should be rejected (403/419)

See [CSRF Validation Documentation](CSRF_VALIDATION.md) for complete details.

## Implementation Notes

- CSRF protection is **only active in API mode**
- The `requests.Session` object automatically manages cookies across requests
- Tokens are shared across all actions in a journey or all payloads in a TTP
- Rate limiting (429) and CSRF failures (403, 419) both support automatic retry with appropriate handling

