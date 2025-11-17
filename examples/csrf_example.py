"""
Example: Using CSRF Protection in Scythe

This example demonstrates how to configure CSRF protection for testing
web applications that require CSRF tokens with API requests.
"""

from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import ApiRequestAction
from scythe.core.csrf import CSRFProtection
from scythe.journeys.executor import JourneyExecutor


# Example 1: Django Application
def example_django():
    """Example for Django applications (csrftoken cookie -> X-CSRFToken header)"""

    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='csrftoken',
        header_name='X-CSRFToken',
        inject_into='header'
    )

    journey = Journey(
        name="Django API Test",
        description="Test Django app with CSRF",
        csrf_protection=csrf
    )

    # Step 1: GET request extracts CSRF token from cookie
    step1 = Step(
        name="Get initial page",
        description="Extract CSRF token",
        actions=[
            ApiRequestAction(
                method='GET',
                url='/api/items/',
                expected_status=200
            )
        ]
    )

    # Step 2: POST request automatically includes CSRF token
    step2 = Step(
        name="Create item",
        description="POST with CSRF token",
        actions=[
            ApiRequestAction(
                method='POST',
                url='/api/items/',
                body_json={
                    'name': 'Test Item',
                    'description': 'Created via Scythe'
                },
                expected_status=201
            )
        ]
    )

    journey.add_step(step1)
    journey.add_step(step2)

    executor = JourneyExecutor(
        journey=journey,
        target_url='https://your-django-app.com',
        mode='API'
    )

    executor.run()


# Example 2: Laravel Application
def example_laravel():
    """Example for Laravel applications (XSRF-TOKEN cookie -> X-XSRF-TOKEN header)"""

    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='XSRF-TOKEN',
        header_name='X-XSRF-TOKEN',
        inject_into='header'
    )

    journey = Journey(
        name="Laravel API Test",
        description="Test Laravel app with CSRF",
        csrf_protection=csrf
    )

    journey.add_step(Step(
        name="Update user",
        actions=[
            ApiRequestAction(
                method='PUT',
                url='/api/users/123',
                body_json={'name': 'Updated Name'},
                expected_status=200
            )
        ]
    ))

    executor = JourneyExecutor(
        journey=journey,
        target_url='https://your-laravel-app.com',
        mode='API'
    )

    executor.run()


# Example 3: Custom Application with Token in Response Header
def example_custom_header():
    """Example for custom apps that return CSRF token in response header"""

    csrf = CSRFProtection(
        extract_from='header',           # Token comes from response header
        header_name='X-CSRF-Token',      # Header name for both extract and inject
        inject_into='header'
    )

    journey = Journey(
        name="Custom API Test",
        description="Test custom app with header-based CSRF",
        csrf_protection=csrf
    )

    journey.add_step(Step(
        name="Create resource",
        actions=[
            ApiRequestAction(
                method='POST',
                url='/api/resources',
                body_json={'data': 'test'},
                expected_status=201
            )
        ]
    ))

    executor = JourneyExecutor(
        journey=journey,
        target_url='https://your-custom-app.com',
        mode='API'
    )

    executor.run()


# Example 4: Token from JSON Response Body
def example_json_token():
    """Example for apps that return CSRF token in JSON response body"""

    csrf = CSRFProtection(
        extract_from='body',             # Token in response JSON
        body_field='csrfToken',          # JSON field name
        header_name='X-CSRF-Token',      # Header to send it in
        inject_into='header'
    )

    journey = Journey(
        name="JSON Token Test",
        description="Test app with JSON CSRF token",
        csrf_protection=csrf
    )

    # First request to get the token from JSON response
    journey.add_step(Step(
        name="Get token",
        actions=[
            ApiRequestAction(
                method='GET',
                url='/api/csrf',
                expected_status=200
            )
        ]
    ))

    # Subsequent request uses the extracted token
    journey.add_step(Step(
        name="Use token",
        actions=[
            ApiRequestAction(
                method='POST',
                url='/api/data',
                body_json={'value': 'test'},
                expected_status=201
            )
        ]
    ))

    executor = JourneyExecutor(
        journey=journey,
        target_url='https://your-app.com',
        mode='API'
    )

    executor.run()


# Example 5: Automatic Retry Without Dedicated Refresh Endpoint
def example_automatic_retry():
    """
    Example showing automatic retry when API updates CSRF cookie with every response.
    This is the most common scenario - no refresh_endpoint needed!
    """

    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='__Host-csrf_',
        header_name='X-CSRF-Token',
        inject_into='header'
        # No refresh_endpoint! Scythe will automatically:
        # 1. Hit the base URL on 403/419 errors
        # 2. Extract the fresh CSRF cookie
        # 3. Retry the failed request
    )

    journey = Journey(
        name="CSRF with Auto-Refresh",
        description="Test with automatic CSRF token refresh",
        csrf_protection=csrf
    )

    journey.add_step(Step(
        name="Protected action",
        actions=[
            ApiRequestAction(
                method='DELETE',
                url='/api/items/456',
                expected_status=204
            )
        ]
    ))

    executor = JourneyExecutor(
        journey=journey,
        target_url='https://your-app.com',
        mode='API'
    )

    executor.run()


# Example 6: With Dedicated Refresh Endpoint
def example_with_refresh_endpoint():
    """Example with a dedicated CSRF refresh endpoint"""

    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='csrftoken',
        header_name='X-CSRFToken',
        inject_into='header',
        refresh_endpoint='/api/csrf-token'  # Use this specific endpoint for refresh
    )

    journey = Journey(
        name="CSRF with Dedicated Refresh Endpoint",
        description="Test with custom refresh endpoint",
        csrf_protection=csrf
    )

    journey.add_step(Step(
        name="Protected action",
        actions=[
            ApiRequestAction(
                method='DELETE',
                url='/api/items/456',
                expected_status=204
            )
        ]
    ))

    executor = JourneyExecutor(
        journey=journey,
        target_url='https://your-app.com',
        mode='API'
    )

    executor.run()


# Example 7: Request Flooding TTP with CSRF
def example_request_flooding_with_csrf():
    """Example: Testing rate limiting with CSRF-protected endpoints"""

    from scythe.ttps.web.request_flooding import RequestFloodingTTP
    from scythe.core.executor import TTPExecutor

    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='XSRF-TOKEN',
        header_name='X-XSRF-TOKEN'
    )

    ttp = RequestFloodingTTP(
        target_endpoints=['/api/search'],
        request_count=100,
        requests_per_second=10,
        http_method='POST',
        payload_data={'query': 'test'},
        expected_result=False,  # Expect rate limiting to kick in
        execution_mode='api',
        csrf_protection=csrf
    )

    executor = TTPExecutor(
        ttp=ttp,
        target_url='https://your-app.com'
    )

    executor.run()


if __name__ == '__main__':
    print("CSRF Protection Examples")
    print("========================\n")
    print("Uncomment the example you want to run:\n")

    # Uncomment one of these to run:
    # example_django()
    # example_laravel()
    # example_custom_header()
    # example_json_token()
    # example_automatic_retry()           # Most common - no refresh endpoint needed!
    # example_with_refresh_endpoint()     # If you have a dedicated refresh endpoint
    # example_request_flooding_with_csrf()

    print("Please edit this file and uncomment an example to run it.")
