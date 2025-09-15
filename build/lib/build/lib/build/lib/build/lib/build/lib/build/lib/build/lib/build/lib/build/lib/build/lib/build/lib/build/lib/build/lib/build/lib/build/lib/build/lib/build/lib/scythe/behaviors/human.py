from typing import Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
import time
import random
from .base import Behavior

class HumanBehavior(Behavior):
    """
    Behavior that emulates human-like interaction patterns during TTP execution.
    
    This behavior introduces realistic delays, mouse movements, and typing patterns
    to make the TTP execution appear more human-like and less detectable.
    """
    
    def __init__(self, 
                 base_delay: float = 2.0,
                 delay_variance: float = 1.0,
                 typing_delay: float = 0.1,
                 mouse_movement: bool = True,
                 max_consecutive_failures: int = 3):
        """
        Initialize HumanBehavior.
        
        Args:
            base_delay: Base delay between actions in seconds
            delay_variance: Random variance to add to delays
            typing_delay: Delay between keystrokes when typing
            mouse_movement: Whether to add random mouse movements
            max_consecutive_failures: Maximum consecutive failures before stopping
        """
        super().__init__(
            name="Human Behavior",
            description="Emulates human-like interaction patterns with realistic delays and movements"
        )
        
        self.base_delay = base_delay
        self.delay_variance = delay_variance
        self.typing_delay = typing_delay
        self.mouse_movement = mouse_movement
        self.max_consecutive_failures = max_consecutive_failures
        self.consecutive_failures = 0
        
    def pre_execution(self, driver: WebDriver, target_url: str) -> None:
        """
        Prepare for human-like execution by setting up browser characteristics.
        """
        # Simulate human-like browser setup
        driver.set_window_size(1366, 768)  # Common resolution
        
        # Add some initial delay as humans don't instantly navigate
        time.sleep(self._random_delay(1.0, 2.5))
        
        # Random mouse movement to simulate human presence
        if self.mouse_movement:
            self._random_mouse_movement(driver)
    
    def pre_step(self, driver: WebDriver, payload: Any, step_number: int) -> None:
        """
        Prepare for each step with human-like behavior.
        """
        # Humans sometimes pause before taking action
        if step_number > 1:
            pause_delay = self._random_delay(0.5, 1.5)
            time.sleep(pause_delay)
        
        # Simulate human-like mouse movement before interaction
        if self.mouse_movement and random.random() < 0.7:  # 70% chance
            self._random_mouse_movement(driver)
        
        # Humans might scroll or look around the page
        if random.random() < 0.3:  # 30% chance
            self._simulate_page_scanning(driver)
    
    def post_step(self, driver: WebDriver, payload: Any, step_number: int, success: bool) -> None:
        """
        Post-step behavior with human-like reactions.
        """
        if success:
            self.consecutive_failures = 0
            # Humans might pause longer after success to examine results
            pause_delay = self._random_delay(1.0, 3.0)
        else:
            self.consecutive_failures += 1
            # Humans might pause and try to understand why it failed
            pause_delay = self._random_delay(0.5, 2.0)
        
        time.sleep(pause_delay)
        
        # Simulate human checking the page after action
        if random.random() < 0.4:  # 40% chance
            self._simulate_result_checking(driver)
    
    def post_execution(self, driver: WebDriver, results: list) -> None:
        """
        Final human-like behavior after execution completes.
        """
        # Humans might browse around after completing their task
        if random.random() < 0.3:  # 30% chance
            self._simulate_casual_browsing(driver)
        
        # Final pause before closing
        time.sleep(self._random_delay(1.0, 2.0))
    
    def get_step_delay(self, step_number: int) -> float:
        """
        Calculate human-like delay between steps.
        
        Humans tend to:
        - Start slower and get faster as they get comfortable
        - Have more variance in timing
        - Slow down when they encounter issues
        """
        # Base delay with decreasing factor as steps progress (getting comfortable)
        comfort_factor = max(0.5, 1.0 - (step_number * 0.05))
        
        # Failure factor - slow down if we've had failures
        failure_factor = 1.0 + (self.consecutive_failures * 0.3)
        
        # Calculate final delay with human-like variance
        calculated_delay = self.base_delay * comfort_factor * failure_factor
        variance = self._random_delay(-self.delay_variance, self.delay_variance)
        
        return max(0.1, calculated_delay + variance)
    
    def should_continue(self, step_number: int, consecutive_failures: int) -> bool:
        """
        Human-like decision making on whether to continue.
        
        Humans typically give up after several consecutive failures.
        """
        return consecutive_failures < self.max_consecutive_failures
    
    def on_error(self, error: Exception, step_number: int) -> bool:
        """
        Human-like error handling.
        
        Humans might retry certain errors but give up on others.
        """
        # Simulate human confusion/frustration with longer pause
        time.sleep(self._random_delay(2.0, 4.0))
        
        # Humans are more likely to continue on simple errors
        if "NoSuchElementException" in str(type(error)):
            return step_number < 5  # Give up after 5 attempts if elements not found
        
        return True
    
    def human_type(self, element, text: str) -> None:
        """
        Type text with human-like characteristics.
        
        Args:
            element: The web element to type into
            text: The text to type
        """
        element.clear()
        
        for char in text:
            element.send_keys(char)
            
            # Human-like typing delay with occasional longer pauses
            if random.random() < 0.1:  # 10% chance of longer pause
                time.sleep(self._random_delay(0.2, 0.5))
            else:
                time.sleep(self._random_delay(0.05, self.typing_delay))
    
    def _random_mouse_movement(self, driver: WebDriver) -> None:
        """
        Simulate random mouse movements.
        """
        try:
            actions = ActionChains(driver)
            
            # Get current window size
            size = driver.get_window_size()
            
            # Random movement within the window
            x = random.randint(100, size['width'] - 100)
            y = random.randint(100, size['height'] - 100)
            
            # Move to random position
            actions.move_by_offset(x, y)
            actions.perform()
            
            # Small delay after movement
            time.sleep(self._random_delay(0.1, 0.3))
            
        except Exception:
            # If mouse movement fails, just continue
            pass
    
    def _simulate_page_scanning(self, driver: WebDriver) -> None:
        """
        Simulate human scanning the page by scrolling.
        """
        try:
            # Random scroll amount
            scroll_amount = random.randint(100, 300)
            
            if random.random() < 0.5:  # 50% chance scroll down
                driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            else:  # 50% chance scroll up
                driver.execute_script(f"window.scrollBy(0, -{scroll_amount});")
            
            # Brief pause to "read"
            time.sleep(self._random_delay(0.5, 1.0))
            
            # Scroll back
            driver.execute_script(f"window.scrollBy(0, {-scroll_amount if scroll_amount > 0 else abs(scroll_amount)});")
            
        except Exception:
            # If scrolling fails, just continue
            pass
    
    def _simulate_result_checking(self, driver: WebDriver) -> None:
        """
        Simulate human checking results after an action.
        """
        try:
            # Look for common result indicators
            indicators = ["error", "success", "invalid", "failed", "welcome", "dashboard"]
            
            for indicator in indicators:
                try:
                    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{indicator}')]")
                    if elements:
                        # "Focus" on the element briefly
                        ActionChains(driver).move_to_element(elements[0]).perform()
                        time.sleep(self._random_delay(0.3, 0.8))
                        break
                except Exception:
                    continue
                    
        except Exception:
            # If result checking fails, just continue
            pass
    
    def _simulate_casual_browsing(self, driver: WebDriver) -> None:
        """
        Simulate casual browsing behavior after completing the main task.
        """
        try:
            # Try to find and click a random link
            links = driver.find_elements(By.TAG_NAME, "a")
            if links:
                random_link = random.choice(links[:5])  # Choose from first 5 links
                if random_link.is_displayed():
                    ActionChains(driver).move_to_element(random_link).perform()
                    time.sleep(self._random_delay(0.5, 1.0))
                    
                    # Sometimes click, sometimes just hover
                    if random.random() < 0.3:  # 30% chance to actually click
                        try:
                            random_link.click()
                            time.sleep(self._random_delay(1.0, 2.0))
                            driver.back()  # Go back to original page
                        except Exception:
                            pass
                            
        except Exception:
            # If casual browsing fails, just continue
            pass