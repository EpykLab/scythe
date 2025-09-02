import unittest
from typing import Any, Dict, Optional

from scythe.journeys.actions import ApiRequestAction


class _FakeResponse:
    def __init__(self, status_code: int = 200, headers: Optional[Dict[str, str]] = None, json_body: Optional[Dict[str, Any]] = None, text: str = ""):
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
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.headers: Dict[str, str] = {}

    def request(self, method, url, params=None, json=None, data=None, headers=None, timeout=None):
        # emulate minimal requests.Session.request
        return self._response


# Fake Pydantic-like models to avoid external imports
class FakeModelV2:
    def __init__(self, status: str, version: Optional[str] = None):
        self.status = status
        self.version = version

    @classmethod
    def model_validate(cls, data: Dict[str, Any]) -> "FakeModelV2":
        # Minimal validation: require 'status'
        if not isinstance(data, dict) or "status" not in data or not isinstance(data["status"], str):
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
        if not isinstance(data, dict) or "status" not in data or not isinstance(data["status"], str):
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


if __name__ == "__main__":
    unittest.main()
