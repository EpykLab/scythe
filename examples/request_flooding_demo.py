#!/usr/bin/env python3
"""
RequestFloodingTTP Usage Examples

This demo shows how to use the new RequestFloodingTTP for testing 
application resilience against DDoS and request flooding attacks.
"""

from scythe.ttps.web.request_flooding import RequestFloodingTTP
from scythe.core.executor import Executor


def basic_api_flooding_example():
    """
    Basic API flooding test to check rate limiting.
    """
    print("=== Basic API Flooding Example ===")
    
    # Create a TTP that tests API endpoints with volume flooding
    ttp = RequestFloodingTTP(
        target_endpoints=['/api/search', '/api/users', '/api/products'],
        request_count=100,
        requests_per_second=15.0,
        attack_pattern='volume',
        concurrent_threads=5,
        execution_mode='api',
        expected_result=False,  # We expect defenses to kick in
        http_method='GET'
    )
    
    # Configure executor
    executor = Executor(
        target_url='https://api.example.com',
        ttp=ttp,
        behavior=None  # Use default behavior
    )
    
    print(f"TTP Name: {ttp.name}")
    print(f"Description: {ttp.description}")
    print(f"Attack Pattern: {ttp.attack_pattern}")
    print(f"Expected Result: {'Success' if ttp.expected_result else 'Defenses should activate'}")
    
    # Note: Uncomment to actually run the test
    # results = executor.execute()
    # print(f"Results: {results}")


def burst_attack_example():
    """
    Burst attack pattern that sends traffic in waves.
    """
    print("\n=== Burst Attack Example ===")
    
    ttp = RequestFloodingTTP(
        target_endpoints=['/api/heavy-computation'],
        request_count=50,
        requests_per_second=5.0,
        attack_pattern='burst',  # Send bursts every 10 requests
        concurrent_threads=3,
        execution_mode='api',
        payload_data={
            'complexity': 'high',
            'dataset_size': 10000
        },
        expected_result=False
    )
    
    print(f"Attack Pattern: {ttp.attack_pattern}")
    print("This pattern sends fast bursts every 10 requests with slower periods between")


def slowloris_attack_example():
    """
    Slowloris-style attack with long-held connections.
    """
    print("\n=== Slowloris Attack Example ===")
    
    ttp = RequestFloodingTTP(
        target_endpoints=['/api/upload', '/api/process'],
        request_count=20,
        requests_per_second=2.0,
        attack_pattern='slowloris',
        concurrent_threads=10,
        execution_mode='api',
        expected_result=False
    )
    
    print(f"Attack Pattern: {ttp.attack_pattern}")
    print("This pattern holds connections open for extended periods")


def resource_exhaustion_example():
    """
    Resource exhaustion attack targeting expensive operations.
    """
    print("\n=== Resource Exhaustion Example ===")
    
    ttp = RequestFloodingTTP(
        target_endpoints=['/api/search', '/api/reports'],
        request_count=30,
        requests_per_second=8.0,
        attack_pattern='resource_exhaustion',
        concurrent_threads=4,
        execution_mode='api',
        payload_data={
            'query': '*',  # Will be overridden by pattern
            'format': 'detailed'
        },
        expected_result=False
    )
    
    print(f"Attack Pattern: {ttp.attack_pattern}")
    print("This pattern requests large datasets and expensive operations")


def ui_mode_flooding_example():
    """
    UI mode flooding for testing web form submissions.
    """
    print("\n=== UI Mode Flooding Example ===")
    
    ttp = RequestFloodingTTP(
        target_endpoints=['/contact', '/signup'],
        request_count=25,
        requests_per_second=3.0,
        attack_pattern='volume',
        execution_mode='ui',
        form_selector='form',
        submit_selector='button[type="submit"], input[type="submit"]',
        payload_data={
            'name': 'Test User',
            'email': 'test@example.com',
            'message': 'This is a test message for flooding'
        },
        expected_result=False
    )
    
    print(f"Execution Mode: {ttp.execution_mode}")
    print("This tests form submission flooding through the browser UI")


def authenticated_flooding_example():
    """
    Flooding attack that requires authentication.
    """
    print("\n=== Authenticated Flooding Example ===")
    
    # Note: You would typically import and configure an authentication method
    # from scythe.auth.basic import BasicAuth
    # auth = BasicAuth(username='testuser', password='testpass')
    
    ttp = RequestFloodingTTP(
        target_endpoints=['/api/protected/data', '/api/user/profile'],
        request_count=75,
        requests_per_second=12.0,
        attack_pattern='volume',
        execution_mode='api',
        # authentication=auth,  # Uncomment when using real auth
        expected_result=False
    )
    
    print("This example shows flooding against authenticated endpoints")


def custom_success_indicators_example():
    """
    Flooding with custom indicators for detecting defensive measures.
    """
    print("\n=== Custom Success Indicators Example ===")
    
    ttp = RequestFloodingTTP(
        target_endpoints=['/api/data'],
        request_count=40,
        execution_mode='api',
        success_indicators={
            'rate_limit_status_codes': [429, 503, 502, 522],
            'error_keywords': ['rate limit', 'blocked', 'temporary ban'],
            'max_response_time': 20.0,
            'expected_success_rate': 0.15  # Expect 85% to be blocked
        },
        expected_result=False
    )
    
    print("Custom indicators help detect various defensive mechanisms")


def analyze_attack_results():
    """
    Example of how to analyze attack results for detailed insights.
    """
    print("\n=== Attack Results Analysis ===")
    
    # Create a TTP and simulate some results
    ttp = RequestFloodingTTP(request_count=10)
    
    # Simulate results (in real usage, these come from actual requests)
    import requests
    from unittest.mock import Mock
    
    # Simulate mixed results
    for i in range(5):
        response = Mock()
        response.status_code = 200
        response.headers = {}
        ttp._record_api_result(response, 0.5 + i * 0.1, {})
    
    for i in range(3):
        response = Mock()
        response.status_code = 429
        response.headers = {'Retry-After': '5'}
        ttp._record_api_result(response, 0.2, {})
    
    # Simulate some timeouts
    for i in range(2):
        ttp._record_api_result(None, 10.0, {}, timeout=True)
    
    # Get comprehensive summary
    summary = ttp.get_attack_summary()
    
    print("Attack Results Summary:")
    print(f"  Total Requests: {summary['total_requests']}")
    print(f"  Success Rate: {summary['success_rate']:.1f}%")
    print(f"  Rate Limited: {summary['rate_limit_rate']:.1f}%")
    print(f"  Error Rate: {summary['error_rate']:.1f}%")
    print(f"  Avg Response Time: {summary['avg_response_time']}s")
    print(f"  Defense Assessment: {summary['defense_assessment']}")
    print(f"  Status Codes: {summary['status_code_distribution']}")


def main():
    """
    Run all examples to demonstrate the RequestFloodingTTP capabilities.
    """
    print("RequestFloodingTTP Usage Examples")
    print("=" * 50)
    
    try:
        basic_api_flooding_example()
        burst_attack_example()
        slowloris_attack_example()
        resource_exhaustion_example()
        ui_mode_flooding_example()
        authenticated_flooding_example()
        custom_success_indicators_example()
        analyze_attack_results()
        
        print("\n" + "=" * 50)
        print("✅ All examples completed successfully!")
        print("\nTo actually run these tests against a target:")
        print("1. Configure your target URL")
        print("2. Set up appropriate authentication if needed")
        print("3. Uncomment the executor.execute() calls")
        print("4. Run with appropriate rate limiting to avoid overwhelming targets")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()