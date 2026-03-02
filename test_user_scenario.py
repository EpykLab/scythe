#!/usr/bin/env python3
"""Test the user's actual scenario to debug the exit code issue."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from scythe.journeys import ApiRequestAction
from scythe.journeys import JourneyExecutor
from scythe.journeys import Journey, Step


def main() -> int:
    # Simulate a failing API request
    journey = Journey(
        name="test API routes",
        description="test API routes",
        steps=[
            Step(
                name="Test routes that should return 401",
                description="tests routes expecting 401",
                actions=[
                    ApiRequestAction(
                        method="GET",
                        url="/api/v1/auth/me",
                        expected_status=401,
                        expected_result=True,
                    ),
                ],
            )
        ],
    )

    executor = JourneyExecutor(
        journey=journey,
        mode="API",
        target_url="https://httpbin.org",
    )

    result = executor.run()

    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"overall_success: {result.get('overall_success')}")
    print(f"expected_result: {result.get('expected_result')}")
    print(f"steps_failed: {result.get('steps_failed')}")
    print(f"steps_succeeded: {result.get('steps_succeeded')}")
    print(f"was_successful(): {executor.was_successful()}")
    print(f"exit_code(): {executor.exit_code()}")
    print("=" * 60)

    return executor.exit_code()


if __name__ == "__main__":
    sys.exit(main())
