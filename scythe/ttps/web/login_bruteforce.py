from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import NoSuchElementException
from typing import Dict, Any, Optional
import requests

from ...core.ttp import TTP
from ...payloads.generators import PayloadGenerator

class LoginBruteforceTTP(TTP):
    """
    A TTP that emulates a login bruteforce attack.
    
    Supports two execution modes:
    - UI mode: Uses Selenium to fill login forms
    - API mode: Makes direct HTTP POST requests to login endpoints
    """
    def __init__(self,
                 payload_generator: PayloadGenerator,
                 username: str,
                 username_selector: str = None,
                 password_selector: str = None,
                 submit_selector: str = None,
                 expected_result: bool = True,
                 authentication=None,
                 execution_mode: str = 'ui',
                 api_endpoint: Optional[str] = None,
                 username_field: str = 'username',
                 password_field: str = 'password',
                 success_indicators: Optional[Dict[str, Any]] = None):
        """
        Initialize the Login Bruteforce TTP.
        
        Args:
            payload_generator: Generator that yields password payloads
            username: Username to attempt login with
            username_selector: CSS selector for username field (UI mode)
            password_selector: CSS selector for password field (UI mode)
            submit_selector: CSS selector for submit button (UI mode)
            expected_result: Whether we expect to find a valid password
            authentication: Optional authentication to perform before testing
            execution_mode: 'ui' or 'api'
            api_endpoint: API endpoint path for login (API mode, e.g., '/api/auth/login')
            username_field: Field name for username in API request body (API mode)
            password_field: Field name for password in API request body (API mode)
            success_indicators: Dict with keys 'status_code' (int), 'response_contains' (str),
                              'response_not_contains' (str) to determine successful login in API mode
        """
        super().__init__(
            name="Login Bruteforce",
            description="Attempts to guess a user's password using a list of payloads.",
            expected_result=expected_result,
            authentication=authentication,
            execution_mode=execution_mode
        )
        self.payload_generator = payload_generator
        self.username = username
        
        # UI mode fields
        self.username_selector = username_selector
        self.password_selector = password_selector
        self.submit_selector = submit_selector
        
        # API mode fields
        self.api_endpoint = api_endpoint
        self.username_field = username_field
        self.password_field = password_field
        self.success_indicators = success_indicators or {
            'status_code': 200,
            'response_not_contains': 'invalid'
        }

    def get_payloads(self):
        """Yields passwords from the configured generator."""
        yield from self.payload_generator()

    def execute_step(self, driver: WebDriver, payload: str):
        """Fills the login form and submits it."""
        try:
            username_field = driver.find_element(By.CSS_SELECTOR, self.username_selector)
            password_field = driver.find_element(By.CSS_SELECTOR, self.password_selector)

            username_field.clear()
            username_field.send_keys(self.username)

            password_field.clear()
            password_field.send_keys(payload) # Payload is the password

            # Use submit button if available, otherwise press Enter on the password field
            try:
                submit_button = driver.find_element(By.CSS_SELECTOR, self.submit_selector)
                submit_button.click()
            except NoSuchElementException:
                password_field.send_keys("\n")

        except NoSuchElementException as e:
            raise Exception(f"Could not find a login element on the page: {e}")

    def verify_result(self, driver: WebDriver) -> bool:
        """
        Checks for indicators of a successful login in UI mode.
        A simple check is if the URL no longer contains 'login'.
        """
        return "login" not in driver.current_url.lower()
    
    def execute_step_api(self, session: requests.Session, payload: str, context: Dict[str, Any]) -> requests.Response:
        """
        Executes a login attempt via API request.
        
        Args:
            session: requests.Session for making HTTP requests
            payload: The password to attempt
            context: Shared context dictionary
            
        Returns:
            requests.Response from the login attempt
        """
        from urllib.parse import urljoin
        
        # Build the full URL
        base_url = context.get('target_url', '')
        if not base_url:
            raise ValueError("target_url must be set in context for API mode")
        
        url = urljoin(base_url, self.api_endpoint or '/login')
        
        # Build request body
        body = {
            self.username_field: self.username,
            self.password_field: payload
        }
        
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
        
        # Make the request
        response = session.post(url, json=body, headers=headers or None, timeout=10.0)
        
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
        Verifies if the login attempt was successful based on the API response.
        
        Args:
            response: The response from execute_step_api
            context: Shared context dictionary
            
        Returns:
            True if login appears successful, False otherwise
        """
        # Check status code
        expected_status = self.success_indicators.get('status_code')
        if expected_status is not None and response.status_code != expected_status:
            return False
        
        # Check response body contains/not contains strings
        try:
            response_text = response.text.lower()
            
            # Check if response should contain certain text
            contains = self.success_indicators.get('response_contains')
            if contains and contains.lower() not in response_text:
                return False
            
            # Check if response should NOT contain certain text
            not_contains = self.success_indicators.get('response_not_contains')
            if not_contains and not_contains.lower() in response_text:
                return False
            
            return True
        except Exception:
            # If we can't read the response, consider it a failure
            return False
