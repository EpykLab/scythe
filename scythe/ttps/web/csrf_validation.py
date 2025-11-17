"""
CSRF Validation TTP - Tests whether CSRF protection is properly enforced.

This TTP validates that the application properly enforces CSRF protection by:
1. Making requests WITHOUT CSRF tokens (should be rejected)
2. Making requests WITH valid CSRF tokens (should succeed)
3. Making requests with INVALID CSRF tokens (should be rejected)
4. Testing multiple endpoints to ensure comprehensive coverage
"""

from typing import Dict, Any, Optional, List, Generator
import requests
import time
import logging

from ...core.ttp import TTP
from ...core.csrf import CSRFProtection


logger = logging.getLogger(__name__)


class CSRFValidationTTP(TTP):
    """
    Tests whether CSRF protection is actually enforced by the application.

    This TTP performs comprehensive CSRF validation testing by making requests
    with and without valid CSRF tokens to verify that the application properly
    rejects unauthorized requests.

    Test scenarios:
    1. Request WITHOUT any CSRF token → Should get 403/419 (CSRF rejection)
    2. Request WITH valid CSRF token → Should succeed (200-299)
    3. Request with INVALID/fake CSRF token → Should get 403/419 (CSRF rejection)

    Expected results:
    - expected_result=True: CSRF protection IS properly enforced (recommended)
    - expected_result=False: CSRF protection is NOT enforced (vulnerability)

    Example usage:
        csrf = CSRFProtection(cookie_name='csrftoken', header_name='X-CSRF-Token')

        ttp = CSRFValidationTTP(
            target_endpoints=['/api/users', '/api/posts', '/api/delete'],
            http_method='POST',
            test_payload={'test': 'data'},
            csrf_protection=csrf,
            expected_result=True  # Expect CSRF to be enforced
        )
    """

    def __init__(
        self,
        target_endpoints: List[str],
        http_method: str = 'POST',
        test_payload: Optional[Dict[str, Any]] = None,
        csrf_protection: Optional[CSRFProtection] = None,
        expected_rejection_codes: Optional[List[int]] = None,
        expected_success_codes: Optional[List[int]] = None,
        test_invalid_token: bool = True,
        invalid_token_value: str = 'invalid-csrf-token-12345',
        expected_result: bool = True,
        authentication=None
    ):
        """
        Initialize CSRF Validation TTP.

        Args:
            target_endpoints: List of endpoint paths to test (e.g., ['/api/users', '/api/posts'])
            http_method: HTTP method to use for testing (default: POST)
            test_payload: Optional payload data to send with requests
            csrf_protection: CSRFProtection configuration for extracting/injecting tokens
            expected_rejection_codes: Status codes indicating CSRF rejection (default: [403, 419])
            expected_success_codes: Status codes indicating success (default: 200-299)
            test_invalid_token: Whether to test with invalid tokens (default: True)
            invalid_token_value: The invalid token value to use for testing
            expected_result: True if CSRF should be enforced (secure), False if not (vulnerable)
            authentication: Optional authentication to use before testing
        """
        super().__init__(
            name="CSRF Validation Test",
            description=f"Validates CSRF protection enforcement on {len(target_endpoints)} endpoint(s)",
            expected_result=expected_result,
            authentication=authentication,
            execution_mode='api',
            csrf_protection=csrf_protection
        )

        self.target_endpoints = target_endpoints
        self.http_method = http_method.upper()
        self.test_payload = test_payload or {}
        self.expected_rejection_codes = expected_rejection_codes or [403, 419]
        self.expected_success_codes = expected_success_codes or list(range(200, 300))
        self.test_invalid_token = test_invalid_token
        self.invalid_token_value = invalid_token_value

        # Validation results storage
        self.validation_results = {
            'endpoints_tested': 0,
            'endpoints_protected': 0,
            'endpoints_vulnerable': 0,
            'test_details': []
        }

        if not csrf_protection:
            logger.warning("No CSRF protection configured - will only test rejection without tokens")

    def get_payloads(self) -> Generator[Dict[str, Any], None, None]:
        """
        Generate test payloads for each endpoint and test scenario.

        Each payload represents one test case:
        - Test 1: Request without CSRF token
        - Test 2: Request with valid CSRF token
        - Test 3: Request with invalid CSRF token (if enabled)

        Yields:
            Dict containing endpoint, test_type, and expected behavior
        """
        for endpoint in self.target_endpoints:
            # Test 1: Without CSRF token (should be rejected)
            yield {
                'endpoint': endpoint,
                'test_type': 'without_token',
                'expected_outcome': 'rejected',
                'use_token': False,
                'use_invalid_token': False
            }

            # Test 2: With valid CSRF token (should succeed)
            if self.csrf_protection:
                yield {
                    'endpoint': endpoint,
                    'test_type': 'with_valid_token',
                    'expected_outcome': 'success',
                    'use_token': True,
                    'use_invalid_token': False
                }

            # Test 3: With invalid CSRF token (should be rejected)
            if self.test_invalid_token and self.csrf_protection:
                yield {
                    'endpoint': endpoint,
                    'test_type': 'with_invalid_token',
                    'expected_outcome': 'rejected',
                    'use_token': True,
                    'use_invalid_token': True
                }

    def execute_step_api(
        self,
        session: requests.Session,
        payload: Dict[str, Any],
        context: Dict[str, Any]
    ) -> requests.Response:
        """
        Execute a single CSRF validation test.

        Args:
            session: requests.Session for making HTTP requests
            payload: Test case payload from get_payloads()
            context: Shared context including target URL and CSRF state

        Returns:
            Response from the test request
        """
        from urllib.parse import urljoin

        endpoint = payload['endpoint']
        test_type = payload['test_type']
        use_token = payload['use_token']
        use_invalid_token = payload['use_invalid_token']

        # Build URL
        base_url = context.get('target_url', '')
        url = urljoin(base_url, endpoint)

        # Prepare headers
        headers = {'Content-Type': 'application/json'}

        # Merge auth headers
        auth_headers = context.get('auth_headers', {})
        if auth_headers:
            headers.update(auth_headers)

        # Handle CSRF token injection
        if use_token:
            if use_invalid_token:
                # Use a fake/invalid token
                if self.csrf_protection:
                    if self.csrf_protection.inject_into == 'header':
                        headers[self.csrf_protection.header_name] = self.invalid_token_value
                        logger.debug(f"Injecting INVALID CSRF token into header '{self.csrf_protection.header_name}'")
                    elif self.csrf_protection.inject_into == 'body':
                        self.test_payload[self.csrf_protection.body_field] = self.invalid_token_value
                        logger.debug(f"Injecting INVALID CSRF token into body field '{self.csrf_protection.body_field}'")
            else:
                # Use the valid token from context
                csrf_protection = context.get('csrf_protection')
                if isinstance(csrf_protection, CSRFProtection):
                    headers, data = csrf_protection.inject_token(
                        headers=headers,
                        data=self.test_payload.copy(),
                        method=self.http_method,
                        context=context
                    )
                    self.test_payload = data or self.test_payload
                    logger.debug(f"Injecting VALID CSRF token")
        else:
            # Explicitly do NOT include CSRF token
            logger.debug(f"NOT including CSRF token (testing rejection)")

        # Make the request
        start_time = time.time()
        try:
            logger.info(f"Testing {endpoint} - {test_type}")

            response = session.request(
                method=self.http_method,
                url=url,
                json=self.test_payload if self.test_payload else None,
                headers=headers,
                timeout=10
            )

            response_time = time.time() - start_time

            # Record test result
            self._record_test_result(payload, response, response_time)

            return response

        except Exception as e:
            logger.error(f"Request failed: {e}")
            response_time = time.time() - start_time
            self._record_test_result(payload, None, response_time, error=str(e))
            raise

    def verify_result_api(
        self,
        response: requests.Response,
        context: Dict[str, Any]
    ) -> bool:
        """
        Verify if the CSRF protection behaved as expected.

        For each test type:
        - without_token: Should be rejected (403/419)
        - with_valid_token: Should succeed (200-299)
        - with_invalid_token: Should be rejected (403/419)

        Args:
            response: Response from execute_step_api
            context: Shared context

        Returns:
            True if CSRF behaved correctly, False if vulnerability detected
        """
        if not response:
            return False

        status_code = response.status_code

        # Get the last test result to know what was expected
        if not self.validation_results['test_details']:
            return False

        last_test = self.validation_results['test_details'][-1]
        expected_outcome = last_test.get('expected_outcome')
        test_type = last_test.get('test_type')
        endpoint = last_test.get('endpoint')

        if expected_outcome == 'rejected':
            # Should be rejected with 403/419
            is_rejected = status_code in self.expected_rejection_codes

            if is_rejected:
                logger.info(f"✓ {endpoint} - {test_type}: Correctly rejected with {status_code}")
                last_test['result'] = 'PASS'
                last_test['behavior'] = 'Correctly rejected'
                return True
            else:
                logger.warning(f"✗ {endpoint} - {test_type}: NOT rejected! Got {status_code} (VULNERABILITY)")
                last_test['result'] = 'FAIL'
                last_test['behavior'] = f'Should reject but got {status_code}'
                self.validation_results['endpoints_vulnerable'] += 1
                return False

        elif expected_outcome == 'success':
            # Should succeed with 200-299
            is_success = status_code in self.expected_success_codes

            if is_success:
                logger.info(f"✓ {endpoint} - {test_type}: Correctly accepted with {status_code}")
                last_test['result'] = 'PASS'
                last_test['behavior'] = 'Correctly accepted'
                return True
            else:
                logger.warning(f"✗ {endpoint} - {test_type}: Rejected valid token! Got {status_code}")
                last_test['result'] = 'FAIL'
                last_test['behavior'] = f'Valid token rejected with {status_code}'
                return False

        return False

    def _record_test_result(
        self,
        payload: Dict[str, Any],
        response: Optional[requests.Response],
        response_time: float,
        error: Optional[str] = None
    ):
        """Record the result of a test case."""
        result = {
            'endpoint': payload['endpoint'],
            'test_type': payload['test_type'],
            'expected_outcome': payload['expected_outcome'],
            'status_code': response.status_code if response else None,
            'response_time_ms': int(response_time * 1000),
            'error': error,
            'result': 'PENDING',  # Will be updated in verify_result_api
            'behavior': 'Unknown'
        }

        self.validation_results['test_details'].append(result)
        self.validation_results['endpoints_tested'] = len(set(
            r['endpoint'] for r in self.validation_results['test_details']
        ))

    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the CSRF validation results.

        Returns:
            Dict with summary statistics and detailed results
        """
        # Count protected endpoints (all tests passed for that endpoint)
        endpoint_status = {}
        for detail in self.validation_results['test_details']:
            endpoint = detail['endpoint']
            if endpoint not in endpoint_status:
                endpoint_status[endpoint] = {'passed': 0, 'failed': 0, 'total': 0}

            endpoint_status[endpoint]['total'] += 1
            if detail['result'] == 'PASS':
                endpoint_status[endpoint]['passed'] += 1
            else:
                endpoint_status[endpoint]['failed'] += 1

        # Determine protected vs vulnerable
        protected = sum(1 for ep, status in endpoint_status.items() if status['failed'] == 0)
        vulnerable = sum(1 for ep, status in endpoint_status.items() if status['failed'] > 0)

        # Recalculate endpoints_tested
        self.validation_results['endpoints_tested'] = len(endpoint_status)
        self.validation_results['endpoints_protected'] = protected
        self.validation_results['endpoints_vulnerable'] = vulnerable

        return {
            **self.validation_results,
            'endpoint_status': endpoint_status,
            'overall_result': 'SECURE' if vulnerable == 0 else 'VULNERABLE',
            'protection_rate': f"{protected}/{len(endpoint_status)}" if endpoint_status else "0/0"
        }

    # UI mode not supported for CSRF validation
    def execute_step(self, driver, payload):
        """UI mode not supported for CSRF validation."""
        raise NotImplementedError("CSRF validation only supports API mode")

    def verify_result(self, driver):
        """UI mode not supported for CSRF validation."""
        raise NotImplementedError("CSRF validation only supports API mode")
