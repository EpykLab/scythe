"""
CSRF Validation Example - Testing whether CSRF protection is actually enforced

This example demonstrates how to use the CSRFValidationTTP to verify that
your web application properly enforces CSRF protection.
"""

from scythe.ttps.web.csrf_validation import CSRFValidationTTP
from scythe.core.csrf import CSRFProtection
from scythe.core.executor import TTPExecutor


# Example 1: Basic CSRF Validation
def example_basic_validation():
    """Test basic CSRF validation on a few endpoints."""

    # Configure how to extract/inject CSRF tokens
    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='csrftoken',      # Django default
        header_name='X-CSRFToken',
        inject_into='header'
    )

    # Create validation TTP
    ttp = CSRFValidationTTP(
        target_endpoints=[
            '/api/users',
            '/api/posts',
            '/api/comments'
        ],
        http_method='POST',
        test_payload={'test': 'data'},
        csrf_protection=csrf,
        expected_result=True  # We EXPECT CSRF to be enforced (secure)
    )

    # Run the validation
    executor = TTPExecutor(
        ttp=ttp,
        target_url='https://your-django-app.com'
    )

    results = executor.run()

    # Get detailed summary
    summary = ttp.get_validation_summary()

    print("\n" + "="*60)
    print("CSRF VALIDATION SUMMARY")
    print("="*60)
    print(f"Overall Result: {summary['overall_result']}")
    print(f"Endpoints Tested: {summary['endpoints_tested']}")
    print(f"Protected: {summary['endpoints_protected']}")
    print(f"Vulnerable: {summary['endpoints_vulnerable']}")
    print(f"Protection Rate: {summary['protection_rate']}")

    print("\n" + "-"*60)
    print("DETAILED RESULTS:")
    print("-"*60)
    for detail in summary['test_details']:
        status_icon = "✓" if detail['result'] == 'PASS' else "✗"
        print(f"{status_icon} {detail['endpoint']} - {detail['test_type']}: "
              f"{detail['status_code']} - {detail['behavior']}")

    return summary


# Example 2: Laravel Application
def example_laravel_validation():
    """Test CSRF validation on Laravel application."""

    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='XSRF-TOKEN',     # Laravel default
        header_name='X-XSRF-TOKEN',
        inject_into='header'
    )

    ttp = CSRFValidationTTP(
        target_endpoints=[
            '/api/products',
            '/api/orders',
            '/api/cart'
        ],
        http_method='POST',
        csrf_protection=csrf,
        expected_result=True
    )

    executor = TTPExecutor(ttp=ttp, target_url='https://your-laravel-app.com')
    results = executor.run()

    summary = ttp.get_validation_summary()
    print(f"\nLaravel CSRF Status: {summary['overall_result']}")
    print(f"Protected Endpoints: {summary['protection_rate']}")


# Example 3: Custom Application
def example_custom_validation():
    """Test CSRF validation on custom application with custom cookie name."""

    csrf = CSRFProtection(
        extract_from='cookie',
        cookie_name='__Host-csrf_',   # Your custom cookie
        header_name='X-CSRF-Token',
        inject_into='header'
    )

    ttp = CSRFValidationTTP(
        target_endpoints=[
            '/api/admin/users',
            '/api/admin/settings',
            '/api/data/delete'
        ],
        http_method='POST',
        test_payload={'action': 'test'},
        csrf_protection=csrf,
        expected_result=True
    )

    executor = TTPExecutor(ttp=ttp, target_url='https://your-custom-app.com')
    results = executor.run()

    return ttp.get_validation_summary()


# Example 4: Testing for Vulnerabilities (Expecting CSRF NOT to be enforced)
def example_vulnerability_detection():
    """
    Test endpoints that SHOULD NOT have CSRF protection.
    Or test to detect if CSRF protection is missing (vulnerability).
    """

    csrf = CSRFProtection(
        cookie_name='csrftoken',
        header_name='X-CSRF-Token'
    )

    ttp = CSRFValidationTTP(
        target_endpoints=[
            '/api/public/contact',      # Public endpoint, no CSRF expected
            '/api/public/newsletter'
        ],
        http_method='POST',
        csrf_protection=csrf,
        expected_result=False  # We EXPECT CSRF NOT to be enforced
    )

    executor = TTPExecutor(ttp=ttp, target_url='https://your-app.com')
    results = executor.run()

    summary = ttp.get_validation_summary()
    if summary['overall_result'] == 'VULNERABLE':
        print("✓ Public endpoints correctly have no CSRF protection")
    else:
        print("✗ Unexpected: Public endpoints have CSRF protection")


# Example 5: Testing Only Token Rejection (No Invalid Token Test)
def example_rejection_only():
    """Test only that requests without tokens are rejected."""

    csrf = CSRFProtection(
        cookie_name='csrftoken',
        header_name='X-CSRF-Token'
    )

    ttp = CSRFValidationTTP(
        target_endpoints=['/api/sensitive'],
        csrf_protection=csrf,
        test_invalid_token=False,  # Skip invalid token test
        expected_result=True
    )

    executor = TTPExecutor(ttp=ttp, target_url='https://your-app.com')
    results = executor.run()

    summary = ttp.get_validation_summary()
    # Will only test: without_token and with_valid_token
    print(f"Tests run: {len(summary['test_details'])}")  # Should be 2, not 3


# Example 6: Custom Rejection and Success Codes
def example_custom_status_codes():
    """Test with custom expected status codes."""

    csrf = CSRFProtection(
        cookie_name='csrftoken',
        header_name='X-CSRF-Token'
    )

    ttp = CSRFValidationTTP(
        target_endpoints=['/api/special'],
        csrf_protection=csrf,
        expected_rejection_codes=[403, 419, 401],  # Accept 401 as CSRF rejection
        expected_success_codes=[200, 201, 204],    # Accept multiple success codes
        expected_result=True
    )

    executor = TTPExecutor(ttp=ttp, target_url='https://your-app.com')
    results = executor.run()


# Example 7: With Authentication
def example_with_authentication():
    """Test CSRF validation with authenticated endpoints."""

    from scythe.auth.bearer import BearerTokenAuth

    # Setup authentication
    auth = BearerTokenAuth(
        login_url='/api/login',
        username='testuser',
        password='testpass',
        token_field='access_token'
    )

    # Setup CSRF
    csrf = CSRFProtection(
        cookie_name='csrftoken',
        header_name='X-CSRF-Token'
    )

    # Test authenticated endpoints
    ttp = CSRFValidationTTP(
        target_endpoints=[
            '/api/profile/update',
            '/api/account/delete',
            '/api/settings/change'
        ],
        http_method='POST',
        csrf_protection=csrf,
        authentication=auth,  # Add authentication
        expected_result=True
    )

    executor = TTPExecutor(ttp=ttp, target_url='https://your-app.com')
    results = executor.run()

    summary = ttp.get_validation_summary()
    print(f"\nAuthenticated Endpoints - CSRF Status: {summary['overall_result']}")


# Example 8: Comprehensive Security Audit
def example_comprehensive_audit():
    """Perform a comprehensive CSRF audit across multiple endpoint types."""

    csrf = CSRFProtection(
        cookie_name='csrftoken',
        header_name='X-CSRF-Token'
    )

    # Test different HTTP methods
    for method in ['POST', 'PUT', 'PATCH', 'DELETE']:
        print(f"\n{'='*60}")
        print(f"Testing {method} endpoints")
        print(f"{'='*60}")

        ttp = CSRFValidationTTP(
            target_endpoints=[
                f'/api/test/{method.lower()}',
                f'/api/users/{method.lower()}'
            ],
            http_method=method,
            csrf_protection=csrf,
            expected_result=True
        )

        executor = TTPExecutor(ttp=ttp, target_url='https://your-app.com')
        executor.run()

        summary = ttp.get_validation_summary()
        print(f"{method} - {summary['overall_result']}: {summary['protection_rate']} protected")


# Example 9: Vulnerability Report Generation
def example_generate_report():
    """Generate a detailed vulnerability report."""

    csrf = CSRFProtection(
        cookie_name='csrftoken',
        header_name='X-CSRF-Token'
    )

    ttp = CSRFValidationTTP(
        target_endpoints=[
            '/api/users',
            '/api/posts',
            '/api/comments',
            '/api/admin/settings',
            '/api/data/export'
        ],
        csrf_protection=csrf,
        expected_result=True
    )

    executor = TTPExecutor(ttp=ttp, target_url='https://your-app.com')
    executor.run()

    summary = ttp.get_validation_summary()

    # Generate report
    print("\n" + "="*70)
    print("CSRF SECURITY AUDIT REPORT")
    print("="*70)
    print(f"Target: https://your-app.com")
    print(f"Date: {import datetime; datetime.datetime.now()}")  # Would need import
    print(f"\nOVERALL STATUS: {summary['overall_result']}")
    print(f"Total Endpoints Tested: {summary['endpoints_tested']}")
    print(f"Protected: {summary['endpoints_protected']}")
    print(f"Vulnerable: {summary['endpoints_vulnerable']}")

    if summary['endpoints_vulnerable'] > 0:
        print("\n⚠️  VULNERABILITIES DETECTED:")
        print("-"*70)
        for endpoint, status in summary['endpoint_status'].items():
            if status['failed'] > 0:
                print(f"  • {endpoint}")
                # Find which tests failed for this endpoint
                for detail in summary['test_details']:
                    if detail['endpoint'] == endpoint and detail['result'] == 'FAIL':
                        print(f"    - {detail['test_type']}: {detail['behavior']}")
    else:
        print("\n✅ All endpoints properly protected with CSRF tokens!")

    print("\nDETAILED TEST RESULTS:")
    print("-"*70)
    for detail in summary['test_details']:
        icon = "✓" if detail['result'] == 'PASS' else "✗"
        print(f"{icon} [{detail['status_code']}] {detail['endpoint']:30} "
              f"{detail['test_type']:20} - {detail['behavior']}")


if __name__ == '__main__':
    print("CSRF Validation Examples")
    print("=" * 70)
    print("\nChoose an example to run:")
    print("1. Basic Validation")
    print("2. Laravel Validation")
    print("3. Custom Application")
    print("4. Vulnerability Detection")
    print("5. Rejection Only (no invalid token test)")
    print("6. Custom Status Codes")
    print("7. With Authentication")
    print("8. Comprehensive Audit")
    print("9. Generate Report")
    print("\nUncomment the example you want to run in the code.\n")

    # Uncomment one of these to run:
    # example_basic_validation()
    # example_laravel_validation()
    # example_custom_validation()
    # example_vulnerability_detection()
    # example_rejection_only()
    # example_custom_status_codes()
    # example_with_authentication()
    # example_comprehensive_audit()
    # example_generate_report()
