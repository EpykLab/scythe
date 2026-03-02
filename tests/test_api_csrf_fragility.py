import unittest
from unittest.mock import MagicMock, Mock

from scythe.core.csrf import CSRFProtection
from scythe.journeys.actions import ApiRequestAction


class TestApiRequestCSRFFragility(unittest.TestCase):
    def test_retry_flag_is_respected(self):
        csrf = CSRFProtection(retry_on_failure=False)
        response = Mock()
        response.status_code = 403

        self.assertFalse(
            csrf.should_retry(response),
            "retry_on_failure=False should disable CSRF retries",
        )

    def test_csrf_retry_still_works_when_rate_limit_logic_disabled(self):
        csrf = CSRFProtection(cookie_name="csrftoken", header_name="X-CSRF-Token")

        mock_session = MagicMock()

        first_response = Mock()
        first_response.status_code = 403
        first_response.headers = {}
        first_response.cookies = {}
        first_response.json.return_value = {"error": "csrf failed"}

        refresh_response = Mock()
        refresh_response.status_code = 200
        refresh_response.headers = {}
        refresh_response.cookies = {"csrftoken": "refreshed-token"}
        refresh_response.raise_for_status = Mock()

        second_response = Mock()
        second_response.status_code = 200
        second_response.headers = {}
        second_response.cookies = {}
        second_response.json.return_value = {"ok": True}

        mock_session.request.side_effect = [first_response, second_response]
        mock_session.get.return_value = refresh_response
        mock_session.cookies = MagicMock()
        mock_session.cookies.get.return_value = "refreshed-token"

        context = {
            "target_url": "https://example.com",
            "requests_session": mock_session,
            "csrf_protection": csrf,
            "csrf_token": "initial-token",
        }

        action = ApiRequestAction(
            method="POST",
            url="/api/items",
            body_json={"name": "item"},
            expected_status=200,
            honor_rate_limit=False,
        )

        result = action.execute(Mock(), context)

        self.assertTrue(result)
        self.assertEqual(mock_session.request.call_count, 2)
        retried_headers = mock_session.request.call_args_list[1][1]["headers"]
        self.assertEqual(retried_headers["X-CSRF-Token"], "refreshed-token")

    def test_body_injection_augments_json_payload_not_form_data(self):
        csrf = CSRFProtection(inject_into="body", body_field="csrfToken")

        mock_session = MagicMock()
        response = Mock()
        response.status_code = 200
        response.headers = {}
        response.cookies = {}
        response.json.return_value = {"ok": True}
        mock_session.request.return_value = response

        context = {
            "target_url": "https://example.com",
            "requests_session": mock_session,
            "csrf_protection": csrf,
            "csrf_token": "body-token",
        }

        action = ApiRequestAction(
            method="POST",
            url="/api/items",
            body_json={"name": "item"},
            expected_status=200,
        )

        self.assertTrue(action.execute(Mock(), context))

        req_kwargs = mock_session.request.call_args[1]
        self.assertIsNone(req_kwargs["data"])
        self.assertEqual(req_kwargs["json"]["name"], "item")
        self.assertEqual(req_kwargs["json"]["csrfToken"], "body-token")


if __name__ == "__main__":
    unittest.main()
