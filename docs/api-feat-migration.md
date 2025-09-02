# API Mode Feature Migration Guide

Last updated: 2025-09-02

This document tracks the design, rollout, and practical steps for introducing API-mode execution to Scythe so users can interact with REST APIs in addition to traditional UI/Selenium flows.

Goals
- Preserve full backward compatibility for existing UI-driven tests.
- Add an opt-in API execution mode that requires no browser.
- Provide a first-class ApiRequestAction for REST calls within Journeys.
- Support authentication for API runs via Authentication.get_auth_headers.
- Keep the unit test suite deterministic (no real browser/network required).

What Changed (High Level)
- JourneyExecutor now accepts mode parameter: "UI" (default) or "API".
- In API mode, a requests.Session is created and placed into the journey context under requests_session; any auth headers are merged under auth_headers for reuse.
- New Action: ApiRequestAction for performing REST calls during a Journey step.
- Authentication base supports get_auth_headers to supply tokens for API runs (BearerTokenAuth implements this).
- HeaderExtractor gained a hybrid method extract_target_version_hybrid that banner-grabs headers via requests first, then falls back to Selenium logs if a driver is provided.

Backward Compatibility
- UI remains the default. Existing scripts that do not specify mode continue to run unchanged.
- Existing Authentication implementations continue to work for UI mode. For API mode, add get_auth_headers when appropriate.

How to Use API Mode
1. Build a Journey as usual with Steps and Actions.
2. Use ApiRequestAction in steps where you want REST calls.
3. Execute with JourneyExecutor(..., mode="API"). No WebDriver is created.
4. Optionally provide an Authentication that implements get_auth_headers for API runs.

Code Snippet

from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import ApiRequestAction
from scythe.journeys.executor import JourneyExecutor

step = Step(
    name="Ping API",
    description="GET /api/ping should return 200",
    actions=[
        ApiRequestAction(method="GET", url="/api/ping", expected_status=200)
    ],
)
journey = Journey(name="API Smoke", description="Simple API health check", steps=[step])
executor = JourneyExecutor(journey=journey, target_url="http://localhost:8000", mode="API")
results = executor.run()
print(results.get("overall_success"))

Authentication for API Runs
- For bearer tokens, use scythe.auth.bearer.BearerTokenAuth. If you already have a token, construct BearerTokenAuth(token="..."), and JourneyExecutor in API mode will merge the Authorization header into the requests.Session.
- If you maintain custom auth, implement get_auth_headers to return a dict of headers.

Testing Guidance
- Unittests remain based on the standard library. Run with: python -m unittest -q
- Prefer mocking requests.Session for any tests you add around ApiRequestAction to avoid real network calls.
- No Chrome is required to run the unit suite. API mode uses requests only.

Migration Checklist
- [ ] Decide where API mode benefits your workflows (smoke checks, pre/post UI steps, backend validation).
- [ ] Add ApiRequestAction where REST interactions are needed.
- [ ] If API endpoints require auth, provide an Authentication with get_auth_headers.
- [ ] Execute your Journey with JourneyExecutor(..., mode="API").
- [ ] Keep UI steps as-is when mixing modes (you can still run in UI mode); or maintain separate API-only journeys.

Troubleshooting
- No headers captured: In API mode, HeaderExtractor will banner-grab using the target_url; ensure the endpoint responds with X-SCYTHE-TARGET-VERSION.
- Mixed results: Confirm expected_status in ApiRequestAction matches actual responses, or set expected_status=None to treat any 2xx (ok) as success.

References
- docs/EXECUTOR.md: JourneyExecutor modes and context keys
- docs/API_REFERENCE.md: ApiRequestAction reference
- docs/GETTING_STARTED.md: API Quickstart
- examples/api_mode_demo.py: runnable example



## Response Models (Pydantic) for API Responses

To validate and parse API JSON responses, ApiRequestAction supports an optional response_model parameter.
This lets you define the expected schema with a Pydantic v2 model and have Scythe validate it at runtime.

Key points:
- response_model: pass a model class (e.g., class Health(BaseModel): ...). ApiRequestAction will call model_validate(data) (Pydantic v2). If using a v1-like model, parse_obj(data) will be used as a fallback.
- response_model_context_key: optional; if set, the parsed model instance is placed into Journey context under this key; default is 'last_response_model'.
- fail_on_validation_error: when True, the action fails if validation raises; otherwise, HTTP status decides action success and the error is recorded under 'response_validation_error'.

Minimal example:

```python
from pydantic import BaseModel
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import ApiRequestAction
from scythe.journeys.executor import JourneyExecutor

class Health(BaseModel):
    status: str
    version: str | None = None

step = Step(
    name="Health",
    description="GET /api/health returns 200 and valid schema",
    actions=[
        ApiRequestAction(
            method="GET",
            url="/api/health",
            expected_status=200,
            response_model=Health,
            response_model_context_key="health_model",
            fail_on_validation_error=True,
        )
    ],
)

journey = Journey(name="API Schema Smoke", description="Schema check", steps=[step])
results = JourneyExecutor(journey, target_url="http://localhost:8080", mode="API").run()
```



## Hybrid Cookie-Based Authentication (New)

Some applications return a JWT in a login response and expect it as a cookie (e.g., `stellarbridge`). Scythe now supports this via CookieJWTAuth.

- Class: scythe.auth.cookie_jwt.CookieJWTAuth
- Configure: login_url, username/password, username_field, password_field, extra_fields, jwt_json_path (dot path), cookie_name (default 'stellarbridge').
- API mode: JourneyExecutor calls get_auth_cookies() and merges the returned mapping into requests.Session.cookies.
- UI mode: authenticate() performs the login if needed and sets the cookie in Selenium for the target domain.

Example (API mode):
```python
from scythe.auth import CookieJWTAuth
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import ApiRequestAction
from scythe.journeys.executor import JourneyExecutor

auth = CookieJWTAuth(
    login_url="http://localhost:8080/api/login",
    username="user@example.com",
    password="secret",
    username_field="email",
    password_field="password",
    jwt_json_path="auth.jwt",
    cookie_name="stellarbridge",
)

step = Step(
    name="Profile",
    description="Protected endpoint",
    actions=[ApiRequestAction(method="GET", url="/api/profile", expected_status=200)],
)
journey = Journey(name="Cookie API", description="", steps=[step], authentication=auth)

results = JourneyExecutor(journey, target_url="http://localhost:8080", mode="API").run()
```

See also: docs/HYBRID_AUTH.md and examples/api_cookie_auth_demo.py
