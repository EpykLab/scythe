# Hybrid Cookie-Based Authentication (CookieJWTAuth)

Last updated: 2025-09-02

Some applications authenticate via a JWT stored in a cookie instead of using Authorization headers. Scythe supports this hybrid pattern via CookieJWTAuth.

## When to Use
- Your login (e.g., POST /api/login) returns a JSON payload with a JWT.
- Subsequent requests are authenticated when a specific cookie (e.g., `stellarbridge`) is present.
- You want to run Journeys in API mode or UI mode with cookie-based session continuity.

## Key Capabilities
- Login via API to obtain the JWT.
- Extract token from nested JSON with a dot-path (e.g., `auth.jwt`).
- Provide cookies for API mode (requests.Session) and set Selenium cookie for UI mode.
- Backward-compatible with existing auth flows; no breaking changes.

## Class: CookieJWTAuth
Location: `scythe.auth.cookie_jwt`

Constructor parameters:
- `login_url: str` — Login endpoint URL for obtaining the token.
- `username: Optional[str]` — Username or email.
- `password: Optional[str]` — Password.
- `username_field: str = 'email'` — Field name to send username/email in the request payload.
- `password_field: str = 'password'` — Field name for password in the request payload.
- `extra_fields: Optional[Dict[str, Any]] = None` — Extra fields to include in the login payload.
- `jwt_json_path: str = 'token'` — Dot-path to token in the JSON response (e.g., `auth.jwt`).
- `cookie_name: str = 'stellarbridge'` — The cookie key used by your app.

Important methods:
- `get_auth_cookies() -> Dict[str, str]` — Returns `{cookie_name: token}`; performs login if needed. Used by API mode.
- `authenticate(driver: WebDriver, target_url: str) -> bool` — Performs login if needed and sets the cookie in Selenium for the target domain. Used by UI mode.
- `get_auth_headers() -> Dict[str, str]` — Returns `{}` for this hybrid strategy.

## API Mode Example
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
    description="Protected endpoint requires cookie",
    actions=[ApiRequestAction(method="GET", url="/api/profile", expected_status=200)],
)
journey = Journey(name="Cookie API", description="", steps=[step], authentication=auth)

results = JourneyExecutor(journey, target_url="http://localhost:8080", mode="API").run()
print("Overall:", results.get("overall_success"))
```

## UI Mode Example
```python
from scythe.auth import CookieJWTAuth
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import NavigateAction
from scythe.journeys.executor import JourneyExecutor

# Authenticate via API and set cookie in the browser, then navigate to a protected page
auth = CookieJWTAuth(
    login_url="http://localhost:8080/api/login",
    username="user@example.com",
    password="secret",
    jwt_json_path="token",
    cookie_name="stellarbridge",
)

step = Step(
    name="Dashboard",
    description="Open /dashboard after cookie auth",
    actions=[NavigateAction(url="http://localhost:8080/dashboard")],
)
journey = Journey(name="Cookie UI", description="", steps=[step], authentication=auth)

results = JourneyExecutor(journey, target_url="http://localhost:8080", mode="UI").run()
```

## Tips
- Use `extra_fields` to include MFA tokens or additional login payload fields.
- If your token is nested, set `jwt_json_path` accordingly (e.g., `data.session.jwt`).
- For cross-domain flows, ensure the `cookie_name` and domain align with your app’s cookie policy.

## Related Docs
- API Mode and ApiRequestAction: `docs/API_REFERENCE.md`
- JourneyExecutor modes: `docs/EXECUTOR.md`
- Migration guide: `docs/api-feat-migration.md`
- Example: `examples/api_cookie_auth_demo.py`
