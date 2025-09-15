from __future__ import annotations

import time
from typing import Dict, Optional, Any
from urllib.parse import urlparse

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover - tests may run without requests installed
    requests = None  # type: ignore
from selenium.webdriver.remote.webdriver import WebDriver

from .base import Authentication, AuthenticationError


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
      perform a POST to login_url (if token not cached), parse JSON, extract the
      token via jwt_json_path, and return {cookie_name: token}.
    - In UI mode: authenticate() will ensure the browser has the cookie set for
      the target domain.
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
                 session: Optional[requests.Session] = None,
                 description: str = "Authenticate via API and set JWT cookie"):
        super().__init__(
            name="Cookie JWT Authentication",
            description=description
        )
        self.login_url = login_url
        self.username = username
        self.password = password
        self.username_field = username_field
        self.password_field = password_field
        self.extra_fields = extra_fields or {}
        self.jwt_json_path = jwt_json_path
        self.cookie_name = cookie_name
        # Avoid importing requests in test environments; allow injected session
        self._session = session or (requests.Session() if requests is not None else None)
        self.token: Optional[str] = None

    def _login_and_get_token(self) -> str:
        payload: Dict[str, Any] = dict(self.extra_fields)
        if self.username is not None:
            payload[self.username_field] = self.username
        if self.password is not None:
            payload[self.password_field] = self.password
        try:
            resp = self._session.post(self.login_url, json=payload, timeout=15)
            # try json; raise on non-2xx to surface errors
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            raise AuthenticationError(f"Login request failed: {e}", self.name)
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
