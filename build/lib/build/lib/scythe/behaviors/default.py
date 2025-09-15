from typing import Any
from selenium.webdriver.remote.webdriver import WebDriver

from .base import Behavior

class DefaultBehavior(Behavior):
    """
    Default behavior that maintains the original TTPExecutor functionality.
    
    This behavior provides the same timing and interaction patterns as the
    original implementation, ensuring backward compatibility.
    """
    
    def __init__(self, delay: float = 1.0):
        """
        Initialize DefaultBehavior.
        
        Args:
            delay: Fixed delay between actions in seconds (matches original default)
        """
        super().__init__(
            name="Default Behavior",
            description="Maintains original TTPExecutor behavior for backward compatibility"
        )
        
        self.delay = delay
        
    def pre_execution(self, driver: WebDriver, target_url: str) -> None:
        """
        No special pre-execution behavior in default mode.
        """
        pass
    
    def pre_step(self, driver: WebDriver, payload: Any, step_number: int) -> None:
        """
        No special pre-step behavior in default mode.
        """
        pass
    
    def post_step(self, driver: WebDriver, payload: Any, step_number: int, success: bool) -> None:
        """
        No special post-step behavior in default mode.
        """
        pass
    
    def post_execution(self, driver: WebDriver, results: list) -> None:
        """
        No special post-execution behavior in default mode.
        """
        pass
    
    def get_step_delay(self, step_number: int) -> float:
        """
        Return the fixed delay as in the original implementation.
        """
        return self.delay
    
    def should_continue(self, step_number: int, consecutive_failures: int) -> bool:
        """
        Default behavior continues indefinitely like the original implementation.
        """
        return True
    
    def on_error(self, error: Exception, step_number: int) -> bool:
        """
        Default error handling continues execution like the original implementation.
        """
        return True