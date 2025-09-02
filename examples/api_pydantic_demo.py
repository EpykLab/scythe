#!/usr/bin/env python3
"""
Example: Using ApiRequestAction with a Pydantic response model.

Prerequisites:
- An HTTP endpoint to call (see examples/test_server_with_version.py for a quick demo server)
- Pydantic installed (already pinned in requirements.txt)

Usage:
    # Optional: start the demo server that sets the version header
    #   python examples/test_server_with_version.py 8080 1.2.3
    # Then run this example (in API mode, no browser):
    #   python examples/api_pydantic_demo.py
"""
from __future__ import annotations

from pydantic import BaseModel

from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import ApiRequestAction
from scythe.journeys.executor import JourneyExecutor


class Health(BaseModel):
    status: str
    version: str | None = None


def build_journey() -> Journey:
    step = Step(
        name="API Health (Schema)",
        description="GET /api/health should return 200 and valid schema",
        actions=[
            ApiRequestAction(
                method="GET",
                url="/api/health",
                expected_status=200,
                response_model=Health,
                response_model_context_key="health_model",
                fail_on_validation_error=True,
            )
        ],
        continue_on_failure=False,
        expected_result=True,
    )

    return Journey(
        name="API Schema Smoke",
        description="Validate API health schema with Pydantic",
        steps=[step],
        expected_result=True,
    )


def main():
    target_url = "http://localhost:8080"  # adjust for your API base URL
    journey = build_journey()

    executor = JourneyExecutor(
        journey=journey,
        target_url=target_url,
        mode="API",  # No browser launched
    )

    results = executor.run()

    print("=== API Pydantic Demo Summary ===")
    print(f"Journey: {results.get('journey_name')}")
    print(f"Overall Success: {results.get('overall_success')}")
    step_results = results.get('step_results') or []
    if step_results:
        first_actions = step_results[0].get('actions') or []
        if first_actions:
            action_data = first_actions[0]
            print(f"Action '{action_data.get('action_name')}' success: {action_data.get('actual')}")


if __name__ == "__main__":
    main()
