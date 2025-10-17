from abc import ABC, abstractmethod
from typing import Generator, Any, Optional, TYPE_CHECKING, Dict
from selenium.webdriver.remote.webdriver import WebDriver

if TYPE_CHECKING:
    from ..auth.base import Authentication
    import requests

class TTP(ABC):
    """
    Abstract Base Class for a single Tactic, Technique, and Procedure (TTP).

    Each TTP implementation must define how to generate payloads, how to
    execute a test step with a given payload, and how to verify the outcome.
    
    TTPs can operate in two modes:
    - 'ui': Uses Selenium WebDriver to interact with web UI (default)
    - 'api': Uses requests library to interact directly with backend APIs
    """

    def __init__(self, name: str, description: str, expected_result: bool = True, 
                 authentication: Optional['Authentication'] = None, execution_mode: str = 'ui'):
        """
        Initialize a TTP.
        
        Args:
            name: Name of the TTP
            description: Description of what the TTP does
            expected_result: Whether this TTP is expected to pass (True) or fail (False).
                           True means we expect to find vulnerabilities/success conditions.
                           False means we expect the security controls to prevent success.
            authentication: Optional authentication mechanism to use before executing TTP
            execution_mode: Execution mode - 'ui' for Selenium-based UI testing or 'api' for direct API testing
        """
        self.name = name
        self.description = description
        self.expected_result = expected_result
        self.authentication = authentication
        self.execution_mode = execution_mode.lower()

    @abstractmethod
    def get_payloads(self) -> Generator[Any, None, None]:
        """Yields payloads for the test execution."""
        pass

    @abstractmethod
    def execute_step(self, driver: WebDriver, payload: Any) -> None:
        """
        Executes a single test action using the provided payload.
        This method should perform the action (e.g., fill form, click button).
        """
        pass
    
    def requires_authentication(self) -> bool:
        """
        Check if this TTP requires authentication.
        
        Returns:
            True if authentication is required, False otherwise
        """
        return self.authentication is not None
    
    def authenticate(self, driver: WebDriver, target_url: str) -> bool:
        """
        Perform authentication if required.
        
        Args:
            driver: WebDriver instance
            target_url: Target URL for authentication
            
        Returns:
            True if authentication successful or not required, False if auth failed
        """
        if not self.requires_authentication():
            return True
        
        try:
            if self.authentication:
                return self.authentication.authenticate(driver, target_url)
            return False
        except Exception as e:
            # Import here to avoid circular imports
            import logging
            logger = logging.getLogger(self.name)
            logger.error(f"Authentication failed: {str(e)}")
            return False

    @abstractmethod
    def verify_result(self, driver: WebDriver) -> bool:
        """
        Verifies the outcome of the executed step in UI mode.

        Returns:
            True if the test indicates a potential success/vulnerability, False otherwise.
        """
        pass
    
    def execute_step_api(self, session: 'requests.Session', payload: Any, context: Dict[str, Any]) -> 'requests.Response':
        """
        Executes a single test action using the provided payload via API request.
        This method should be overridden by TTPs that support API mode.
        
        Args:
            session: requests.Session instance for making HTTP requests
            payload: The payload to use for this test iteration
            context: Shared context dictionary for storing state and auth headers
            
        Returns:
            requests.Response object from the API call
            
        Raises:
            NotImplementedError: If the TTP does not support API mode
        """
        raise NotImplementedError(f"{self.name} does not support API execution mode")
    
    def verify_result_api(self, response: 'requests.Response', context: Dict[str, Any]) -> bool:
        """
        Verifies the outcome of the executed step in API mode.
        This method should be overridden by TTPs that support API mode.
        
        Args:
            response: The requests.Response object from execute_step_api
            context: Shared context dictionary for accessing state
            
        Returns:
            True if the test indicates a potential success/vulnerability, False otherwise
            
        Raises:
            NotImplementedError: If the TTP does not support API mode
        """
        raise NotImplementedError(f"{self.name} does not support API result verification in API mode")
    
    def supports_api_mode(self) -> bool:
        """
        Check if this TTP implementation supports API execution mode.
        
        Returns:
            True if API mode is supported, False otherwise
        """
        # Check if the TTP has overridden the API methods
        try:
            # Try to call the method on the class to see if it's been overridden
            return (type(self).execute_step_api != TTP.execute_step_api or 
                    type(self).verify_result_api != TTP.verify_result_api)
        except Exception:
            return False
