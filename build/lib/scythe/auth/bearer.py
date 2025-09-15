import time
from typing import Dict, Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from .base import Authentication, AuthenticationError


class BearerTokenAuth(Authentication):
    """
    Bearer token authentication for APIs and web applications.
    
    This authentication method supports both direct token provision and
    token acquisition through login flows.
    """
    
    def __init__(self, 
                 token: Optional[str] = None,
                 token_url: Optional[str] = None,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 token_field_name: str = "access_token",
                 auth_header_name: str = "Authorization",
                 auth_header_prefix: str = "Bearer"):
        """
        Initialize Bearer Token Authentication.
        
        Args:
            token: Pre-existing bearer token (if available)
            token_url: URL to obtain token from (for login-based auth)
            username: Username for token acquisition
            password: Password for token acquisition
            token_field_name: Field name in response containing the token
            auth_header_name: Header name for authentication
            auth_header_prefix: Prefix for the auth header value
        """
        super().__init__(
            name="Bearer Token Authentication",
            description="Authenticates using bearer tokens for API access"
        )
        
        self.token = token
        self.token_url = token_url
        self.username = username
        self.password = password
        self.token_field_name = token_field_name
        self.auth_header_name = auth_header_name
        self.auth_header_prefix = auth_header_prefix
        
        if token:
            self.authenticated = True
            self.store_auth_data('token', token)
    
    def authenticate(self, driver: WebDriver, target_url: str) -> bool:
        """
        Perform bearer token authentication.
        
        Args:
            driver: WebDriver instance
            target_url: Target URL for authentication
            
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # If we already have a token, verify it's still valid
            if self.token:
                if self._verify_token(driver, target_url):
                    self.authenticated = True
                    return True
                else:
                    # Token might be expired, try to get a new one
                    self.token = None
                    self.authenticated = False
            
            # If we don't have a token, try to acquire one
            if not self.token and self.token_url and self.username and self.password:
                return self._acquire_token(driver)
            
            # If we still don't have a token, authentication failed
            if not self.token:
                raise AuthenticationError(
                    "No valid bearer token available and cannot acquire one",
                    self.name
                )
            
            return self.authenticated
            
        except Exception as e:
            raise AuthenticationError(f"Bearer token authentication failed: {str(e)}", self.name)
    
    def _acquire_token(self, driver: WebDriver) -> bool:
        """
        Acquire a bearer token through login flow.
        
        Args:
            driver: WebDriver instance
            
        Returns:
            True if token acquisition successful, False otherwise
        """
        try:
            # Navigate to token acquisition URL
            if self.token_url:
                driver.get(self.token_url)
            else:
                raise AuthenticationError("No token URL provided")
            
            # This is a simplified implementation
            # In practice, this would need to handle various login flows
            # For now, we'll assume the token URL provides a simple login form
            
            # Try to find username/email field
            username_selectors = [
                "input[name='username']",
                "input[name='email']", 
                "input[type='email']",
                "#username",
                "#email",
                ".username",
                ".email"
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    username_field = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not username_field:
                raise AuthenticationError("Could not find username/email field")
            
            # Try to find password field
            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "#password",
                ".password"
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not password_field:
                raise AuthenticationError("Could not find password field")
            
            # Fill in credentials
            username_field.clear()
            if self.username:
                username_field.send_keys(self.username)
            
            password_field.clear()
            if self.password:
                password_field.send_keys(self.password)
            
            # Try to find and click submit button
            submit_selectors = [
                "input[type='submit']",
                "button[type='submit']",
                "button",
                ".submit",
                ".login"
            ]
            
            for selector in submit_selectors:
                try:
                    submit_button = driver.find_element(By.CSS_SELECTOR, selector)
                    submit_button.click()
                    break
                except NoSuchElementException:
                    continue
            else:
                # If no submit button found, try pressing Enter
                password_field.send_keys("\n")
            
            # Wait for response and extract token
            time.sleep(2)  # Give time for response
            
            # Try to extract token from page content or localStorage
            token = self._extract_token_from_page(driver)
            
            if token:
                self.token = token
                self.store_auth_data('token', token)
                self.authenticated = True
                return True
            else:
                raise AuthenticationError("Could not extract token from response")
                
        except Exception as e:
            raise AuthenticationError(f"Token acquisition failed: {str(e)}")
    
    def _extract_token_from_page(self, driver: WebDriver) -> Optional[str]:
        """
        Extract token from page content or browser storage.
        
        Args:
            driver: WebDriver instance
            
        Returns:
            Extracted token or None
        """
        # Try to get token from localStorage
        try:
            token = driver.execute_script(f"return localStorage.getItem('{self.token_field_name}');")
            if token:
                return token
        except Exception:
            pass
        
        # Try to get token from sessionStorage
        try:
            token = driver.execute_script(f"return sessionStorage.getItem('{self.token_field_name}');")
            if token:
                return token
        except Exception:
            pass
        
        # Try to extract from page source (JSON response)
        try:
            page_source = driver.page_source.lower()
            if self.token_field_name.lower() in page_source:
                # This is a simple extraction - in practice you'd want more robust JSON parsing
                import re
                pattern = f'"{self.token_field_name}"\\s*:\\s*"([^"]+)"'
                match = re.search(pattern, page_source, re.IGNORECASE)
                if match:
                    return match.group(1)
        except Exception:
            pass
        
        return None
    
    def _verify_token(self, driver: WebDriver, target_url: str) -> bool:
        """
        Verify if the current token is still valid.
        
        Args:
            driver: WebDriver instance
            target_url: Target URL to test against
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Try to access a protected resource with the token
            # This would typically involve adding the Authorization header
            # For web apps, we might check if we can access a protected page
            
            # Add authorization header to subsequent requests
            self._inject_auth_header(driver)
            
            # Try to access the target URL
            driver.get(target_url)
            
            # Check if we get an auth error (simple heuristic)
            page_source = driver.page_source.lower()
            auth_error_indicators = [
                "unauthorized", "401", "forbidden", "403", 
                "access denied", "login required", "authentication failed"
            ]
            
            for indicator in auth_error_indicators:
                if indicator in page_source:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _inject_auth_header(self, driver: WebDriver) -> None:
        """
        Inject authorization header for subsequent requests.
        
        Args:
            driver: WebDriver instance
        """
        if not self.token:
            return
        
        # Use CDP (Chrome DevTools Protocol) to add headers if available
        try:
            auth_value = f"{self.auth_header_prefix} {self.token}"
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": driver.execute_script("return navigator.userAgent;"),
                "headers": {self.auth_header_name: auth_value}
            })
        except Exception:
            # If CDP is not available, store in localStorage for JS access
            try:
                driver.execute_script(
                    f"localStorage.setItem('auth_token', '{self.token}');"
                )
            except Exception:
                pass
    
    def is_authenticated(self, driver: WebDriver) -> bool:
        """
        Check if currently authenticated.
        
        Args:
            driver: WebDriver instance
            
        Returns:
            True if authenticated, False otherwise
        """
        return self.authenticated and self.token is not None
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.
        
        Returns:
            Dictionary containing authorization header
        """
        if self.token:
            return {
                self.auth_header_name: f"{self.auth_header_prefix} {self.token}"
            }
        return {}
    
    def logout(self, driver: WebDriver) -> bool:
        """
        Logout and clear bearer token.
        
        Args:
            driver: WebDriver instance
            
        Returns:
            True if logout successful
        """
        try:
            # Clear the token
            self.token = None
            self.authenticated = False
            self.clear_auth_data()
            
            # Clear browser storage
            super().logout(driver)
            
            # Clear any stored auth tokens
            try:
                driver.execute_script("localStorage.removeItem('auth_token');")
                driver.execute_script(f"localStorage.removeItem('{self.token_field_name}');")
                driver.execute_script(f"sessionStorage.removeItem('{self.token_field_name}');")
            except Exception:
                pass
            
            return True
            
        except Exception:
            return False