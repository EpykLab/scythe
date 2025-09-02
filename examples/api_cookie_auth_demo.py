#!/usr/bin/env python3
"""
Example: API mode with hybrid cookie-based authentication (CookieJWTAuth).

This demonstrates logging into an API to obtain a JWT and setting it as a
cookie (default name 'stellarbridge') for subsequent requests in API mode.

Prerequisites:
- A login endpoint (e.g., POST /api/login) that returns a JSON payload with a
  JWT at a known JSON path (e.g., auth.jwt).
- A protected endpoint (e.g., GET /api/profile) that relies on the cookie.

Usage:
    python examples/api_cookie_auth_demo.py

Note: Adjust URLs and field names for your application.
"""
from __future__ import annotations

from scythe.auth import CookieJWTAuth
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import ApiRequestAction
from scythe.journeys.executor import JourneyExecutor


def build_journey() -> Journey:
    # Step 1: call a protected endpoint which should succeed after cookie auth
    step = Step(
        name="Profile",
        description="GET /api/profile returns 200 when cookie auth is set",
        actions=[
            ApiRequestAction(method="GET", url="/api/profile", expected_status=200)
        ],
        continue_on_failure=False,
        expected_result=True,
    )

    auth = CookieJWTAuth(
        login_url="http://localhost:8080/api/login",  # change to your login URL
        username="user@example.com",
        password="secret",
        username_field="email",  # or "username" if your API uses that
        password_field="password",
        jwt_json_path="auth.jwt",  # dot path to the token in the login response
        cookie_name="stellarbridge",  # cookie name your app expects
    )

    return Journey(
        name="Cookie Auth API Journey",
        description="Login via API and set JWT cookie for subsequent requests",
        steps=[step],
        expected_result=True,
        authentication=auth,
    )


def main():
    target_url = "http://localhost:8080"  # API base URL
    journey = build_journey()

    executor = JourneyExecutor(
        journey=journey,
        target_url=target_url,
        mode="API",  # Use API mode, no browser launched
    )

    results = executor.run()

    print("=== API Cookie Auth Demo Summary ===")
    print(f"Overall Success: {results.get('overall_success')}")
    print(f"Steps: {results.get('steps_succeeded')}/{results.get('steps_executed')} succeeded")


if __name__ == "__main__":
    main()
