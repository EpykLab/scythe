from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException
from typing import Dict, Any, Optional
import requests

from ...core.ttp import TTP
from ...payloads.generators import PayloadGenerator

class InputFieldInjector(TTP):
    """
    SQL Injection TTP that tests input fields for SQL injection vulnerabilities.
    
    Supports two execution modes:
    - UI mode: Fills form fields with SQL payloads
    - API mode: Sends SQL payloads in API request body fields
    """
    def __init__(self,
                 target_url: str = None,
                 field_selector: str = None,
                 submit_selector: str = None,
                 payload_generator: PayloadGenerator = None,
                 expected_result: bool = True,
                 authentication=None,
                 execution_mode: str = 'ui',
                 api_endpoint: Optional[str] = None,
                 injection_field: str = 'query',
                 http_method: str = 'POST'):
        """
        Initialize the SQL Injection TTP.
        
        Args:
            target_url: Target URL (UI mode)
            field_selector: CSS/tag selector for input field (UI mode)
            submit_selector: CSS selector for submit button (UI mode)
            payload_generator: Generator that yields SQL injection payloads
            expected_result: Whether we expect to find SQL injection vulnerabilities
            authentication: Optional authentication
            execution_mode: 'ui' or 'api'
            api_endpoint: API endpoint path (API mode, e.g., '/api/search')
            injection_field: Field name to inject SQL payload into (API mode)
            http_method: HTTP method to use (API mode) - 'POST' or 'GET'
        """
        super().__init__(
            name="SQL Injection via Input Field", 
            description="Simulate SQL injection by injecting payloads into input fields",
            expected_result=expected_result,
            authentication=authentication,
            execution_mode=execution_mode)

        # UI mode fields
        self.target_url = target_url
        self.field_selector = field_selector
        self.submit_selector = submit_selector
        
        # Common fields
        self.payload_generator = payload_generator
        
        # API mode fields
        self.api_endpoint = api_endpoint
        self.injection_field = injection_field
        self.http_method = http_method.upper()

    def get_payloads(self):
        """yields queries from the configured generator"""
        yield from self.payload_generator()

    def execute_step(self, driver: WebDriver, payload: str):
        """fills in a form field with an SQL payload and injects it"""
        try:
            """define the field"""
            field = driver.find_element(By.TAG_NAME, self.field_selector)

            """clear the field"""
            field.clear()

            field.send_keys(payload)

            try:
                submit_button = driver.find_element(By.CSS_SELECTOR, self.submit_selector)

                submit_button.click()
            except NoSuchElementException:
                field.send_keys("\n")

        except NoSuchElementException as e:
            raise Exception(f"could not find input field on page: {e}")


    def verify_result(self, driver: WebDriver) -> bool:
        """Checks for SQL error indicators in the page source (UI mode)."""
        return "sql" in driver.page_source.lower() or \
               "source" in driver.page_source.lower()
    
    def execute_step_api(self, session: requests.Session, payload: str, context: Dict[str, Any]) -> requests.Response:
        """
        Executes a SQL injection attempt via API request.
        
        Args:
            session: requests.Session for making HTTP requests
            payload: The SQL injection payload to test
            context: Shared context dictionary
            
        Returns:
            requests.Response from the injection attempt
        """
        from urllib.parse import urljoin
        
        # Build the full URL
        base_url = context.get('target_url', '')
        if not base_url:
            raise ValueError("target_url must be set in context for API mode")
        
        url = urljoin(base_url, self.api_endpoint or '/search')
        
        # Merge auth headers from context
        headers = {}
        auth_headers = context.get('auth_headers', {})
        if auth_headers:
            headers.update(auth_headers)
        
        # Honor rate limiting
        import time
        resume_at = context.get('rate_limit_resume_at')
        now = time.time()
        if isinstance(resume_at, (int, float)) and resume_at > now:
            wait_s = min(resume_at - now, 30)
            if wait_s > 0:
                time.sleep(wait_s)
        
        # Make the request based on HTTP method
        if self.http_method == 'GET':
            # For GET, put payload in query params
            response = session.get(url, params={self.injection_field: payload}, headers=headers or None, timeout=10.0)
        else:
            # For POST/PUT/etc, put payload in JSON body
            body = {self.injection_field: payload}
            response = session.request(self.http_method, url, json=body, headers=headers or None, timeout=10.0)
        
        # Handle rate limiting
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After', '1')
            try:
                wait_s = int(retry_after)
            except (ValueError, TypeError):
                wait_s = 1
            context['rate_limit_resume_at'] = time.time() + min(wait_s, 30)
        
        return response
    
    def verify_result_api(self, response: requests.Response, context: Dict[str, Any]) -> bool:
        """
        Verifies if the SQL injection attempt triggered a vulnerability.
        
        Args:
            response: The response from execute_step_api
            context: Shared context dictionary
            
        Returns:
            True if SQL error indicators found, False otherwise
        """
        try:
            response_text = response.text.lower()
            # Common SQL error indicators
            sql_indicators = [
                'sql', 'syntax', 'mysql', 'sqlite', 'postgresql', 'oracle',
                'odbc', 'jdbc', 'driver', 'database', 'query', 'syntax error',
                'unterminated', 'unexpected', 'warning: mysql'
            ]
            return any(indicator in response_text for indicator in sql_indicators)
        except Exception:
            return False


class URLManipulation(TTP):
    """
    SQL Injection TTP that tests URL query parameters for SQL injection vulnerabilities.
    
    Supports two execution modes:
    - UI mode: Navigates to URLs with SQL payloads in query parameters
    - API mode: Sends GET requests with SQL payloads in query parameters
    """
    def __init__(self,
                 payload_generator: PayloadGenerator,
                 target_url: str = None,
                 expected_result: bool = True,
                 authentication=None,
                 execution_mode: str = 'ui',
                 api_endpoint: Optional[str] = None,
                 query_param: str = 'q'):
        """
        Initialize the URL Manipulation SQL Injection TTP.
        
        Args:
            payload_generator: Generator that yields SQL injection payloads
            target_url: Target URL (UI mode)
            expected_result: Whether we expect to find SQL injection vulnerabilities
            authentication: Optional authentication
            execution_mode: 'ui' or 'api'
            api_endpoint: API endpoint path (API mode, e.g., '/api/search')
            query_param: Query parameter name to inject into (default: 'q')
        """
        super().__init__(
            name="SQL Injection via URL manipulation", 
            description="Simulate SQL injection by manipulating URL query parameters",
            expected_result=expected_result,
            authentication=authentication,
            execution_mode=execution_mode)
        self.target_url = target_url
        self.payload_generator = payload_generator
        self.api_endpoint = api_endpoint
        self.query_param = query_param

    def get_payloads(self):
        yield from self.payload_generator()

    def execute_step(self, driver: WebDriver, payload: str):
        """Execute SQL injection via URL manipulation in UI mode."""
        driver.get(f"{self.target_url}?{self.query_param}={payload}")

    def verify_result(self, driver: WebDriver) -> bool:
        """Check for SQL error indicators in UI mode."""
        return "sql" in driver.page_source.lower() or \
               "source" in driver.page_source.lower()
    
    def execute_step_api(self, session: requests.Session, payload: str, context: Dict[str, Any]) -> requests.Response:
        """
        Executes a SQL injection attempt via API request with query parameters.
        
        Args:
            session: requests.Session for making HTTP requests
            payload: The SQL injection payload to test
            context: Shared context dictionary
            
        Returns:
            requests.Response from the injection attempt
        """
        from urllib.parse import urljoin
        
        # Build the full URL
        base_url = context.get('target_url', '')
        if not base_url:
            raise ValueError("target_url must be set in context for API mode")
        
        url = urljoin(base_url, self.api_endpoint or self.target_url or '/')
        
        # Merge auth headers from context
        headers = {}
        auth_headers = context.get('auth_headers', {})
        if auth_headers:
            headers.update(auth_headers)
        
        # Honor rate limiting
        import time
        resume_at = context.get('rate_limit_resume_at')
        now = time.time()
        if isinstance(resume_at, (int, float)) and resume_at > now:
            wait_s = min(resume_at - now, 30)
            if wait_s > 0:
                time.sleep(wait_s)
        
        # Make GET request with payload in query param
        response = session.get(url, params={self.query_param: payload}, headers=headers or None, timeout=10.0)
        
        # Handle rate limiting
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After', '1')
            try:
                wait_s = int(retry_after)
            except (ValueError, TypeError):
                wait_s = 1
            context['rate_limit_resume_at'] = time.time() + min(wait_s, 30)
        
        return response
    
    def verify_result_api(self, response: requests.Response, context: Dict[str, Any]) -> bool:
        """
        Verifies if the SQL injection attempt triggered a vulnerability.
        
        Args:
            response: The response from execute_step_api
            context: Shared context dictionary
            
        Returns:
            True if SQL error indicators found, False otherwise
        """
        try:
            response_text = response.text.lower()
            # Common SQL error indicators
            sql_indicators = [
                'sql', 'syntax', 'mysql', 'sqlite', 'postgresql', 'oracle',
                'odbc', 'jdbc', 'driver', 'database', 'query', 'syntax error',
                'unterminated', 'unexpected', 'warning: mysql'
            ]
            return any(indicator in response_text for indicator in sql_indicators)
        except Exception:
            return False
