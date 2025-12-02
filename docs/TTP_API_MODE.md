# TTP API Mode

## Overview

TTPs (Tactics, Techniques, and Procedures) now support two execution modes:

1. **UI Mode** (default): Uses Selenium WebDriver to interact with the web UI
2. **API Mode** (new): Makes direct HTTP requests to backend APIs

API mode allows you to test security controls at the backend level without the overhead of browser automation, making tests faster and enabling better rate limiting control.

## When to Use API Mode

### Use API Mode When:
- Testing backend API security controls directly
- You want faster test execution (no browser overhead)
- Testing rate limiting or brute force protections
- The security control is implemented at the API layer
- You need precise control over HTTP requests and headers
- Testing in CI/CD pipelines where browser automation is impractical

### Use UI Mode When:
- Testing UI-specific protections (CAPTCHA, UI rate limiting)
- Validating user experience during attacks
- The security control is implemented client-side
- Testing full end-to-end user workflows
- You need to verify visual feedback

## Supported TTPs

### Login Bruteforce (`LoginBruteforceTTP`)

**UI Mode Configuration:**
```python
from scythe.payloads.generators import WordlistPayloadGenerator
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP

# Traditional UI mode
ttp = LoginBruteforceTTP(
    payload_generator=WordlistPayloadGenerator('passwords.txt'),
    username='admin',
    username_selector='input[name="username"]',
    password_selector='input[name="password"]',
    submit_selector='button[type="submit"]',
    execution_mode='ui'  # Default
)
```

**API Mode Configuration:**
```python
# New API mode
ttp = LoginBruteforceTTP(
    payload_generator=WordlistPayloadGenerator('passwords.txt'),
    username='admin',
    execution_mode='api',
    api_endpoint='/api/auth/login',
    username_field='username',  # JSON field name
    password_field='password',  # JSON field name
    success_indicators={
        'status_code': 200,
        'response_contains': 'token',
        'response_not_contains': 'invalid'
    }
)
```

### SQL Injection - Input Field (`InputFieldInjector`)

**UI Mode Configuration:**
```python
from scythe.ttps.web.sql_injection import InputFieldInjector

# UI mode - inject into form fields
ttp = InputFieldInjector(
    target_url='http://example.com/search',
    field_selector='input[name="query"]',
    submit_selector='button[type="submit"]',
    payload_generator=sql_payloads,
    execution_mode='ui'
)
```

**API Mode Configuration:**
```python

full_form = {
    'first_name': 'something',
    'last_name': 'something else',
    'email': 'something@something.com',
    'phone': '123-456-7890' # we will inject into this field but need to set a default value
}


# API mode - inject into JSON request body
ttp = InputFieldInjector(
    payload_generator=sql_payloads,
    execution_mode='api',
    api_endpoint='/api/search',
    injection_field='phone',  # scythe will update this form field with the sql injection at runtime
    http_method='POST',  # or 'GET', 'PUT', etc.
    inject_full_form_payload: full_form,

)
```

### SQL Injection - URL Manipulation (`URLManipulation`)

**UI Mode Configuration:**
```python
from scythe.ttps.web.sql_injection import URLManipulation

# UI mode - navigate to URLs with payloads
ttp = URLManipulation(
    payload_generator=sql_payloads,
    target_url='http://example.com/items',
    execution_mode='ui'
)
```

**API Mode Configuration:**
```python
# API mode - send GET requests with payloads
ttp = URLManipulation(
    payload_generator=sql_payloads,
    execution_mode='api',
    api_endpoint='/api/items',
    query_param='id'  # Query parameter to inject into
)
```

## Using TTPs in Journeys

### Journey with TTPAction (API Mode)

```python
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import TTPAction
from scythe.journeys.executor import JourneyExecutor

# Create TTP in API mode
login_ttp = LoginBruteforceTTP(
    payload_generator=password_gen,
    username='admin',
    execution_mode='api',
    api_endpoint='/api/auth/login',
    username_field='username',
    password_field='password'
)

# Create journey
journey = Journey(
    name="API Bruteforce Test",
    description="Test login bruteforce via API"
)

step = Step(name="Bruteforce", description="Attempt bruteforce")
step.add_action(TTPAction(
    ttp=login_ttp,
    target_url="http://example.com"
))

journey.add_step(step)

# Execute in API mode
executor = JourneyExecutor(
    journey,
    target_url="http://example.com",
    api_mode=True  # Enable API mode
)
result = executor.execute()
```

## Rate Limiting in API Mode

API mode automatically handles rate limiting by:

1. **Honoring HTTP 429 responses**: Automatically pauses when receiving `429 Too Many Requests`
2. **Respecting `Retry-After` headers**: Waits the specified time before retrying
3. **Tracking `X-RateLimit-*` headers**: Monitors `X-RateLimit-Remaining` and `X-RateLimit-Reset`
4. **Shared context**: Rate limit state is shared across actions via the context dictionary

Example:
```python
# The TTP will automatically:
# 1. Check context['rate_limit_resume_at'] before making requests
# 2. Sleep if rate limit is active
# 3. Update context when rate limit headers are detected
# 4. Coordinate with other actions in the same journey
```

## Migration Guide

### Before (UI Mode Only)
```python
# Old approach: UI only
from scythe.payloads.generators import WordlistPayloadGenerator
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP

password_gen = WordlistPayloadGenerator('passwords.txt')

ttp = LoginBruteforceTTP(
    payload_generator=password_gen,
    username='admin',
    username_selector='input[name="username"]',
    password_selector='input[name="password"]',
    submit_selector='button[type="submit"]'
)

# Run with executor...
```

### After (With API Mode)
```python
# New approach: Choose UI or API mode
from scythe.payloads.generators import WordlistPayloadGenerator
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP

password_gen = WordlistPayloadGenerator('passwords.txt')

# Option 1: Keep using UI mode (no changes needed)
ui_ttp = LoginBruteforceTTP(
    payload_generator=password_gen,
    username='admin',
    username_selector='input[name="username"]',
    password_selector='input[name="password"]',
    submit_selector='button[type="submit"]',
    execution_mode='ui'  # Explicit (default)
)

# Option 2: Use new API mode for faster execution
api_ttp = LoginBruteforceTTP(
    payload_generator=password_gen,
    username='admin',
    execution_mode='api',
    api_endpoint='/api/auth/login',
    username_field='username',
    password_field='password',
    success_indicators={
        'status_code': 200,
        'response_not_contains': 'invalid'
    }
)
```

**Key Points:**
- **Backward compatible**: Existing UI mode code works unchanged
- **No breaking changes**: `execution_mode` defaults to `'ui'`
- **UI selectors optional**: When using API mode, you don't need CSS selectors
- **API fields required**: API mode requires `api_endpoint` and field names

## Creating Custom TTPs with API Mode Support

To add API mode support to a custom TTP:

```python
from scythe.core.ttp import TTP
from typing import Dict, Any
import requests

class MyCustomTTP(TTP):
    def __init__(self, 
                 payload_generator,
                 execution_mode='ui',
                 api_endpoint=None,
                 **kwargs):
        super().__init__(
            name="My Custom TTP",
            description="Does something cool",
            execution_mode=execution_mode
        )
        self.payload_generator = payload_generator
        self.api_endpoint = api_endpoint
    
    # UI mode methods (required)
    def get_payloads(self):
        yield from self.payload_generator()
    
    def execute_step(self, driver, payload):
        # UI mode implementation
        pass
    
    def verify_result(self, driver):
        # UI mode verification
        pass
    
    # API mode methods (optional - only if supporting API mode)
    def execute_step_api(self, session: requests.Session, 
                        payload: Any, context: Dict[str, Any]) -> requests.Response:
        """Execute via API request"""
        from urllib.parse import urljoin
        
        base_url = context.get('target_url', '')
        url = urljoin(base_url, self.api_endpoint)
        
        # Make your API request
        response = session.post(url, json={'data': payload})
        
        return response
    
    def verify_result_api(self, response: requests.Response, 
                         context: Dict[str, Any]) -> bool:
        """Verify API response"""
        return response.status_code == 200
```

## Benefits

### Performance
- **5-10x faster**: No browser startup or rendering overhead
- **Lower resource usage**: No WebDriver or browser processes
- **Parallel execution**: Easier to run multiple API tests concurrently

### Testing Capabilities
- **Direct backend testing**: Test API security controls without UI
- **Better rate limit handling**: Built-in rate limit coordination
- **More control**: Direct access to HTTP headers, status codes, response bodies
- **CI/CD friendly**: No need for headless browser setup

### Flexibility
- **Mixed mode**: Use both UI and API mode in the same journey
- **Easy migration**: Add API mode support without breaking existing tests
- **Reuse payloads**: Same payload generators work for both modes

## Examples

See `examples/ttp_api_mode_demo.py` for comprehensive examples including:
- Login bruteforce in UI and API modes
- SQL injection in UI and API modes
- Mixed mode with authentication
- Migration patterns

## Architecture

### How It Works

1. **TTP Base Class**: Extended with `execute_step_api()` and `verify_result_api()` methods
2. **Execution Mode**: TTPs have an `execution_mode` property ('ui' or 'api')
3. **TTPAction**: Automatically routes to UI or API execution based on mode
4. **Session Management**: API mode uses `requests.Session` stored in journey context
5. **Rate Limiting**: Shared context coordinates rate limit state across actions

### Request Flow (API Mode)

```
TTPAction.execute()
    ↓
Check execution_mode == 'api'
    ↓
Get/create requests.Session from context
    ↓
For each payload:
    ↓
    TTP.execute_step_api(session, payload, context)
        ↓
        Check rate limits in context
        ↓
        Make HTTP request
        ↓
        Update rate limit state in context
        ↓
        Return response
    ↓
    TTP.verify_result_api(response, context)
        ↓
        Check response for success indicators
        ↓
        Return True/False
```

## Backward Compatibility

- **All existing code works unchanged**: Default `execution_mode='ui'`
- **No required changes**: UI selectors still work as before
- **Gradual migration**: Add API mode support when needed
- **Mixed usage**: Use UI mode for some TTPs, API mode for others

## Future Enhancements

Potential future additions:
- GraphQL API support
- WebSocket TTP support
- gRPC API testing
- Custom authentication handlers for API mode
- Response model validation with Pydantic
