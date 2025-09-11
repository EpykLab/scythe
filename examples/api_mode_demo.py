#!/usr/bin/env python3
"""
Example: Running a Journey in API mode using ApiRequestAction.

Prerequisites:
- An HTTP endpoint to call (for quick local testing you can use examples/test_server_with_version.py)

Usage:
    # In one terminal (optional helper server):
    # python examples/test_server_with_version.py 8080 1.2.3
    # In another terminal, run this demo:
    # python examples/api_mode_demo.py

This example performs a simple GET to /api/health on the target and prints the
journey results summary. No browser is launched in API mode.
"""
from __future__ import annotations

from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import ApiRequestAction
from scythe.journeys.executor import JourneyExecutor


def build_journey() -> Journey:
    step = Step(
        name="API Health",
        description="GET /api/health should return 200",
        actions=[
            ApiRequestAction(method="GET", url="/api/health", expected_status=200)
        ],
        continue_on_failure=False,
        expected_result=True,
    )

    journey = Journey(
        name="API Smoke",
        description="Simple API smoke check using requests",
        steps=[step],
        expected_result=True,
        # authentication=BearerTokenAuth(token="YOUR_TOKEN_HERE")  # optional
    )
    return journey


def main():
    target_url = "http://localhost:8080"  # adjust for your API base URL
    journey = build_journey()

    executor = JourneyExecutor(
        journey=journey,
        target_url=target_url,
        mode="API",  # key: use API mode to avoid launching a browser
    )

    results = executor.run()

    print("=== API Mode Demo Summary ===")
    print(f"Journey: {results.get('journey_name')}")
    print(f"Overall Success: {results.get('overall_success')}")
    print(f"Steps: {results.get('steps_succeeded')}/{results.get('steps_executed')} succeeded")
    print(f"Actions: {results.get('actions_succeeded')}/{results.get('actions_executed')} succeeded")
    tv = results.get('target_versions')
    if tv:
        print(f"Detected target versions: {list(set(tv))}")
    else:
        print("No X-SCYTHE-TARGET-VERSION headers detected.")


if __name__ == "__main__":
    main()
