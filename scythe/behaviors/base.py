from abc import ABC, abstractmethod
from typing import Dict, Any
from selenium.webdriver.remote.webdriver import WebDriver
import random

class Behavior(ABC):
    """
    Abstract base class for defining execution behaviors during TTP tests.
    
    Behaviors control how TTPs are executed to emulate realistic human or machine
    patterns, including timing, interaction patterns, and error handling.
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.execution_count = 0
        self.config = {}
    
    @abstractmethod
    def pre_execution(self, driver: WebDriver, target_url: str) -> None:
        """
        Called before the TTP execution begins.
        
        Args:
            driver: The WebDriver instance
            target_url: The target URL for the TTP
        """
        pass
    
    @abstractmethod
    def pre_step(self, driver: WebDriver, payload: Any, step_number: int) -> None:
        """
        Called before each TTP step execution.
        
        Args:
            driver: The WebDriver instance
            payload: The current payload being used
            step_number: The current step number (1-based)
        """
        pass
    
    @abstractmethod
    def post_step(self, driver: WebDriver, payload: Any, step_number: int, success: bool) -> None:
        """
        Called after each TTP step execution.
        
        Args:
            driver: The WebDriver instance
            payload: The payload that was used
            step_number: The current step number (1-based)
            success: Whether the step was successful
        """
        pass
    
    @abstractmethod
    def post_execution(self, driver: WebDriver, results: list) -> None:
        """
        Called after the TTP execution completes.
        
        Args:
            driver: The WebDriver instance
            results: List of results from the TTP execution
        """
        pass
    
    @abstractmethod
    def get_step_delay(self, step_number: int) -> float:
        """
        Returns the delay to use before the next step.
        
        Args:
            step_number: The current step number (1-based)
            
        Returns:
            Delay in seconds
        """
        pass
    
    def should_continue(self, step_number: int, consecutive_failures: int) -> bool:
        """
        Determines whether to continue execution based on current state.
        
        Args:
            step_number: The current step number (1-based)
            consecutive_failures: Number of consecutive failed attempts
            
        Returns:
            True if execution should continue, False otherwise
        """
        return True
    
    def on_error(self, error: Exception, step_number: int) -> bool:
        """
        Called when an error occurs during execution.
        
        Args:
            error: The exception that occurred
            step_number: The current step number (1-based)
            
        Returns:
            True if execution should continue, False if it should stop
        """
        return True
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the behavior with custom parameters.
        
        Args:
            config: Dictionary of configuration parameters
        """
        self.config.update(config)
    
    def _random_delay(self, min_seconds: float, max_seconds: float) -> float:
        """
        Generate a random delay between min and max seconds.
        
        Args:
            min_seconds: Minimum delay
            max_seconds: Maximum delay
            
        Returns:
            Random delay in seconds
        """
        return random.uniform(min_seconds, max_seconds)
    
    def _increment_execution_count(self) -> None:
        """Increment the execution counter."""
        self.execution_count += 1