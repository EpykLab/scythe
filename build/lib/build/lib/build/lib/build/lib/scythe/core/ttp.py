from abc import ABC, abstractmethod
from typing import Generator, Any, Optional, TYPE_CHECKING
from selenium.webdriver.remote.webdriver import WebDriver

if TYPE_CHECKING:
    from ..auth.base import Authentication

class TTP(ABC):
    """
    Abstract Base Class for a single Tactic, Technique, and Procedure (TTP).

    Each TTP implementation must define how to generate payloads, how to
    execute a test step with a given payload, and how to verify the outcome.
    """

    def __init__(self, name: str, description: str, expected_result: bool = True, authentication: Optional['Authentication'] = None):
        """
        Initialize a TTP.
        
        Args:
            name: Name of the TTP
            description: Description of what the TTP does
            expected_result: Whether this TTP is expected to pass (True) or fail (False).
                           True means we expect to find vulnerabilities/success conditions.
                           False means we expect the security controls to prevent success.
            authentication: Optional authentication mechanism to use before executing TTP
        """
        self.name = name
        self.description = description
        self.expected_result = expected_result
        self.authentication = authentication

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
        Verifies the outcome of the executed step.

        Returns:
            True if the test indicates a potential success/vulnerability, False otherwise.
        """
        pass
