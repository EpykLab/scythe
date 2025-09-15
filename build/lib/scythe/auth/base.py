from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from selenium.webdriver.remote.webdriver import WebDriver


class Authentication(ABC):
    """
    Abstract base class for authentication mechanisms.
    
    This class defines the interface for authentication methods that can be
    used with TTPs to authenticate before executing the main test logic.
    """
    
    def __init__(self, name: str, description: str):
        """
        Initialize the authentication mechanism.
        
        Args:
            name: Name of the authentication method
            description: Description of what this authentication does
        """
        self.name = name
        self.description = description
        self.authenticated = False
        self.auth_data = {}
    
    @abstractmethod
    def authenticate(self, driver: WebDriver, target_url: str) -> bool:
        """
        Perform authentication using the provided WebDriver.
        
        Args:
            driver: The WebDriver instance to use for authentication
            target_url: The target URL where authentication should be performed
            
        Returns:
            True if authentication was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_authenticated(self, driver: WebDriver) -> bool:
        """
        Check if the current session is authenticated.
        
        Args:
            driver: The WebDriver instance to check
            
        Returns:
            True if authenticated, False otherwise
        """
        pass
    
    def logout(self, driver: WebDriver) -> bool:
        """
        Log out from the current session.
        
        Args:
            driver: The WebDriver instance to use for logout
            
        Returns:
            True if logout was successful, False otherwise
        """
        # Default implementation - clear cookies and local storage
        try:
            driver.delete_all_cookies()
            driver.execute_script("localStorage.clear();")
            driver.execute_script("sessionStorage.clear();")
            self.authenticated = False
            return True
        except Exception:
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers that can be used for API requests.
        
        Returns:
            Dictionary of headers to include in requests
        """
        return {}
    
    def get_auth_cookies(self) -> Dict[str, str]:
        """
        Get authentication cookies that should be set for API requests.
        
        Returns:
            Dictionary mapping cookie name to cookie value.
        """
        return {}
    
    def store_auth_data(self, key: str, value: Any) -> None:
        """
        Store authentication-related data.
        
        Args:
            key: The key to store the data under
            value: The value to store
        """
        self.auth_data[key] = value
    
    def get_auth_data(self, key: str, default: Any = None) -> Any:
        """
        Retrieve authentication-related data.
        
        Args:
            key: The key to retrieve data for
            default: Default value if key is not found
            
        Returns:
            The stored value or default
        """
        return self.auth_data.get(key, default)
    
    def clear_auth_data(self) -> None:
        """Clear all stored authentication data."""
        self.auth_data.clear()
        self.authenticated = False


class AuthenticationError(Exception):
    """Exception raised when authentication fails."""
    
    def __init__(self, message: str, auth_method: Optional[str] = None):
        self.auth_method = auth_method
        super().__init__(message)