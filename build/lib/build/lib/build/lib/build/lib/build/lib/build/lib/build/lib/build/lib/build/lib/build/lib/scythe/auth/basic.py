import time
from typing import Optional, List
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from .base import Authentication, AuthenticationError


class BasicAuth(Authentication):
    """
    Basic authentication for form-based login systems.
    
    This authentication method handles traditional username/password forms
    commonly found in web applications.
    """
    
    def __init__(self, 
                 username: str,
                 password: str,
                 login_url: Optional[str] = None,
                 username_selector: Optional[str] = None,
                 password_selector: Optional[str] = None,
                 submit_selector: Optional[str] = None,
                 success_indicators: Optional[List[str]] = None,
                 failure_indicators: Optional[List[str]] = None):
        """
        Initialize Basic Authentication.
        
        Args:
            username: Username for authentication
            password: Password for authentication
            login_url: URL of the login page (if different from target)
            username_selector: CSS selector for username field
            password_selector: CSS selector for password field
            submit_selector: CSS selector for submit button
            success_indicators: List of strings/selectors that indicate successful login
            failure_indicators: List of strings/selectors that indicate failed login
        """
        super().__init__(
            name="Basic Authentication",
            description="Authenticates using username and password forms"
        )
        
        self.username = username
        self.password = password
        self.login_url = login_url
        self.username_selector = username_selector
        self.password_selector = password_selector
        self.submit_selector = submit_selector
        
        # Default success indicators
        self.success_indicators = success_indicators or [
            "dashboard", "welcome", "logout", "profile", "account",
            "home", "main", "success"
        ]
        
        # Default failure indicators
        self.failure_indicators = failure_indicators or [
            "error", "invalid", "incorrect", "failed", "denied",
            "unauthorized", "login failed", "authentication failed"
        ]
    
    def authenticate(self, driver: WebDriver, target_url: str) -> bool:
        """
        Perform basic authentication using username and password.
        
        Args:
            driver: WebDriver instance
            target_url: Target URL for authentication
            
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Check if already authenticated
            if self.is_authenticated(driver):
                return True
            
            # Navigate to login page
            login_page = self.login_url or target_url
            driver.get(login_page)
            
            # Wait for page to load
            time.sleep(1)
            
            # Find and fill username field
            username_field = self._find_username_field(driver)
            if not username_field:
                raise AuthenticationError("Could not find username field")
            
            username_field.clear()
            username_field.send_keys(self.username)
            
            # Find and fill password field
            password_field = self._find_password_field(driver)
            if not password_field:
                raise AuthenticationError("Could not find password field")
            
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Submit the form
            if not self._submit_form(driver, password_field):
                raise AuthenticationError("Could not submit login form")
            
            # Wait for response
            time.sleep(2)
            
            # Check if authentication was successful
            if self._check_authentication_result(driver):
                self.authenticated = True
                self.store_auth_data('username', self.username)
                self.store_auth_data('login_time', time.time())
                return True
            else:
                raise AuthenticationError("Authentication failed - invalid credentials or login error")
                
        except Exception as e:
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(f"Basic authentication failed: {str(e)}", self.name)
    
    def _find_username_field(self, driver: WebDriver):
        """
        Find the username input field using various selectors.
        
        Args:
            driver: WebDriver instance
            
        Returns:
            WebElement for username field or None
        """
        # If specific selector provided, use it
        if self.username_selector:
            try:
                return driver.find_element(By.CSS_SELECTOR, self.username_selector)
            except NoSuchElementException:
                pass
        
        # Try common username field selectors
        username_selectors = [
            "input[name='username']",
            "input[name='email']",
            "input[name='user']",
            "input[name='login']",
            "input[id='username']",
            "input[id='email']",
            "input[id='user']",
            "input[id='login']",
            "input[type='email']",
            "input[class*='username']",
            "input[class*='email']",
            "input[class*='user']",
            "input[placeholder*='username' i]",
            "input[placeholder*='email' i]",
            "input[placeholder*='user' i]",
            "input[data-testid*='username']",
            "input[data-testid*='email']"
        ]
        
        for selector in username_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed() and element.is_enabled():
                    return element
            except NoSuchElementException:
                continue
        
        return None
    
    def _find_password_field(self, driver: WebDriver):
        """
        Find the password input field using various selectors.
        
        Args:
            driver: WebDriver instance
            
        Returns:
            WebElement for password field or None
        """
        # If specific selector provided, use it
        if self.password_selector:
            try:
                return driver.find_element(By.CSS_SELECTOR, self.password_selector)
            except NoSuchElementException:
                pass
        
        # Try common password field selectors
        password_selectors = [
            "input[name='password']",
            "input[name='passwd']",
            "input[name='pass']",
            "input[id='password']",
            "input[id='passwd']",
            "input[id='pass']",
            "input[type='password']",
            "input[class*='password']",
            "input[placeholder*='password' i]",
            "input[data-testid*='password']"
        ]
        
        for selector in password_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed() and element.is_enabled():
                    return element
            except NoSuchElementException:
                continue
        
        return None
    
    def _submit_form(self, driver: WebDriver, password_field) -> bool:
        """
        Submit the login form.
        
        Args:
            driver: WebDriver instance
            password_field: Password field element for fallback Enter key
            
        Returns:
            True if form was submitted successfully
        """
        # If specific submit selector provided, use it
        if self.submit_selector:
            try:
                submit_button = driver.find_element(By.CSS_SELECTOR, self.submit_selector)
                submit_button.click()
                return True
            except NoSuchElementException:
                pass
        
        # Try common submit button selectors
        submit_selectors = [
            "input[type='submit']",
            "button[type='submit']",
            "button[id*='login']",
            "button[id*='submit']",
            "button[class*='login']",
            "button[class*='submit']",
            "input[value*='login' i]",
            "input[value*='sign in' i]",
            "button[data-testid*='login']",
            "button[data-testid*='submit']",
            "a[class*='login']"
        ]
        
        for selector in submit_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed() and element.is_enabled():
                    element.click()
                    return True
            except NoSuchElementException:
                continue
        
        # Fallback: press Enter on password field
        try:
            password_field.send_keys("\n")
            return True
        except Exception:
            return False
    
    def _check_authentication_result(self, driver: WebDriver) -> bool:
        """
        Check if authentication was successful by looking for indicators.
        
        Args:
            driver: WebDriver instance
            
        Returns:
            True if authentication appears successful
        """
        current_url = driver.current_url.lower()
        page_source = driver.page_source.lower()
        
        # Check for failure indicators first
        for indicator in self.failure_indicators:
            if indicator.lower() in page_source or indicator.lower() in current_url:
                return False
        
        # Check for success indicators
        for indicator in self.success_indicators:
            if indicator.lower() in page_source or indicator.lower() in current_url:
                return True
        
        # Check if URL changed (indicating redirect after successful login)
        if self.login_url and current_url != self.login_url.lower():
            # If we're no longer on the login page, likely successful
            login_indicators = ["login", "signin", "auth"]
            for indicator in login_indicators:
                if indicator in current_url:
                    return False  # Still on login-like page
            return True
        
        # Look for common authenticated elements
        authenticated_elements = [
            "logout", "sign out", "profile", "account", "dashboard",
            "menu", "navigation", "user menu"
        ]
        
        for element_text in authenticated_elements:
            try:
                # Look for elements containing these terms
                xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{element_text}')]"
                elements = driver.find_elements(By.XPATH, xpath)
                if elements:
                    return True
            except Exception:
                continue
        
        # Default to False if we can't determine success
        return False
    
    def is_authenticated(self, driver: WebDriver) -> bool:
        """
        Check if currently authenticated.
        
        Args:
            driver: WebDriver instance
            
        Returns:
            True if authenticated, False otherwise
        """
        if not self.authenticated:
            return False
        
        # Check if session is still valid
        try:
            page_source = driver.page_source.lower()
            current_url = driver.current_url.lower()
            
            # Look for logout indicators (suggests we're logged in)
            logout_indicators = ["logout", "sign out", "log out"]
            for indicator in logout_indicators:
                if indicator in page_source:
                    return True
            
            # Check if we're on a login page (suggests we're not logged in)
            login_indicators = ["login", "signin", "sign in", "authenticate"]
            for indicator in login_indicators:
                if indicator in current_url:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def logout(self, driver: WebDriver) -> bool:
        """
        Logout from the current session.
        
        Args:
            driver: WebDriver instance
            
        Returns:
            True if logout successful
        """
        try:
            # Try to find and click logout button/link
            logout_selectors = [
                "a[href*='logout']",
                "button[id*='logout']",
                "a[id*='logout']",
                "button[class*='logout']",
                "a[class*='logout']",
                "*[data-testid*='logout']",
                "a[href*='signout']",
                "a[href*='sign-out']"
            ]
            
            for selector in logout_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        element.click()
                        time.sleep(1)
                        break
                except NoSuchElementException:
                    continue
            
            # Clear authentication state
            self.authenticated = False
            self.clear_auth_data()
            
            # Clear browser storage
            super().logout(driver)
            
            return True
            
        except Exception:
            return False
    
    def get_auth_headers(self) -> dict:
        """
        Get authentication headers.
        
        For basic auth, this would typically return empty dict
        as authentication is session-based.
        
        Returns:
            Empty dictionary (session-based auth)
        """
        return {}