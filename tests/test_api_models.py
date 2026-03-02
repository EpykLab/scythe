import unittest
from typing import Any, Dict, Optional

from scythe.journeys.actions import ApiRequestAction


class _FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        text: str = "",
    ):
        self.status_code = status_code
        self.headers = headers or {}
        self._json = json_body
        self.text = text

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> Dict[str, Any]:
        if self._json is None:
            raise ValueError("No JSON body")
        return self._json


class _FakeSession:
    def __init__(
        self,
        response: _FakeResponse | None = None,
        responses: Optional[list[_FakeResponse]] = None,
    ):
        self._response = response
        self._responses = list(responses or [])
        self.headers: Dict[str, str] = {}
        self.calls = []

    def request(
        self, method, url, params=None, json=None, data=None, headers=None, timeout=None
    ):
        # emulate minimal requests.Session.request
        self.calls.append(
            {
                "method": method,
                "url": url,
                "params": params,
                "json": json,
                "data": data,
                "headers": headers,
                "timeout": timeout,
            }
        )
        if self._responses:
            return self._responses.pop(0)
        return self._response


# Fake Pydantic-like models to avoid external imports
class FakeModelV2:
    def __init__(self, status: str, version: Optional[str] = None):
        self.status = status
        self.version = version

    @classmethod
    def model_validate(cls, data: Dict[str, Any]) -> "FakeModelV2":
        # Minimal validation: require 'status'
        if (
            not isinstance(data, dict)
            or "status" not in data
            or not isinstance(data["status"], str)
        ):
            raise ValueError("Invalid data for FakeModelV2: missing 'status' as str")
        version = data.get("version")
        if version is not None and not isinstance(version, str):
            raise ValueError("Invalid 'version' type")
        return cls(status=data["status"], version=version)


class FakeModelV1:
    def __init__(self, status: str):
        self.status = status

    @classmethod
    def parse_obj(cls, data: Dict[str, Any]) -> "FakeModelV1":
        if (
            not isinstance(data, dict)
            or "status" not in data
            or not isinstance(data["status"], str)
        ):
            raise ValueError("Invalid data for FakeModelV1: missing 'status' as str")
        return cls(status=data["status"])


class TestApiRequestActionModels(unittest.TestCase):
    def test_valid_json_parses_into_model_v2(self):
        fake_resp = _FakeResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            json_body={"status": "ok", "version": "1.2.3"},
        )
        session = _FakeSession(fake_resp)

        action = ApiRequestAction(
            method="GET",
            url="/api/health",
            expected_status=200,
            response_model=FakeModelV2,
            response_model_context_key="health_model",
        )
        context: Dict[str, Any] = {
            "target_url": "http://localhost:8080",
            "requests_session": session,
        }

        result = action.execute(driver=None, context=context)

        self.assertTrue(result)
        # Model instance stored
        model_instance = action.get_result("response_model_instance")
        self.assertIsNotNone(model_instance)
        self.assertIsInstance(model_instance, FakeModelV2)
        self.assertEqual(model_instance.status, "ok")
        # Context updated with model
        self.assertIn("health_model", context)
        self.assertIsInstance(context["health_model"], FakeModelV2)
        # No validation error recorded
        self.assertIsNone(action.get_result("response_validation_error"))

    def test_invalid_json_records_error_and_can_fail_v1(self):
        fake_resp = _FakeResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            json_body={"wrong": "shape"},
        )
        session = _FakeSession(fake_resp)

        action = ApiRequestAction(
            method="GET",
            url="/api/health",
            expected_status=200,
            response_model=FakeModelV1,  # triggers parse_obj path
            fail_on_validation_error=True,
        )
        context: Dict[str, Any] = {
            "target_url": "http://localhost:8080",
            "requests_session": session,
        }

        result = action.execute(driver=None, context=context)

        # HTTP status would normally be success, but validation error should force failure
        self.assertFalse(result)
        self.assertIsNone(action.get_result("response_model_instance"))
        self.assertIsNotNone(action.get_result("response_validation_error"))

    def test_action_data_not_mutated_after_csrf_injection(self):
        class _NoopCsrf:
            auto_extract = False

            def inject_token(self, headers, data, method, context):
                copied = dict(data or {})
                copied["csrf"] = "token"
                return {**(headers or {}), "X-CSRF-Token": "token"}, copied

        action = ApiRequestAction(
            method="POST",
            url="/api/items",
            data={"name": "alice"},
            expected_status=200,
        )
        context: Dict[str, Any] = {
            "target_url": "http://localhost:8080",
            "csrf_protection": _NoopCsrf(),
            "requests_session": _FakeSession(
                _FakeResponse(status_code=200, json_body={"status": "ok"})
            ),
        }

        self.assertTrue(action.execute(driver=None, context=context))
        self.assertEqual(action.data, {"name": "alice"})

    def test_retry_metadata_is_recorded_for_429(self):
        responses = [
            _FakeResponse(
                status_code=429,
                headers={"Retry-After": "1"},
                json_body={"status": "retry"},
            ),
            _FakeResponse(status_code=200, headers={}, json_body={"status": "ok"}),
        ]
        session = _FakeSession(responses=responses)
        action = ApiRequestAction(
            method="GET",
            url="/api/health",
            expected_status=200,
        )
        context: Dict[str, Any] = {
            "target_url": "http://localhost:8080",
            "requests_session": session,
            "_time_fn": lambda: 1000.0,
            "_sleep_fn": lambda _s: None,
        }

        self.assertTrue(action.execute(driver=None, context=context))
        self.assertEqual(action.get_result("attempt_count"), 2)
        self.assertEqual(action.get_result("retry_reason"), "http_429")
        self.assertEqual(action.get_result("retry_wait_s"), 1)

    def test_expected_json_paths_exact_and_exists(self):
        fake_resp = _FakeResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            json_body={
                "data": {
                    "status": "ok",
                    "user": {"email": "user@example.com"},
                }
            },
        )
        session = _FakeSession(fake_resp)

        action = ApiRequestAction(
            method="GET",
            url="/api/me",
            expected_status=200,
            expected_json_paths={
                "data.status": "ok",
                "data.user.email": "__exists__",
            },
        )
        context: Dict[str, Any] = {
            "target_url": "http://localhost:8080",
            "requests_session": session,
        }

        result = action.execute(driver=None, context=context)

        self.assertTrue(result)
        self.assertTrue(action.get_result("json_paths_ok"))
        self.assertTrue(action.get_result("api_assertions_ok"))

    def test_expected_json_paths_fail_when_missing(self):
        fake_resp = _FakeResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            json_body={"data": {"status": "ok"}},
        )
        session = _FakeSession(fake_resp)

        action = ApiRequestAction(
            method="GET",
            url="/api/me",
            expected_status=200,
            expected_json_paths={"data.user.email": "__exists__"},
        )
        context: Dict[str, Any] = {
            "target_url": "http://localhost:8080",
            "requests_session": session,
        }

        result = action.execute(driver=None, context=context)

        self.assertFalse(result)
        self.assertFalse(action.get_result("json_paths_ok"))
        self.assertFalse(action.get_result("api_assertions_ok"))


if __name__ == "__main__":
    unittest.main()
