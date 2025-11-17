"""
Login Bruteforce with CSRF Protection Example

This example demonstrates how to use LoginBruteforceTTP in API mode
with CSRF protection enabled.
"""

from scythe.ttps.web.login_bruteforce import LoginBruteforceTTP
from scythe.core.csrf import CSRFProtection
from scythe.core.executor import TTPExecutor
from scythe.payloads.generators import PayloadGenerator


# Example 1: Django application with CSRF
def example_django_login_bruteforce():
    """Test login bruteforce on Django app with CSRF protection."""

    # Configure CSRF protection for Django
    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='csrftoken',      # Django default
        header_name='X-CSRFToken',
        inject_into='header'
    )

    # Create a simple password generator
    def password_generator():
        passwords = ['password123', 'admin123', 'test123', 'correct_password']
        for pwd in passwords:
            yield pwd

    # Create the TTP
    ttp = LoginBruteforceTTP(
        payload_generator=password_generator,
        username='testuser',
        execution_mode='api',
        api_endpoint='/api/auth/login',
        username_field='username',
        password_field='password',
        success_indicators={
            'status_code': 200,
            'response_not_contains': 'invalid'
        },
        csrf_protection=csrf,  # Enable CSRF
        expected_result=True   # We expect to find a valid password
    )

    # Execute the TTP
    executor = TTPExecutor(
        ttp=ttp,
        target_url='https://your-django-app.com'
    )

    results = executor.run()
    print(f"\nLogin bruteforce completed!")
    print(f"Success: {results.get('success', False)}")


# Example 2: Laravel application with CSRF
def example_laravel_login_bruteforce():
    """Test login bruteforce on Laravel app with CSRF protection."""

    # Configure CSRF protection for Laravel
    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='XSRF-TOKEN',     # Laravel default
        header_name='X-XSRF-TOKEN',
        inject_into='header'
    )

    def password_generator():
        # Use a wordlist or custom passwords
        passwords = ['pass1', 'pass2', 'pass3', 'secret123']
        for pwd in passwords:
            yield pwd

    ttp = LoginBruteforceTTP(
        payload_generator=password_generator,
        username='admin',
        execution_mode='api',
        api_endpoint='/api/login',
        csrf_protection=csrf,
        expected_result=False  # Testing if bruteforce is prevented
    )

    executor = TTPExecutor(ttp=ttp, target_url='https://your-laravel-app.com')
    results = executor.run()

    print(f"\nBruteforce prevention test completed!")
    print(f"Prevented: {not results.get('success', True)}")


# Example 3: Custom application with CSRF in body
def example_custom_csrf_in_body():
    """Test login bruteforce with CSRF token in request body."""

    # Some apps expect CSRF in the POST body instead of headers
    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='__Host-csrf_',
        body_field='_csrf',          # Token goes in body
        inject_into='body'           # Not header
    )

    def password_generator():
        with open('passwords.txt', 'r') as f:
            for line in f:
                yield line.strip()

    ttp = LoginBruteforceTTP(
        payload_generator=password_generator,
        username='user@example.com',
        execution_mode='api',
        api_endpoint='/auth/login',
        username_field='email',      # Custom field name
        password_field='pass',       # Custom field name
        csrf_protection=csrf,
        expected_result=True
    )

    executor = TTPExecutor(ttp=ttp, target_url='https://custom-app.com')
    executor.run()


# Example 4: With dedicated CSRF refresh endpoint
def example_with_refresh_endpoint():
    """Test login bruteforce when app has dedicated CSRF endpoint."""

    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='csrftoken',
        header_name='X-CSRF-Token',
        refresh_endpoint='/api/csrf-token'  # Dedicated refresh endpoint
    )

    def password_generator():
        yield from ['test1', 'test2', 'test3']

    ttp = LoginBruteforceTTP(
        payload_generator=password_generator,
        username='testuser',
        execution_mode='api',
        api_endpoint='/api/login',
        csrf_protection=csrf
    )

    executor = TTPExecutor(ttp=ttp, target_url='https://your-app.com')
    executor.run()


# Example 5: Testing rate limiting with CSRF
def example_rate_limiting_with_csrf():
    """Test login bruteforce with both CSRF and rate limiting."""

    csrf = CSRFProtection(
        cookie_name='csrftoken',
        header_name='X-CSRF-Token'
    )

    def many_passwords():
        # Try many passwords to trigger rate limiting
        for i in range(100):
            yield f'password{i}'

    ttp = LoginBruteforceTTP(
        payload_generator=many_passwords,
        username='testuser',
        execution_mode='api',
        api_endpoint='/api/login',
        csrf_protection=csrf,
        expected_result=False  # Expect rate limiting to prevent success
    )

    executor = TTPExecutor(ttp=ttp, target_url='https://your-app.com')
    results = executor.run()

    print(f"\nRate limiting test completed!")
    print(f"Rate limited: {results.get('rate_limited', False)}")


# Example 6: No CSRF protection (public endpoint)
def example_no_csrf():
    """Test login bruteforce on endpoint without CSRF protection."""

    def password_generator():
        yield from ['admin', 'password', '123456']

    # No csrf_protection parameter - works normally
    ttp = LoginBruteforceTTP(
        payload_generator=password_generator,
        username='user',
        execution_mode='api',
        api_endpoint='/public/login'
        # No csrf_protection - endpoint doesn't require it
    )

    executor = TTPExecutor(ttp=ttp, target_url='https://public-api.com')
    executor.run()


if __name__ == '__main__':
    print("Login Bruteforce with CSRF Examples")
    print("=" * 70)
    print("\nChoose an example to run:")
    print("1. Django Login Bruteforce with CSRF")
    print("2. Laravel Login Bruteforce with CSRF")
    print("3. Custom CSRF in Body")
    print("4. With Dedicated CSRF Refresh Endpoint")
    print("5. Rate Limiting with CSRF")
    print("6. No CSRF Protection")
    print("\nUncomment the example you want to run in the code.\n")

    # Uncomment one of these to run:
    # example_django_login_bruteforce()
    # example_laravel_login_bruteforce()
    # example_custom_csrf_in_body()
    # example_with_refresh_endpoint()
    # example_rate_limiting_with_csrf()
    # example_no_csrf()
