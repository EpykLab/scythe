#!/usr/bin/env python3
"""Debug script to check exit code behavior"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from scythe.journeys import ApiRequestAction
from scythe.journeys import JourneyExecutor
from scythe.journeys import Journey, Step

# Create a simple test that WILL fail
journey = Journey(
    name="test routes",
    description="test routes",
    steps=[
        Step(
            name="Test route expecting 401",
            description="test route expecting 401",
            actions=[
                ApiRequestAction(
                    method="GET",
                    url="/status/200",  # This returns 200, not 401
                    expected_status=401,  # We expect 401
                    expected_result=True  # We expect the action to succeed (get 401)
                ),
            ],
        )
    ])

executor = JourneyExecutor(
    journey=journey,
    mode="API",
    target_url="https://httpbin.org")

print("\n" + "="*60)
print("BEFORE executor.run()")
print("="*60)

result = executor.run()

print("\n" + "="*60)
print("AFTER executor.run()")
print("="*60)
print(f"result type: {type(result)}")
print(f"result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
print(f"overall_success: {result.get('overall_success') if isinstance(result, dict) else 'N/A'}")
print(f"expected_result: {result.get('expected_result') if isinstance(result, dict) else 'N/A'}")
print(f"steps_failed: {result.get('steps_failed') if isinstance(result, dict) else 'N/A'}")
print(f"steps_succeeded: {result.get('steps_succeeded') if isinstance(result, dict) else 'N/A'}")
print()
print(f"executor.was_successful(): {executor.was_successful()}")
print(f"executor.exit_code(): {executor.exit_code()}")
print("="*60)

exit_code = executor.exit_code()
print(f"\nAbout to call sys.exit({exit_code})")
sys.exit(exit_code)
