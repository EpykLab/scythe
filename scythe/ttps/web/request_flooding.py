from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from typing import Dict, Any, Optional, List, Generator
import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

from ...core.ttp import TTP


class RequestFloodingTTP(TTP):
    """
    A TTP that emulates DDoS and request flooding attacks to test application resilience.
    
    This TTP tests an application's ability to withstand high-volume request attacks
    and rate limiting mechanisms by sending multiple rapid requests to target endpoints.
    
    Supports two execution modes:
    - UI mode: Uses Selenium to repeatedly interact with web pages/forms
    - API mode: Makes rapid HTTP requests to API endpoints
    
    Attack patterns include:
    - Volume flooding: High number of requests in short time
    - Slowloris-style: Slow, prolonged connections
    - Burst flooding: Intermittent bursts of high traffic
    - Resource exhaustion: Targeting expensive operations
    """
    
    def __init__(self,
                 target_endpoints: List[str] = None,
                 request_count: int = 100,
                 requests_per_second: float = 10.0,
                 attack_pattern: str = 'volume',
                 concurrent_threads: int = 5,
                 payload_data: Optional[Dict[str, Any]] = None,
                 http_method: str = 'GET',
                 form_selector: str = None,
                 submit_selector: str = None,
                 expected_result: bool = False,
                 authentication=None,
                 execution_mode: str = 'api',
                 success_indicators: Optional[Dict[str, Any]] = None,
                 user_agents: Optional[List[str]] = None,
                 randomize_timing: bool = True):
        """
        Initialize the Request Flooding TTP.
        
        Args:
            target_endpoints: List of endpoint paths to target (e.g., ['/api/search', '/login'])
            request_count: Total number of requests to send per endpoint
            requests_per_second: Target rate of requests (used for timing calculations)
            attack_pattern: Type of attack - 'volume', 'slowloris', 'burst', 'resource_exhaustion'
            concurrent_threads: Number of concurrent threads to use for requests
            payload_data: Data to send in request body (API mode) or form fields (UI mode)
            http_method: HTTP method to use ('GET', 'POST', 'PUT', 'DELETE')
            form_selector: CSS selector for form to repeatedly submit (UI mode)
            submit_selector: CSS selector for submit button (UI mode)
            expected_result: False = expect app to resist/rate-limit, True = expect success
            authentication: Optional authentication mechanism
            execution_mode: 'ui' or 'api'
            success_indicators: Dict defining what constitutes successful flooding detection
            user_agents: List of user agents to rotate through (helps bypass simple filtering)
            randomize_timing: Whether to randomize request timing to appear more natural
        """
        super().__init__(
            name="Request Flooding / DDoS Test",
            description=f"Tests application resilience against {attack_pattern} flooding attacks with {request_count} requests",
            expected_result=expected_result,
            authentication=authentication,
            execution_mode=execution_mode
        )
        
        # Core configuration
        self.target_endpoints = target_endpoints or ['/']
        self.request_count = request_count
        self.requests_per_second = requests_per_second
        self.attack_pattern = attack_pattern.lower()
        self.concurrent_threads = min(concurrent_threads, 20)  # Cap to prevent system overload
        self.payload_data = payload_data or {}
        self.http_method = http_method.upper()
        
        # UI mode configuration
        self.form_selector = form_selector
        self.submit_selector = submit_selector
        
        # Attack sophistication
        self.user_agents = user_agents or [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101'
        ]
        self.randomize_timing = randomize_timing
        
        # Success/failure detection
        self.success_indicators = success_indicators or {
            'rate_limit_status_codes': [429, 503, 502],
            'error_keywords': ['rate limit', 'too many requests', 'service unavailable'],
            'max_response_time': 30.0,  # Consider slow responses as potential DoS impact
            'expected_success_rate': 0.1  # Expect most requests to be blocked if defenses work
        }
        
        # Attack results tracking
        self.attack_results = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'rate_limited_requests': 0,
            'error_responses': 0,
            'avg_response_time': 0.0,
            'max_response_time': 0.0,
            'responses_by_status': {},
            'attack_effectiveness': 0.0
        }

    def get_payloads(self) -> Generator[Dict[str, Any], None, None]:
        """
        Generates attack payloads based on the configured attack pattern.
        Each payload contains timing and configuration data for the attack.
        """
        base_delay = 1.0 / self.requests_per_second if self.requests_per_second > 0 else 0.1
        
        for i in range(self.request_count):
            payload = {
                'request_id': i,
                'endpoint': self.target_endpoints[i % len(self.target_endpoints)],
                'data': self.payload_data.copy(),
                'user_agent': random.choice(self.user_agents),
                'delay': self._calculate_delay(i, base_delay),
                'timeout': self._calculate_timeout(i)
            }
            
            # Add attack-pattern specific modifications
            if self.attack_pattern == 'burst':
                # Create bursts every 10 requests
                if i % 10 == 0:
                    payload['delay'] = 0.05  # Very fast burst
                else:
                    payload['delay'] = base_delay * 3  # Slower between bursts
                    
            elif self.attack_pattern == 'slowloris':
                payload['timeout'] = 60.0  # Very long timeout
                payload['delay'] = base_delay * 2  # Slower rate but longer connections
                
            elif self.attack_pattern == 'resource_exhaustion':
                # Add resource-intensive parameters
                payload['data'].update({
                    'limit': 10000,  # Request large datasets
                    'search': '*',   # Broad search terms
                    'recursive': True
                })
            
            yield payload

    def _calculate_delay(self, request_index: int, base_delay: float) -> float:
        """Calculate delay between requests based on pattern and randomization."""
        if not self.randomize_timing:
            return base_delay
            
        # Add randomization (±25% of base delay)
        jitter = base_delay * 0.25 * (random.random() - 0.5) * 2
        return max(0.01, base_delay + jitter)
    
    def _calculate_timeout(self, request_index: int) -> float:
        """Calculate request timeout based on attack pattern."""
        if self.attack_pattern == 'slowloris':
            return 60.0
        elif self.attack_pattern == 'resource_exhaustion':
            return 30.0
        else:
            return 10.0

    def execute_step(self, driver: WebDriver, payload: Dict[str, Any]) -> None:
        """
        Executes a single flooding request in UI mode.
        For UI mode, this repeatedly submits forms or navigates to pages.
        """
        try:
            endpoint = payload['endpoint']
            delay = payload['delay']
            
            # Wait for the calculated delay
            if delay > 0:
                time.sleep(delay)
            
            # Navigate to the target endpoint
            current_url = driver.current_url
            base_url = current_url.split('?')[0].rstrip('/')
            target_url = f"{base_url}{endpoint}"
            
            start_time = time.time()
            driver.get(target_url)
            
            # If we have form selectors, submit the form
            if self.form_selector and self.submit_selector:
                try:
                    # Fill form with payload data
                    for field_name, field_value in payload['data'].items():
                        try:
                            field = driver.find_element(By.NAME, field_name)
                            field.clear()
                            field.send_keys(str(field_value))
                        except NoSuchElementException:
                            # Try by ID if name doesn't work
                            try:
                                field = driver.find_element(By.ID, field_name)
                                field.clear()
                                field.send_keys(str(field_value))
                            except NoSuchElementException:
                                continue  # Skip this field if not found
                    
                    # Submit the form
                    submit_btn = driver.find_element(By.CSS_SELECTOR, self.submit_selector)
                    submit_btn.click()
                    
                except NoSuchElementException:
                    pass  # Continue even if form submission fails
            
            # Record timing
            response_time = time.time() - start_time
            self._record_ui_result(response_time, driver.current_url)
            
        except TimeoutException:
            self._record_ui_result(payload['timeout'], None, timeout=True)
        except Exception as e:
            self._record_ui_result(0.0, None, error=str(e))

    def verify_result(self, driver: WebDriver) -> bool:
        """
        Verifies the outcome of the flooding attack in UI mode.
        Checks for rate limiting, error pages, or performance degradation.
        """
        try:
            page_source = driver.page_source.lower()
            current_url = driver.current_url.lower()
            
            # Check for rate limiting indicators
            rate_limit_indicators = [
                'rate limit', 'too many requests', 'service unavailable',
                'temporarily unavailable', 'error 429', 'error 503',
                'please wait', 'slow down', 'blocked'
            ]
            
            for indicator in rate_limit_indicators:
                if indicator in page_source or indicator in current_url:
                    return not self.expected_result  # Rate limiting found
            
            # If no rate limiting found and we expected defenses, that's a failure
            return self.expected_result
            
        except Exception:
            return False

    def execute_step_api(self, session: requests.Session, payload: Dict[str, Any], context: Dict[str, Any]) -> requests.Response:
        """
        Executes a single flooding request in API mode.
        This is where the actual HTTP flooding happens.
        """
        from urllib.parse import urljoin
        
        # Build the full URL
        base_url = context.get('target_url', '')
        if not base_url:
            raise ValueError("target_url must be set in context for API mode")
        
        endpoint = payload['endpoint']
        url = urljoin(base_url, endpoint)
        
        # Prepare headers
        headers = {
            'User-Agent': payload['user_agent']
        }
        
        # Merge auth headers from context
        auth_headers = context.get('auth_headers', {})
        if auth_headers:
            headers.update(auth_headers)
        
        # Wait for the calculated delay
        delay = payload['delay']
        if delay > 0:
            time.sleep(delay)
        
        # Honor existing rate limiting from previous requests
        resume_at = context.get('rate_limit_resume_at')
        if resume_at and time.time() < resume_at:
            # Skip this request due to rate limiting
            raise requests.exceptions.RequestException("Rate limited")
        
        # Make the request
        start_time = time.time()
        try:
            if self.http_method == 'GET':
                response = session.get(
                    url, 
                    params=payload['data'],
                    headers=headers,
                    timeout=payload['timeout']
                )
            else:
                response = session.request(
                    self.http_method,
                    url,
                    json=payload['data'],
                    headers=headers,
                    timeout=payload['timeout']
                )
            
            # Record the result
            response_time = time.time() - start_time
            self._record_api_result(response, response_time, context)
            
            return response
            
        except requests.exceptions.Timeout:
            response_time = payload['timeout']
            self._record_api_result(None, response_time, context, timeout=True)
            raise
        except Exception as e:
            response_time = time.time() - start_time
            self._record_api_result(None, response_time, context, error=str(e))
            raise

    def verify_result_api(self, response: requests.Response, context: Dict[str, Any]) -> bool:
        """
        Verifies if the flooding attack was effective or if defenses kicked in.
        
        Args:
            response: The response from execute_step_api
            context: Shared context dictionary
            
        Returns:
            True if attack behavior detected (rate limiting, errors), 
            False if requests succeeded without defensive measures
        """
        # Check if we have accumulated enough results to make a determination
        total_requests = self.attack_results['total_requests']
        
        # Early determination if we have enough data
        if total_requests >= min(20, self.request_count // 2):
            success_rate = self.attack_results['successful_requests'] / total_requests
            rate_limit_rate = self.attack_results['rate_limited_requests'] / total_requests
            
            # If we expected defenses (expected_result=False)
            if not self.expected_result:
                # Good defense: high rate limiting, low success rate
                if rate_limit_rate > 0.3 or success_rate < self.success_indicators['expected_success_rate']:
                    return True
                    
            # If we expected success (expected_result=True)
            else:
                # Attack successful: high success rate, low rate limiting  
                if success_rate > 0.7 and rate_limit_rate < 0.2:
                    return True
        
        # Check immediate response indicators
        if response:
            # Rate limiting detected
            if response.status_code in self.success_indicators['rate_limit_status_codes']:
                return not self.expected_result
                
            # Check response content for defensive indicators
            try:
                response_text = response.text.lower()
                for keyword in self.success_indicators['error_keywords']:
                    if keyword in response_text:
                        return not self.expected_result
            except Exception:
                pass
        
        # Default to continuing the test
        return False

    def _record_ui_result(self, response_time: float, url: str = None, timeout: bool = False, error: str = None):
        """Record results from UI mode execution."""
        self.attack_results['total_requests'] += 1
        
        if timeout:
            self.attack_results['failed_requests'] += 1
        elif error:
            self.attack_results['error_responses'] += 1
        elif url and any(indicator in url for indicator in ['error', 'limit', '429', '503']):
            self.attack_results['rate_limited_requests'] += 1
        else:
            self.attack_results['successful_requests'] += 1
        
        # Update timing stats
        self.attack_results['max_response_time'] = max(
            self.attack_results['max_response_time'], response_time
        )
        
        # Calculate rolling average
        total = self.attack_results['total_requests']
        current_avg = self.attack_results['avg_response_time']
        self.attack_results['avg_response_time'] = (
            (current_avg * (total - 1) + response_time) / total
        )

    def _record_api_result(self, response: requests.Response = None, response_time: float = 0.0, 
                          context: Dict[str, Any] = None, timeout: bool = False, error: str = None):
        """Record results from API mode execution."""
        self.attack_results['total_requests'] += 1
        
        if timeout:
            self.attack_results['failed_requests'] += 1
        elif error:
            self.attack_results['error_responses'] += 1
        elif response:
            status_code = response.status_code
            
            # Track status code distribution
            if status_code not in self.attack_results['responses_by_status']:
                self.attack_results['responses_by_status'][status_code] = 0
            self.attack_results['responses_by_status'][status_code] += 1
            
            # Categorize the response
            if status_code in self.success_indicators['rate_limit_status_codes']:
                self.attack_results['rate_limited_requests'] += 1
                
                # Update rate limiting in context
                if context and response.headers.get('Retry-After'):
                    try:
                        retry_after = int(response.headers['Retry-After'])
                        context['rate_limit_resume_at'] = time.time() + min(retry_after, 60)
                    except (ValueError, TypeError):
                        context['rate_limit_resume_at'] = time.time() + 5
                        
            elif 200 <= status_code < 300:
                self.attack_results['successful_requests'] += 1
            else:
                self.attack_results['error_responses'] += 1
        
        # Update timing statistics
        self.attack_results['max_response_time'] = max(
            self.attack_results['max_response_time'], response_time
        )
        
        # Calculate rolling average response time
        total = self.attack_results['total_requests']
        current_avg = self.attack_results['avg_response_time']
        self.attack_results['avg_response_time'] = (
            (current_avg * (total - 1) + response_time) / total
        )
        
        # Calculate attack effectiveness score
        if total > 0:
            success_rate = self.attack_results['successful_requests'] / total
            rate_limit_rate = self.attack_results['rate_limited_requests'] / total
            
            if self.expected_result:
                # Higher success rate = more effective attack
                self.attack_results['attack_effectiveness'] = success_rate * 100
            else:
                # Higher rate limiting = more effective defenses (which we want to detect)
                self.attack_results['attack_effectiveness'] = rate_limit_rate * 100

    def get_attack_summary(self) -> Dict[str, Any]:
        """
        Returns a comprehensive summary of the attack results.
        Useful for detailed analysis and reporting.
        """
        total = self.attack_results['total_requests']
        if total == 0:
            return {"error": "No requests completed"}
        
        summary = {
            "attack_pattern": self.attack_pattern,
            "total_requests": total,
            "success_rate": (self.attack_results['successful_requests'] / total) * 100,
            "rate_limit_rate": (self.attack_results['rate_limited_requests'] / total) * 100,
            "error_rate": (self.attack_results['error_responses'] / total) * 100,
            "avg_response_time": round(self.attack_results['avg_response_time'], 3),
            "max_response_time": round(self.attack_results['max_response_time'], 3),
            "attack_effectiveness": round(self.attack_results['attack_effectiveness'], 1),
            "status_code_distribution": self.attack_results['responses_by_status'],
            "defense_assessment": self._assess_defenses()
        }
        
        return summary

    def _assess_defenses(self) -> str:
        """Assess the effectiveness of the target's defensive measures."""
        total = self.attack_results['total_requests']
        if total == 0:
            return "Insufficient data"
        
        success_rate = self.attack_results['successful_requests'] / total
        rate_limit_rate = self.attack_results['rate_limited_requests'] / total
        avg_response_time = self.attack_results['avg_response_time']
        
        if rate_limit_rate > 0.5:
            return "Strong rate limiting detected - Good defenses"
        elif rate_limit_rate > 0.2:
            return "Moderate rate limiting detected - Basic defenses"
        elif avg_response_time > 10.0:
            return "Performance degradation detected - Possible DoS impact"
        elif success_rate > 0.8:
            return "High success rate - Weak or no defenses detected"
        else:
            return "Mixed results - Some defensive measures present"