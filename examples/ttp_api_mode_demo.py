#!/usr/bin/env python3
"""
TTP API Mode Demo

This example demonstrates how to use TTPs in API mode to test security controls
without needing to go through the UI/Selenium layer. This is useful for:
1. Faster execution (no browser overhead)
2. Direct API testing
3. Better rate limiting control
4. Testing backend protections independently of UI

Demonstrates:
- Login bruteforce TTP in both UI and API modes
- SQL injection TTP in both UI and API modes
- How to configure API endpoints and payloads
- Rate limiting in API mode
"""

from scythe.payloads.generators import StaticPayloadGenerator
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.ttps.web.sql_injection import InputFieldInjector, URLManipulation
from scythe.journeys.base import Journey, Step
from scythe.journeys.actions import TTPAction, ApiRequestAction
from scythe.journeys.executor import JourneyExecutor


def login_bruteforce_ui_mode_example():
    """
    Example: Login bruteforce using UI mode (traditional Selenium approach)
    """
    print("\n" + "="*80)
    print("Example 1: Login Bruteforce - UI Mode")
    print("="*80)
    
    # Create payload generator with common passwords
    password_gen = StaticPayloadGenerator([
        'password123',
        'admin',
        'letmein',
        '123456'
    ])
    
    # Create TTP in UI mode (default)
    login_ttp = LoginBruteforceTTP(
        payload_generator=password_gen,
        username='admin',
        username_selector='input[name="username"]',
        password_selector='input[name="password"]',
        submit_selector='button[type="submit"]',
        expected_result=False,  # We expect rate limiting to prevent this
        execution_mode='ui'  # Explicitly set UI mode (this is the default)
    )
    
    # Create journey
    journey = Journey(
        name="Login Bruteforce Test - UI Mode",
        description="Test login bruteforce protection via UI"
    )
    
    step = Step(
        name="Bruteforce Login",
        description="Attempt to bruteforce login via UI"
    )
    
    step.add_action(TTPAction(
        ttp=login_ttp,
        target_url="http://localhost:8000/login"
    ))
    
    journey.add_step(step)
    
    # Execute
    executor = JourneyExecutor(journey, target_url="http://localhost:8000", headless=True)
    result = executor.execute()
    
    print(f"\nUI Mode Result: {'PASSED' if result else 'FAILED'}")
    return result


def login_bruteforce_api_mode_example():
    """
    Example: Login bruteforce using API mode (direct HTTP requests)
    Much faster than UI mode and can handle rate limiting better.
    """
    print("\n" + "="*80)
    print("Example 2: Login Bruteforce - API Mode")
    print("="*80)
    
    # Create payload generator with common passwords
    password_gen = StaticPayloadGenerator([
        'password123',
        'admin',
        'letmein',
        '123456',
        'welcome1'
    ])
    
    # Create TTP in API mode
    login_ttp = LoginBruteforceTTP(
        payload_generator=password_gen,
        username='admin',
        # UI selectors not needed for API mode
        execution_mode='api',
        # API-specific configuration
        api_endpoint='/api/auth/login',
        username_field='username',  # JSON field name for username
        password_field='password',  # JSON field name for password
        success_indicators={
            'status_code': 200,  # Successful login returns 200
            'response_contains': 'token',  # Response should contain a token
            'response_not_contains': 'invalid'  # Should not contain error message
        },
        expected_result=False  # We expect security controls to prevent success
    )
    
    # Create journey
    journey = Journey(
        name="Login Bruteforce Test - API Mode",
        description="Test login bruteforce protection via API"
    )
    
    step = Step(
        name="Bruteforce Login API",
        description="Attempt to bruteforce login via direct API calls"
    )
    
    step.add_action(TTPAction(
        ttp=login_ttp,
        target_url="http://localhost:8000"
    ))
    
    journey.add_step(step)
    
    # Execute in API mode
    executor = JourneyExecutor(
        journey, 
        target_url="http://localhost:8000",
        api_mode=True  # Enable API mode for the journey
    )
    result = executor.execute()
    
    print(f"\nAPI Mode Result: {'PASSED' if result else 'FAILED'}")
    return result


def sql_injection_ui_mode_example():
    """
    Example: SQL injection testing via UI form fields
    """
    print("\n" + "="*80)
    print("Example 3: SQL Injection - UI Mode")
    print("="*80)
    
    # SQL injection payloads
    sql_payloads = StaticPayloadGenerator([
        "' OR '1'='1",
        "' OR 1=1--",
        "admin'--",
        "' UNION SELECT NULL--"
    ])
    
    # Create TTP in UI mode
    sql_ttp = InputFieldInjector(
        target_url="http://localhost:8000/search",
        field_selector='input[name="query"]',
        submit_selector='button[type="submit"]',
        payload_generator=sql_payloads,
        expected_result=False,  # We expect input validation to prevent this
        execution_mode='ui'
    )
    
    # Create journey
    journey = Journey(
        name="SQL Injection Test - UI Mode",
        description="Test SQL injection protection via UI"
    )
    
    step = Step(
        name="SQL Injection via Form",
        description="Attempt SQL injection through search form"
    )
    
    step.add_action(TTPAction(
        ttp=sql_ttp,
        target_url="http://localhost:8000/search"
    ))
    
    journey.add_step(step)
    
    # Execute
    executor = JourneyExecutor(journey, target_url="http://localhost:8000", headless=True)
    result = executor.execute()
    
    print(f"\nUI Mode Result: {'PASSED' if result else 'FAILED'}")
    return result


def sql_injection_api_mode_example():
    """
    Example: SQL injection testing via direct API calls
    Faster and can test API-specific injection points.
    """
    print("\n" + "="*80)
    print("Example 4: SQL Injection - API Mode")
    print("="*80)
    
    # SQL injection payloads
    sql_payloads = StaticPayloadGenerator([
        "' OR '1'='1",
        "' OR 1=1--",
        "admin'--",
        "' UNION SELECT NULL--",
        "1; DROP TABLE users--"
    ])
    
    # Create TTP in API mode
    sql_ttp = InputFieldInjector(
        payload_generator=sql_payloads,
        expected_result=False,  # We expect input validation to prevent this
        execution_mode='api',
        # API-specific configuration
        api_endpoint='/api/search',
        injection_field='query',  # JSON field to inject payload into
        http_method='POST'  # HTTP method to use
    )
    
    # Create journey
    journey = Journey(
        name="SQL Injection Test - API Mode",
        description="Test SQL injection protection via API"
    )
    
    step = Step(
        name="SQL Injection via API",
        description="Attempt SQL injection through direct API calls"
    )
    
    step.add_action(TTPAction(
        ttp=sql_ttp,
        target_url="http://localhost:8000"
    ))
    
    journey.add_step(step)
    
    # Execute in API mode
    executor = JourneyExecutor(
        journey, 
        target_url="http://localhost:8000",
        api_mode=True
    )
    result = executor.execute()
    
    print(f"\nAPI Mode Result: {'PASSED' if result else 'FAILED'}")
    return result


def url_manipulation_api_mode_example():
    """
    Example: SQL injection via URL query parameters in API mode
    """
    print("\n" + "="*80)
    print("Example 5: SQL Injection via URL - API Mode")
    print("="*80)
    
    # SQL injection payloads
    sql_payloads = StaticPayloadGenerator([
        "' OR '1'='1",
        "1' OR '1'='1' --",
        "1 UNION SELECT NULL, NULL--"
    ])
    
    # Create TTP in API mode
    sql_ttp = URLManipulation(
        payload_generator=sql_payloads,
        expected_result=False,
        execution_mode='api',
        api_endpoint='/api/items',
        query_param='id'  # Query parameter to inject into
    )
    
    # Create journey
    journey = Journey(
        name="SQL Injection URL Test - API Mode",
        description="Test SQL injection in URL parameters via API"
    )
    
    step = Step(
        name="SQL Injection via URL Params",
        description="Attempt SQL injection through URL query parameters"
    )
    
    step.add_action(TTPAction(
        ttp=sql_ttp,
        target_url="http://localhost:8000"
    ))
    
    journey.add_step(step)
    
    # Execute in API mode
    executor = JourneyExecutor(
        journey, 
        target_url="http://localhost:8000",
        api_mode=True
    )
    result = executor.execute()
    
    print(f"\nAPI Mode Result: {'PASSED' if result else 'FAILED'}")
    return result


def mixed_mode_with_authentication_example():
    """
    Example: Using API mode with authentication
    Demonstrates how to authenticate and then run TTPs in API mode
    """
    print("\n" + "="*80)
    print("Example 6: API Mode with Authentication")
    print("="*80)
    
    # Create journey
    journey = Journey(
        name="Authenticated API Testing",
        description="Test with API authentication and TTPs"
    )
    
    # Step 1: Authenticate via API
    auth_step = Step(
        name="Authenticate",
        description="Get authentication token"
    )
    
    auth_step.add_action(ApiRequestAction(
        method='POST',
        url='/api/auth/login',
        body_json={
            'username': 'testuser',
            'password': 'testpass'
        },
        expected_status=200,
        name="Login to get token"
    ))
    
    journey.add_step(auth_step)
    
    # Step 2: Run bruteforce TTP in API mode (should fail due to auth)
    ttp_step = Step(
        name="Test with Auth",
        description="Attempt bruteforce with authentication"
    )
    
    password_gen = StaticPayloadGenerator(['wrong1', 'wrong2', 'wrong3'])
    
    login_ttp = LoginBruteforceTTP(
        payload_generator=password_gen,
        username='admin',
        execution_mode='api',
        api_endpoint='/api/auth/login',
        username_field='username',
        password_field='password',
        expected_result=False
    )
    
    ttp_step.add_action(TTPAction(
        ttp=login_ttp,
        target_url="http://localhost:8000"
    ))
    
    journey.add_step(ttp_step)
    
    # Execute in API mode
    executor = JourneyExecutor(
        journey, 
        target_url="http://localhost:8000",
        api_mode=True
    )
    result = executor.execute()
    
    print(f"\nAuthenticated API Mode Result: {'PASSED' if result else 'FAILED'}")
    return result


def migration_comparison():
    """
    Example: Shows how to migrate from UI mode to API mode
    Demonstrates that both modes can test the same security control
    """
    print("\n" + "="*80)
    print("Example 7: Migration Comparison - UI vs API Mode")
    print("="*80)
    
    password_gen = StaticPayloadGenerator(['test123', 'admin', 'password'])
    
    # OLD WAY: UI Mode
    print("\n--- Traditional UI Mode ---")
    ui_ttp = LoginBruteforceTTP(
        payload_generator=password_gen,
        username='admin',
        username_selector='input[name="username"]',
        password_selector='input[name="password"]',
        submit_selector='button[type="submit"]',
        execution_mode='ui'
    )
    print(f"Execution mode: {ui_ttp.execution_mode}")
    print("Requires: Selenium WebDriver, browser instance")
    print("Speed: Slower (browser overhead)")
    print("Use case: Testing UI-specific protections, user experience")
    
    # NEW WAY: API Mode
    print("\n--- New API Mode ---")
    api_ttp = LoginBruteforceTTP(
        payload_generator=password_gen,
        username='admin',
        execution_mode='api',
        api_endpoint='/api/auth/login',
        username_field='username',
        password_field='password'
    )
    print(f"Execution mode: {api_ttp.execution_mode}")
    print("Requires: Only requests library")
    print("Speed: Faster (direct HTTP)")
    print("Use case: Testing backend protections, rate limiting, API security")
    print("\nBoth modes test the same security control, just at different layers!")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("TTP API Mode Demo")
    print("="*80)
    print("\nThis demo shows how to use TTPs in both UI and API modes.")
    print("API mode allows you to bypass Selenium and test backend APIs directly.")
    print("\nNOTE: These examples assume a test server is running on localhost:8000")
    print("See examples/test_server_with_version.py for a test server.")
    print("="*80)
    
    # Show the migration comparison
    migration_comparison()
    
    print("\n\nUncomment the examples below to run actual tests:")
    print("(Requires test server to be running)")
    
    # Uncomment to run actual tests:
    # login_bruteforce_ui_mode_example()
    # login_bruteforce_api_mode_example()
    # sql_injection_ui_mode_example()
    # sql_injection_api_mode_example()
    # url_manipulation_api_mode_example()
    # mixed_mode_with_authentication_example()
    
    print("\n" + "="*80)
    print("Demo Complete!")
    print("="*80)
