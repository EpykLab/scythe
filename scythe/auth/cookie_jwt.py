from __future__ import annotations

import time
from typing import Dict, Optional, Any, TYPE_CHECKING
from urllib.parse import urlparse

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover - tests may run without requests installed
    requests = None  # type: ignore
from selenium.webdriver.remote.webdriver import WebDriver

from .base import Authentication, AuthenticationError

if TYPE_CHECKING:
    from ..core.csrf import CSRFProtection


def _extract_by_dot_path(data: Any, path: str) -> Optional[Any]:
    """
    Extract a value from a nested dict/list structure using a simple dot path.
    Supports numeric indices for lists, e.g., "data.items.0.token".
    """
    if not path:
        return None
    parts = path.split(".")
    current: Any = data
    for part in parts:
        if isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                return None
        elif isinstance(current, list):
            try:
                idx = int(part)
            except ValueError:
                return None
            if idx < 0 or idx >= len(current):
                return None
            current = current[idx]
        else:
            return None
    return current


class CookieJWTAuth(Authentication):
    """
    Hybrid authentication where a JWT is acquired from an API login response and
    then used as a cookie for subsequent requests. Useful when the target server
    expects a cookie (e.g., "stellarbridge") instead of Authorization headers.
    
    Behavior:
    - In API mode: JourneyExecutor will call get_auth_cookies(); this class will
      perform a POST to login_url (if token not cached), extract the token, and 
      return {cookie_name: token}.
    - In UI mode: authenticate() will ensure the browser has the cookie set for
      the target domain.
    
    Parameters:
    - content_type: Either "json" (default) to send payload as JSON, or "form" 
      to send as application/x-www-form-urlencoded form data.
    - jwt_source: Either "json" (default) to extract JWT from the JSON response body
      using jwt_json_path, or "cookie" to extract it from the Set-Cookie response header
      using cookie_name.
    """

    def __init__(self,
                 login_url: str,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 username_field: str = "email",
                 password_field: str = "password",
                 extra_fields: Optional[Dict[str, Any]] = None,
                 jwt_json_path: str = "token",
                 cookie_name: str = "stellarbridge",
                 content_type: str = "json",
                 jwt_source: str = "json",
                 session: Optional[requests.Session] = None,
                 description: str = "Authenticate via API and set JWT cookie",
                 csrf_protection: Optional['CSRFProtection'] = None,
                 session_endpoint: Optional[str] = None):
        super().__init__(
            name="Cookie JWT Authentication",
            description=description,
            csrf_protection=csrf_protection,
            session_endpoint=session_endpoint
        )
        self.login_url = login_url
        self.username = username
        self.password = password
        self.username_field = username_field
        self.password_field = password_field
        self.extra_fields = extra_fields or {}
        self.jwt_json_path = jwt_json_path
        self.cookie_name = cookie_name
        self.content_type = content_type
        self.jwt_source = jwt_source
        # Avoid importing requests in test environments; allow injected session
        self._session = session or (requests.Session() if requests is not None else None)
        self.token: Optional[str] = None

    def _login_and_get_token(self) -> str:
        # Import here to avoid circular imports
        from ..core.csrf import CSRFProtection

        # Create auth context for CSRF
        context = {}
        headers = {}

        # If CSRF protection is configured, get initial CSRF token
        if isinstance(self.csrf_protection, CSRFProtection):
            # Use session_endpoint if available (to get fresh session + CSRF)
            # Otherwise use login_url
            # Important: Only make ONE GET request to avoid regenerating tokens
            csrf_endpoint = self.session_endpoint if self.session_endpoint else self.login_url
            try:
                resp = self._session.get(csrf_endpoint, timeout=15)
                # Extract CSRF token from the GET response
                self.csrf_protection.extract_token(
                    response=resp,
                    session=self._session,
                    context=context
                )
            except Exception as e:
                raise AuthenticationError(f"Failed to get CSRF token: {e}", self.name)
        elif self.session_endpoint:
            # No CSRF, but session_endpoint is set - just establish the session
            try:
                self._session.get(self.session_endpoint, timeout=15)
            except Exception as e:
                raise AuthenticationError(f"Failed to establish session at {self.session_endpoint}: {e}", self.name)

        payload: Dict[str, Any] = dict(self.extra_fields)
        payload[self.username_field] = self.username
        payload[self.password_field] = self.password

        # Inject CSRF token into login request
        if isinstance(self.csrf_protection, CSRFProtection):
            headers, payload = self.csrf_protection.inject_token(
                headers=headers,
                data=payload,
                method='POST',
                context=context
            )

        try:
            if self.content_type == "form":
                resp = self._session.post(
                    self.login_url,
                    data=payload,
                    headers=headers or None,
                    timeout=15
                )
            else:
                resp = self._session.post(
                    self.login_url,
                    json=payload,
                    headers=headers or None,
                    timeout=15
                )
            # try json; raise on non-2xx to surface errors
            resp.raise_for_status()
        except Exception as e:
            raise AuthenticationError(f"Login request failed: {e}", self.name)

        # Extract updated CSRF token from response if auto-extraction enabled
        if isinstance(self.csrf_protection, CSRFProtection) and self.csrf_protection.auto_extract:
            self.csrf_protection.extract_token(
                response=resp,
                session=self._session,
                context=context
            )

        # Extract token from either response cookies or JSON body
        token = None
        if self.jwt_source == "cookie":
            # Extract from response cookies
            token = resp.cookies.get(self.cookie_name)
            if not token or not isinstance(token, str):
                raise AuthenticationError(
                    f"JWT cookie '{self.cookie_name}' not found in login response",
                    self.name,
                )
        else:
            # Extract from JSON response body
            try:
                data = resp.json()
            except Exception as e:
                raise AuthenticationError(f"Failed to parse JSON response: {e}", self.name)
            token = _extract_by_dot_path(data, self.jwt_json_path)
            if not token or not isinstance(token, str):
                raise AuthenticationError(
                    f"JWT not found at path '{self.jwt_json_path}' in login response",
                    self.name,
                )

        self.token = token
        self.store_auth_data('jwt', token)
        self.store_auth_data('login_time', time.time())
        return token

    def get_auth_cookies(self) -> Dict[str, str]:
        """
        Return cookie mapping for API mode. Will perform login if token absent.
        """
        if not self.token:
            self._login_and_get_token()
        if not self.token:
            return {}
        return {self.cookie_name: self.token}

    def get_auth_headers(self) -> Dict[str, str]:
        """
        For this hybrid approach, we typically do not use auth headers.
        """
        return {}

    def authenticate(self, driver: WebDriver, target_url: str) -> bool:
        """
        UI path: ensure the cookie exists on the browser for the target domain.
        Will perform the API login if token not yet acquired.
        """
        try:
            if not self.token:
                self._login_and_get_token()
            if not self.token:
                return False
            # Navigate to the target domain base so cookie domain matches
            parsed = urlparse(target_url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            try:
                driver.get(base)
            except Exception:
                pass
            cookie_dict = {
                'name': self.cookie_name,
                'value': self.token,
                'path': '/',
            }
            # If domain available, set explicitly to be safe
            if parsed.netloc:
                cookie_dict['domain'] = parsed.hostname or parsed.netloc
            driver.add_cookie(cookie_dict)
            self.authenticated = True
            return True
        except Exception as e:
            raise AuthenticationError(f"Cookie auth failed: {e}", self.name)

    def is_authenticated(self, driver: WebDriver) -> bool:
        return self.authenticated and self.token is not None

    def logout(self, driver: WebDriver) -> bool:
        try:
            self.token = None
            self.authenticated = False
            self.clear_auth_data()
            # Best-effort cookie removal
            try:
                driver.delete_cookie(self.cookie_name)
            except Exception:
                pass
            super().logout(driver)
            return True
        except Exception:
            return False
