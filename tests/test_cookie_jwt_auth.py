import unittest
from unittest.mock import Mock, patch
from typing import Any, Dict, Optional
import sys
import types

# Provide minimal shims if dependencies are not installed
# requests shim
if 'requests' not in sys.modules:
    requests_mod = types.ModuleType('requests')
    class _Session:
        pass
    requests_mod.Session = _Session
    sys.modules['requests'] = requests_mod

# Provide a minimal selenium shim if selenium is not installed
if 'selenium' not in sys.modules:
    selenium_mod = types.ModuleType('selenium')
    webdriver_mod = types.ModuleType('selenium.webdriver')
    chrome_mod = types.ModuleType('selenium.webdriver.chrome')
    options_mod = types.ModuleType('selenium.webdriver.chrome.options')
    remote_mod = types.ModuleType('selenium.webdriver.remote')
    remote_webdriver_mod = types.ModuleType('selenium.webdriver.remote.webdriver')
    common_mod = types.ModuleType('selenium.webdriver.common')
    common_by_mod = types.ModuleType('selenium.webdriver.common.by')
    selenium_common_mod = types.ModuleType('selenium.common')
    selenium_common_ex_mod = types.ModuleType('selenium.common.exceptions')
    support_mod = types.ModuleType('selenium.webdriver.support')
    support_ui_mod = types.ModuleType('selenium.webdriver.support.ui')
    support_ec_mod = types.ModuleType('selenium.webdriver.support.expected_conditions')

    class _Options:  # placeholder Options
        def __init__(self):
            pass
    options_mod.Options = _Options

    class _WebDriver:  # minimal placeholder to satisfy type import
        pass
    remote_webdriver_mod.WebDriver = _WebDriver

    class _By:
        ID = 'id'
        XPATH = 'xpath'
        CSS_SELECTOR = 'css selector'
        NAME = 'name'
        CLASS_NAME = 'class name'
        TAG_NAME = 'tag name'
    common_by_mod.By = _By

    class _NoSuchElementException(Exception):
        pass
    class _TimeoutException(Exception):
        pass
    selenium_common_ex_mod.NoSuchElementException = _NoSuchElementException
    selenium_common_ex_mod.TimeoutException = _TimeoutException

    # Dummy expected conditions and WebDriverWait
    class _EC:
        @staticmethod
        def element_to_be_clickable(locator):
            return True
    support_ec_mod = types.ModuleType('selenium.webdriver.support.expected_conditions')
    support_ec_mod.element_to_be_clickable = _EC.element_to_be_clickable

    class _WebDriverWait:
        def __init__(self, driver, timeout):
            pass
        def until(self, method):
            return Mock()
    support_ui_mod = types.ModuleType('selenium.webdriver.support.ui')
    support_ui_mod.WebDriverWait = _WebDriverWait
    support_mod = types.ModuleType('selenium.webdriver.support')

    sys.modules['selenium'] = selenium_mod
    sys.modules['selenium.webdriver'] = webdriver_mod
    sys.modules['selenium.webdriver.chrome'] = chrome_mod
    sys.modules['selenium.webdriver.chrome.options'] = options_mod
    sys.modules['selenium.webdriver.remote'] = remote_mod
    sys.modules['selenium.webdriver.remote.webdriver'] = remote_webdriver_mod
    sys.modules['selenium.webdriver.common'] = common_mod
    sys.modules['selenium.webdriver.common.by'] = common_by_mod
    sys.modules['selenium.webdriver.support'] = support_mod
    sys.modules['selenium.webdriver.support.ui'] = support_ui_mod
    sys.modules['selenium.webdriver.support.expected_conditions'] = support_ec_mod
    sys.modules['selenium.common'] = selenium_common_mod
    sys.modules['selenium.common.exceptions'] = selenium_common_ex_mod

from scythe.auth.cookie_jwt import CookieJWTAuth


class _FakeLoginResponse:
    def __init__(self, data: Dict[str, Any], status_code: int = 200):
        self._data = data
        self.status_code = status_code

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise RuntimeError("HTTP Error")

    def json(self):
        return self._data


class _FakeLoginSession:
    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def post(self, url, json=None, timeout=None):
        return _FakeLoginResponse(self._data, 200)


class _CookieJar:
    def __init__(self):
        self._cookies: Dict[str, str] = {}

    def set(self, key: str, value: str):
        self._cookies[key] = value

    def get(self, key: str, default=None):
        return self._cookies.get(key, default)


class _FakeRequestsSession:
    def __init__(self):
        self.headers: Dict[str, str] = {}
        self.cookies = _CookieJar()
        self._last_request: Dict[str, Any] = {}
        self._status: int = 200
        self._text: str = "ok"
        self._json: Optional[Dict[str, Any]] = None

    class _Resp:
        def __init__(self, status_code: int, headers: Dict[str, str], text: str, json_body: Optional[Dict[str, Any]]):
            self.status_code = status_code
            self.headers = headers
            self.text = text
            self._json = json_body

        @property
        def ok(self):
            return 200 <= self.status_code < 300

        def json(self):
            if self._json is None:
                raise ValueError("No JSON body")
            return self._json

    def request(self, method, url, params=None, json=None, data=None, headers=None, timeout=None):
        # Record request for assertions
        self._last_request = {
            'method': method,
            'url': url,
            'headers': headers or {},
            'params': params or {},
            'json': json,
            'data': data,
        }
        return self._Resp(self._status, {}, self._text, self._json)


class TestCookieJWTAuth(unittest.TestCase):
    def test_get_auth_cookies_via_login(self):
        fake_login = _FakeLoginSession({"auth": {"jwt": "ABC123"}})
        auth = CookieJWTAuth(
            login_url="http://api.example.com/login",
            username="user@example.com",
            password="secret",
            username_field="email",
            password_field="password",
            jwt_json_path="auth.jwt",
            cookie_name="stellarbridge",
            session=fake_login,
        )

        cookies = auth.get_auth_cookies()
        self.assertEqual(cookies, {"stellarbridge": "ABC123"})
        self.assertEqual(auth.token, "ABC123")
        self.assertEqual(auth.get_auth_headers(), {})

    def test_ui_auth_sets_browser_cookie(self):
        fake_login = _FakeLoginSession({"token": "XYZ"})
        auth = CookieJWTAuth(
            login_url="http://api.example.com/login",
            username="user@example.com",
            password="secret",
            jwt_json_path="token",
            cookie_name="stellarbridge",
            session=fake_login,
        )
        driver = Mock()
        result = auth.authenticate(driver, target_url="http://app.example.com/protected")
        self.assertTrue(result)
        # add_cookie called with correct name and value
        called_args = driver.add_cookie.call_args[0][0]
        self.assertEqual(called_args["name"], "stellarbridge")
        self.assertEqual(called_args["value"], "XYZ")



if __name__ == "__main__":
    unittest.main()
