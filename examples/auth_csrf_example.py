"""
Authentication with CSRF Protection Examples

This example demonstrates how to use CSRF protection with different
authentication methods in the Scythe testing framework.
"""

from scythe.auth.basic import BasicAuth
from scythe.auth.bearer import BearerTokenAuth
from scythe.auth.cookie_jwt import CookieJWTAuth
from scythe.core.csrf import CSRFProtection
from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.core.executor import TTPExecutor
from scythe.payloads.generators import PayloadGenerator


# Example 1: Django Form-Based Login with CSRF
def example_django_basic_auth_with_csrf():
    """
    Django applications typically have CSRF protection on login forms.
    Selenium (UI mode) handles this automatically, but the BasicAuth class
    can store the CSRF config for reference.
    """

    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='csrftoken',
        header_name='X-CSRFToken'
    )

    auth = BasicAuth(
        username='testuser',
        password='testpass',
        login_url='https://django-app.com/login',
        username_selector='input[name="username"]',
        password_selector='input[name="password"]',
        submit_selector='button[type="submit"]',
        csrf_protection=csrf
    )

    # Use with a TTP
    def password_generator():
        yield from ['password1', 'password2', 'correct']

    ttp = LoginBruteforceTTP(
        payload_generator=password_generator,
        username='testuser',
        execution_mode='ui',
        authentication=auth
    )

    executor = TTPExecutor(ttp=ttp, target_url='https://django-app.com')
    results = executor.run()

    print(f"Django login test: {results}")


# Example 2: API-Based JWT Login with CSRF
def example_api_jwt_login_with_csrf():
    """
    API endpoints that provide JWT tokens often have CSRF protection
    on the login endpoint. CookieJWTAuth handles CSRF automatically.
    """

    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='csrftoken',
        header_name='X-CSRF-Token',
        auto_extract=True  # Extract updated tokens from responses
    )

    auth = CookieJWTAuth(
        login_url='https://api.example.com/auth/login',
        username='user@example.com',
        password='secure_password',
        username_field='email',
        password_field='password',
        jwt_json_path='auth.token',  # Path to JWT in response
        cookie_name='auth_token',
        csrf_protection=csrf  # CSRF protection for login endpoint
    )

    # In API mode, the auth will:
    # 1. GET the login endpoint to extract CSRF token
    # 2. POST credentials with CSRF token
    # 3. Receive JWT and cookies in response
    # 4. Use JWT cookie for subsequent authenticated requests

    auth.get_auth_cookies()  # Triggers the login flow with CSRF

    print(f"JWT authentication successful")


# Example 3: Bearer Token Auth with CSRF for Token Acquisition
def example_bearer_token_auth_with_csrf():
    """
    Bearer token authentication can use CSRF-protected token acquisition endpoints.
    """

    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='csrftoken',
        header_name='X-CSRF-Token'
    )

    # Pre-existing token (no CSRF needed)
    auth_with_token = BearerTokenAuth(
        token='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        csrf_protection=csrf  # Stored but not used if token exists
    )

    # Or acquire token via CSRF-protected endpoint
    auth_acquire_token = BearerTokenAuth(
        token_url='https://api.example.com/oauth/token',
        username='service_account',
        password='service_secret',
        token_field_name='access_token',
        csrf_protection=csrf  # Used during token acquisition
    )

    headers = auth_with_token.get_auth_headers()
    print(f"Bearer token headers: {headers}")


# Example 4: Complete Flow with TTP
def example_login_bruteforce_with_csrf_auth():
    """
    Use LoginBruteforceTTP with API mode and CSRF-protected login endpoint.
    """

    # Configure CSRF for the login endpoint
    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='csrftoken',
        header_name='X-CSRF-Token',
        refresh_endpoint='/api/csrf-token',  # Optional dedicated endpoint
        auto_extract=True
    )

    # Configure API-based JWT authentication with CSRF
    auth = CookieJWTAuth(
        login_url='https://api.example.com/auth/login',
        username='testuser',
        password='testpass',
        username_field='username',
        password_field='password',
        jwt_json_path='data.token',
        cookie_name='auth',
        csrf_protection=csrf
    )

    # Password list for bruteforce
    def password_generator():
        with open('passwords.txt', 'r') as f:
            for line in f:
                yield line.strip()

    # Create TTP with authentication
    ttp = LoginBruteforceTTP(
        payload_generator=password_generator,
        username='testuser',
        execution_mode='api',
        api_endpoint='/api/auth/login',
        username_field='username',
        password_field='password',
        success_indicators={
            'status_code': 200,
            'response_not_contains': 'error'
        },
        authentication=auth,
        expected_result=True
    )

    # Execute with CSRF protection
    executor = TTPExecutor(
        ttp=ttp,
        target_url='https://api.example.com'
    )

    results = executor.run()
    print(f"Bruteforce test with CSRF: {results}")


# Example 5: Multiple Authentication Methods Comparison
def example_auth_methods_comparison():
    """
    Compare different authentication methods with CSRF support.
    """

    # Django: Form-based auth with CSRF (browser handles it)
    django_auth = BasicAuth(
        username='user',
        password='pass',
        login_url='https://django.example.com/login',
        csrf_protection=CSRFProtection(cookie_name='csrftoken')
    )

    # Laravel: API-based auth with XSRF
    laravel_auth = CookieJWTAuth(
        login_url='https://laravel.example.com/api/login',
        username='user@example.com',
        password='password',
        jwt_json_path='token',
        csrf_protection=CSRFProtection(
            extract_from='cookie',
            cookie_name='XSRF-TOKEN',
            header_name='X-XSRF-TOKEN'
        )
    )

    # Custom: API with custom CSRF naming
    custom_auth = CookieJWTAuth(
        login_url='https://custom.example.com/auth/login',
        username='user',
        password='pass',
        csrf_protection=CSRFProtection(
            extract_from='cookie',
            cookie_name='__Host-csrf_',
            header_name='X-CSRF-Token',
            body_field='_csrf_token'
        )
    )

    print("Configured authentication methods:")
    print(f"1. Django (CSRF: {django_auth.csrf_protection.cookie_name})")
    print(f"2. Laravel (CSRF: {laravel_auth.csrf_protection.cookie_name})")
    print(f"3. Custom (CSRF: {custom_auth.csrf_protection.cookie_name})")


# Example 6: Manual CSRF Token Management
def example_manual_csrf_with_auth():
    """
    Manually manage CSRF tokens with authentication.
    """

    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='csrftoken',
        header_name='X-CSRF-Token',
        auto_extract=False  # Manually control extraction
    )

    auth = CookieJWTAuth(
        login_url='https://api.example.com/login',
        username='user',
        password='pass',
        csrf_protection=csrf
    )

    # You can access auth_data to see stored CSRF information
    jwt_token = auth.get_auth_data('jwt')
    login_time = auth.get_auth_data('login_time')

    print(f"JWT Token: {jwt_token}")
    print(f"Login Time: {login_time}")


# Example 7: CSRF-Protected Authentication in Journey
def example_csrf_auth_in_journey():
    """
    Use CSRF-protected authentication in a Journey.
    """

    from scythe.journeys.base import Journey
    from scythe.journeys.actions import ApiRequestAction

    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='csrftoken',
        header_name='X-CSRF-Token'
    )

    auth = CookieJWTAuth(
        login_url='https://api.example.com/auth/login',
        username='user@example.com',
        password='password',
        csrf_protection=csrf
    )

    # Create journey with authentication
    journey = Journey(
        name="API Journey with Auth",
        steps=[
            # Steps will have access to authenticated session
        ],
        authentication=auth,
        csrf_protection=csrf  # Also pass CSRF to journey for API requests
    )

    print(f"Journey configured with {auth.name} and CSRF protection")


if __name__ == '__main__':
    print("Authentication with CSRF Protection Examples")
    print("=" * 70)
    print("\nExample Functions:")
    print("1. example_django_basic_auth_with_csrf()")
    print("2. example_api_jwt_login_with_csrf()")
    print("3. example_bearer_token_auth_with_csrf()")
    print("4. example_login_bruteforce_with_csrf_auth()")
    print("5. example_auth_methods_comparison()")
    print("6. example_manual_csrf_with_auth()")
    print("7. example_csrf_auth_in_journey()")
    print("\nUncomment the example you want to run in the code.\n")

    # Uncomment one of these to run:
    # example_django_basic_auth_with_csrf()
    # example_api_jwt_login_with_csrf()
    # example_bearer_token_auth_with_csrf()
    # example_login_bruteforce_with_csrf_auth()
    example_auth_methods_comparison()
    # example_manual_csrf_with_auth()
    # example_csrf_auth_in_journey()
