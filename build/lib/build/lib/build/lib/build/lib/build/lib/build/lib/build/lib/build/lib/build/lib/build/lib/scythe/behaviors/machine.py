from typing import Any, Dict
from selenium.webdriver.remote.webdriver import WebDriver
import time
from .base import Behavior

class MachineBehavior(Behavior):
    """
    Behavior that emulates machine-like interaction patterns during TTP execution.
    
    This behavior provides consistent, predictable timing and interactions
    suitable for automated testing and high-speed execution scenarios.
    """
    
    def __init__(self, 
                 delay: float = 0.5,
                 max_retries: int = 5,
                 retry_delay: float = 1.0,
                 fail_fast: bool = True):
        """
        Initialize MachineBehavior.
        
        Args:
            delay: Fixed delay between actions in seconds
            max_retries: Maximum number of retries on failure
            retry_delay: Fixed delay between retries
            fail_fast: Whether to stop on first critical error
        """
        super().__init__(
            name="Machine Behavior",
            description="Emulates machine-like interaction patterns with consistent timing and predictable behavior"
        )
        
        self.delay = delay
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.fail_fast = fail_fast
        self.retry_count = 0
        self.total_errors = 0
        
    def pre_execution(self, driver: WebDriver, target_url: str) -> None:
        """
        Prepare for machine-like execution with optimal settings.
        """
        # Set consistent window size for reproducible results
        driver.set_window_size(1920, 1080)
        
        # No initial delay - machines start immediately
        pass
    
    def pre_step(self, driver: WebDriver, payload: Any, step_number: int) -> None:
        """
        Prepare for each step with machine-like precision.
        """
        # Machines execute without hesitation
        pass
    
    def post_step(self, driver: WebDriver, payload: Any, step_number: int, success: bool) -> None:
        """
        Post-step behavior with machine-like consistency.
        """
        if success:
            self.retry_count = 0
        else:
            self.retry_count += 1
            self.total_errors += 1
        
        # Fixed delay regardless of success/failure
        time.sleep(self.delay)
    
    def post_execution(self, driver: WebDriver, results: list) -> None:
        """
        Final machine-like behavior after execution completes.
        """
        # Machines complete and terminate immediately
        pass
    
    def get_step_delay(self, step_number: int) -> float:
        """
        Return consistent delay for machine-like timing.
        
        Machines maintain constant timing regardless of context.
        """
        return self.delay
    
    def should_continue(self, step_number: int, consecutive_failures: int) -> bool:
        """
        Machine-like decision making on whether to continue.
        
        Machines follow strict rules without emotion or fatigue.
        """
        if self.fail_fast and consecutive_failures > 0:
            return consecutive_failures <= self.max_retries
        
        return True
    
    def on_error(self, error: Exception, step_number: int) -> bool:
        """
        Machine-like error handling.
        
        Machines handle errors systematically and predictably.
        """
        self.total_errors += 1
        
        # Fixed retry delay
        time.sleep(self.retry_delay)
        
        # Fail fast on critical errors
        if self.fail_fast:
            critical_errors = [
                "WebDriverException",
                "TimeoutException",
                "SessionNotCreatedException"
            ]
            
            if any(error_type in str(type(error)) for error_type in critical_errors):
                return False
        
        # Continue based on retry count
        return self.retry_count < self.max_retries
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get machine execution statistics.
        
        Returns:
            Dictionary containing execution metrics
        """
        return {
            "total_errors": self.total_errors,
            "current_retry_count": self.retry_count,
            "execution_count": self.execution_count,
            "average_delay": self.delay,
            "max_retries": self.max_retries
        }
    
    def reset_statistics(self) -> None:
        """
        Reset all execution statistics.
        """
        self.total_errors = 0
        self.retry_count = 0
        self.execution_count = 0